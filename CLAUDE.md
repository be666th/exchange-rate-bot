# Exchange Rate Bot — CLAUDE.md

## What This Bot Does

Scrapes Bangkok Bank's foreign exchange rate page (JPY/THB) using headless Chrome, uploads a screenshot of the JPY row to Cloudinary, then pushes a single LINE message to a group with the timestamp, image URL, and buying rate.

Trigger flow: external cron (cron-job.org) → `GET /test-capture` → scrape → Cloudinary upload → LINE push.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Scraping | Selenium (headless Chrome) |
| Image hosting | Cloudinary |
| Messaging | LINE Messaging API (`line-bot-sdk`) |
| Image processing | Pillow |
| Timezone | pytz (Asia/Bangkok) |
| Runtime | Python 3.10, Docker |
| Deployment | Azure Container Apps via GitHub Actions |

## Main Files

| File | Purpose |
|---|---|
| `app.py` | All logic: scraping, image upload, LINE push, FastAPI routes |
| `runner.py` | One-shot entry point (validates env vars, calls `capture_and_send()`) |
| `Dockerfile` | Builds image with Python 3.10 + Chrome + ChromeDriver |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for required environment variables |
| `.github/workflows/deploy.yml` | Azure Container Apps deploy pipeline |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values before running.

```
LINE_CHANNEL_ACCESS_TOKEN=   # LINE Messaging API channel access token
GROUP_ID=                    # Target LINE group ID
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

---

## How to Run

### Locally (web server)
```bash
pip install -r requirements.txt
cp .env.example .env
# fill in .env
uvicorn app:app --reload --host 0.0.0.0 --port 8080
```
Then trigger: `GET http://localhost:8080/test-capture`

### Locally (one-shot)
```bash
python runner.py
```

### Docker
```bash
docker build -t exchange-rate-bot .
docker run -p 8000:8000 --env-file .env exchange-rate-bot
```

### API Endpoints
| Endpoint | Method | Purpose |
|---|---|---|
| `/` | POST | LINE webhook receiver (ignored, returns 200) |
| `/test-capture` | GET | Manually trigger scrape + LINE push |
| `/health` | GET | Health check |
| `/line-test` | GET | Send a test LINE message |
| `/env-check` | GET | Verify env vars are loaded |

---

## Git Conventions

- Branch from `main`; merge back via PR
- Commit messages in imperative English or Thai — match the existing style in git log
- Keep commits focused: one logical change per commit
- Do not commit `.env`, `secrets.txt`, or any credential files (already in `.gitignore`)
- Tag releases if deploying a significant change to Azure

---

## Common Tasks

### Add a new currency
- Edit `app.py`: add a new `find_<currency>_row()` and `extract_<currency>_rates()` following the JPY pattern
- Update the message assembly block near the bottom of `capture_and_send()`

### Fix scraping breakage
- Check if Bangkok Bank changed their table CSS selectors — update `wait_exchange_table()` and `find_jpy_row()` in `app.py`
- Use `/test-capture` + Cloudinary debug uploads (full-page screenshot and page source) to diagnose

### Add or change environment config
- Update `.env.example` first, then `.env`
- If deploying to Azure, update GitHub Actions secrets and the workflow env block in `.github/workflows/deploy.yml`

### Update the LINE message format
- Edit the message assembly block at the bottom of `capture_and_send()` in `app.py`

### Change the cron schedule
- Cron is managed externally via **cron-job.org** (not GitHub Actions — that cron is disabled)
- Update the cron-job.org schedule to call `GET /test-capture` at the desired time
