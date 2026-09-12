import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.tablecheck.com/en/shops/maguro-mart/reserve"
TARGET_DATE = os.getenv("TARGET_DATE", "2026-10-12")
PARTY_SIZE = int(os.getenv("PARTY_SIZE", "4"))
OUTPUT = Path(os.getenv("OUTPUT_FILE", "availability.json"))

TIME_RE = re.compile(r"^\s*([01]?\d|2[0-3]):[0-5]\d\s*$")


def normalize_time(text: str):
    text = (text or "").strip()
    return text if TIME_RE.match(text) else None


def collect_native_select_times(page):
    found = []
    selects = page.locator("select")
    for i in range(selects.count()):
        sel = selects.nth(i)
        opts = sel.locator("option")
        for j in range(opts.count()):
            opt = opts.nth(j)
            text = (opt.inner_text() or "").strip()
            t = normalize_time(text)
            if not t:
                continue
            disabled = opt.is_disabled()
            value = opt.get_attribute("value")
            if not disabled and value not in (None, "", "-1"):
                found.append(t)
    return found


def collect_clickable_time_controls(page):
    found = []
    # TableCheck may render some time choices as buttons/labels rather than <option>.
    candidates = page.locator("button, [role='button'], label")
    for i in range(min(candidates.count(), 500)):
        node = candidates.nth(i)
        try:
            text = (node.inner_text(timeout=300) or "").strip()
        except Exception:
            continue
        t = normalize_time(text)
        if not t:
            continue
        try:
            disabled = node.is_disabled()
        except Exception:
            disabled = False
        aria_disabled = (node.get_attribute("aria-disabled") or "").lower() == "true"
        cls = (node.get_attribute("class") or "").lower()
        visually_disabled = any(x in cls for x in ("disabled", "unavailable", "soldout", "sold-out"))
        if not (disabled or aria_disabled or visually_disabled):
            found.append(t)
    return found


def best_effort_accept_notice(page):
    # The venue notice checkbox is typically the first checkbox on this form.
    boxes = page.locator('input[type="checkbox"]')
    if boxes.count() == 0:
        return
    for i in range(min(boxes.count(), 4)):
        box = boxes.nth(i)
        try:
            if box.is_visible() and box.is_enabled() and not box.is_checked():
                box.check(force=True)
                page.wait_for_timeout(1000)
                return
        except Exception:
            pass


def main():
    params = {
        "num_people": PARTY_SIZE,
        "start_date": TARGET_DATE,
    }
    url = f"{BASE_URL}?{urlencode(params)}"

    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_date": TARGET_DATE,
        "party_size": PARTY_SIZE,
        "url": url,
        "available": False,
        "times": [],
        "status": "ok",
        "note": "",
    }

    debug_dir = Path("debug")
    debug_dir.mkdir(exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="en-US",
                timezone_id="Asia/Tokyo",
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)

            best_effort_accept_notice(page)
            page.wait_for_timeout(4000)

            # Collect actual selectable times from both common rendering styles.
            times = set(collect_native_select_times(page))
            times.update(collect_clickable_time_controls(page))

            # Keep a diagnostic body-text excerpt in case TableCheck changes its UI.
            body_text = page.locator("body").inner_text(timeout=5000)
            result["times"] = sorted(times)
            result["available"] = len(times) > 0

            if result["available"]:
                result["note"] = "At least one selectable reservation time was detected."
            else:
                lower = body_text.lower()
                unavailable_phrases = [
                    "your selected time is unavailable",
                    "no availability",
                    "fully booked",
                    "unavailable",
                ]
                if any(p in lower for p in unavailable_phrases):
                    result["note"] = "No selectable time detected; page also indicates unavailability."
                else:
                    result["note"] = (
                        "No selectable time detected. This can mean sold out, or that TableCheck "
                        "changed the form structure. Check the workflow artifact if this persists."
                    )

            # Lightweight diagnostics useful for manual verification.
            page.screenshot(path=str(debug_dir / "last.png"), full_page=True)
            (debug_dir / "last.html").write_text(page.content(), encoding="utf-8")
            browser.close()

    except PlaywrightTimeoutError as e:
        result["status"] = "error"
        result["note"] = f"Page timeout: {e}"
    except Exception as e:
        result["status"] = "error"
        result["note"] = f"{type(e).__name__}: {e}"

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Do not fail the scheduled workflow merely because TableCheck timed out.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
