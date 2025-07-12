## 📦 Local Dev via Docker Compose

You can run the bot locally on any device without syncing `.env` files by using `docker-compose`.

### 1. Create a `.env.docker` file:

```env
LINE_CHANNEL_ACCESS_TOKEN=your_line_token_here
GROUP_ID=your_line_group_id_here
CLOUDINARY_CLOUD_NAME=your_cloudinary_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

### 2. Use the provided `docker-compose.yml`:

```yaml
version: '3.8'

services:
  exchange-rate-bot:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env.docker
    restart: unless-stopped
```

### 3. Run the bot:

```bash
docker compose up --build
```

The bot will be available at `http://localhost:8080/`
