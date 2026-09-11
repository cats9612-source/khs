# Maguro Mart 예약 모니터

대상:

- 매장: Maguro Mart
- 사이트: TableCheck
- 날짜: **2026-09-19**
- 인원: **4명**
- 확인 주기: **30분**
- 알림: **Telegram 푸시**
- 실행 위치: **GitHub Actions** — 노트북을 꺼도 동작

TableCheck는 `start_date`와 `num_people` URL 파라미터를 지원하므로 해당 조건으로 페이지를 연 뒤,
Playwright가 실제 예약 폼에서 선택 가능한 시간 옵션을 검사합니다.

## 1. Telegram 봇 만들기

1. Telegram에서 `@BotFather`를 엽니다.
2. `/newbot`으로 봇을 만듭니다.
3. BotFather가 주는 **bot token**을 보관합니다.
4. 만든 봇에게 아무 메시지나 한 번 보냅니다.
5. 브라우저에서 아래 주소를 열어 `chat.id`를 확인합니다.

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

예: 응답 안의 `"chat":{"id":123456789,...}`에서 `123456789`가 chat ID입니다.

## 2. GitHub에 올리기

새 **private repository**를 하나 만들고 이 폴더의 내용을 그대로 업로드합니다.

중요: `.github/workflows/monitor.yml`도 포함되어야 합니다.

## 3. GitHub Secrets 등록

Repository → **Settings → Secrets and variables → Actions → New repository secret**

아래 두 개를 만듭니다.

| Secret | 값 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather가 준 토큰 |
| `TELEGRAM_CHAT_ID` | 위에서 확인한 chat ID |

## 4. 테스트

GitHub repository에서:

**Actions → Maguro Mart availability monitor → Run workflow**

실행 결과에서 `availability.json`을 확인할 수 있습니다.

예:

```json
{
  "target_date": "2026-09-19",
  "party_size": 4,
  "available": false,
  "times": []
}
```

빈자리가 잡히면:

```json
{
  "available": true,
  "times": ["17:30", "18:00"]
}
```

그리고 Telegram으로 즉시 알림을 보냅니다.

## 중복 알림 방지

예약 가능 상태를 처음 발견했을 때 repository에 상태용 Issue를 하나 만듭니다.
계속 자리가 있는 동안에는 같은 알림을 반복하지 않습니다.

다시 매진되면 해당 Issue를 자동으로 닫습니다.
그 후 취소 자리가 다시 나타나면 **새 Telegram 알림**이 발생합니다.

## 직접 실행하기

Python 3.12 권장:

```bash
pip install -r requirements.txt
python -m playwright install chromium
python monitor.py
```

## 확인 주기 변경

`.github/workflows/monitor.yml`:

```yaml
- cron: "0,30 * * * *"
```

은 매시 `00분`, `30분` 실행입니다.

GitHub Actions의 scheduled workflow는 서버 부하 등의 이유로 정확히 초 단위에 실행된다는 보장은 없습니다.

## 주의

이 프로그램은 **예약 자체를 자동으로 확정하지 않습니다**.
빈자리를 감지하고 알림만 보냅니다. 알림을 받으면 TableCheck 페이지에서 직접 예약해야 합니다.

또한 TableCheck가 페이지 구조를 변경하면 시간 선택 감지 로직을 수정해야 할 수 있습니다.
