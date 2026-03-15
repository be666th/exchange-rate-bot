# 📈 Exchange Rate Bot

A containerized FastAPI bot that captures Bangkok Bank exchange rates daily and sends the screenshot to your LINE group. Deployed on Azure Container Apps with GitHub Actions automation.

## 🚀 Features

- Captures exchange rate page using Selenium
- Uploads image to Cloudinary
- Pushes LINE message with image URL
- FastAPI endpoint for manual trigger
- Automated deploy pipeline with cron schedule via GitHub Actions

## 🛠️ Requirements

- Python 3.10+
- Azure subscription with Container Apps enabled
- Cloudinary account
- LINE Messaging API channel

## 📂 Project Structure

```
.
├── app.py
├── Dockerfile
├── requirements.txt
├── .env.example
└── .github
    └── workflows
        └── deploy.yml
```

## ⚙️ Setup

1. Clone repository

   ```bash
   git clone https://github.com/yourusername/exchange-rate-bot.git
   cd exchange-rate-bot
   ```

2. Create `.env`

   ```bash
   cp .env.example .env
   ```

3. Fill in your secrets in `.env`

4. Install dependencies (for local test)

   ```bash
   pip install -r requirements.txt
   ```

5. Run locally

   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8080
   ```

## 🐳 Build & Run with Docker

```bash
docker build -t exchange-rate-bot .
docker run -p 8080:8080 --env-file .env exchange-rate-bot
```

## ☁️ Deploy to Azure Container Apps

1. Ensure you have Azure Container Apps and Azure Container Registry setup.
2. Configure GitHub Actions secrets:
   - `AZURE_CREDENTIALS`
   - `AZURE_REGISTRY_USERNAME`
   - `AZURE_REGISTRY_PASSWORD`
3. Push to `main` branch for auto-deploy.

## 📅 Cron Schedule

The GitHub Actions workflow runs daily at 01:32 UTC (08:32 Thailand time) to redeploy and trigger the bot automatically.

Adjust cron in `.github/workflows/deploy.yml` as needed.

## 🔗 References

- [FastAPI](https://fastapi.tiangolo.com/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [LINE Messaging API](https://developers.line.biz/en/docs/messaging-api/)
- [Cloudinary Python SDK](https://cloudinary.com/documentation/python_integration)

## 📝 License

MIT License © 2025 YourName
