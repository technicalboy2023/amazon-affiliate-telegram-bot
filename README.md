# 🤖 Amazon Affiliate Telegram Bot (Lightweight Edition)

Automatically forward Amazon product links from source Telegram channels to your destination channel, replacing them with your **affiliate links** in real-time.

This project has been completely rebuilt to be **extremely lightweight, highly stable, and zero-risk**. It uses **SQLite** and a single `asyncio` event loop (combining `Telethon` + `python-telegram-bot`), making it perfect for Alwaysdata's 256MB free tier.

**No heavy PostgreSQL databases. No complex `.env` handling. No bloated Aiogram code.**

---

## 📋 Features

- 🔄 **Auto Forwarding** — Monitor multiple source channels, auto-forward with affiliate links
- 🔗 **Link Conversion** — Automatically detects and resolves any Amazon URL (`amzn.to`, `amazon.in`, etc.) and replaces it with your affiliate tag.
- 📸 **Media Support** — Handles photos, videos, GIFs, documents with captions seamlessly.
- ✂️ **Word Replacements** — Real-time find-and-replace text (e.g., "Shop Now" → "Buy Now")
- 🚫 **Block Words** — Skip posts completely if they contain specific blocked words
- 📝 **Header/Footer** — Prepend/append custom text to every forwarded post
- ⏱️ **Delay Control** — Set a custom delay between forwards to avoid Telegram flood limits
- 🚦 **Pause/Resume** — Pause forwarding at any time, resume whenever you want
- 📊 **Real-Time Stats** — Track messages received, forwarded, skipped, and recent activity
- 🛡️ **Smart Duplicate Detection** — Automatically extracts the Amazon ASIN and prevents posting the same product twice within a 1-hour sliding window. No spam!

---

## 🏗️ Architecture

```text
📁 controlbot/        (python-telegram-bot) Admin interface & inline keyboards
📁 database/          (sqlite3) Thread-safe DB for routes, stats, dedup, and settings
📁 userbot/           (telethon) Captures posts, replaces links, and forwards
📄 bot.py             Main entrypoint running both bots on one asyncio loop
📄 login.py           Interactive CLI to generate your Telegram session
```

---

## 🚀 Setup on Alwaysdata (Step by Step)

### 1️⃣ SSH into AlwaysData

Open your terminal and SSH into your Alwaysdata account:
```bash
ssh YOUR_USERNAME@ssh-YOUR_ACCOUNT.alwaysdata.net
```

### 2️⃣ Clone Repository

```bash
cd ~
git clone https://github.com/technicalboy2023/amazon-affiliate-telegram-bot.git bot
cd bot
```

### 3️⃣ Create Virtual Environment & Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4️⃣ Configure `config.json`

Create the configuration file:
```bash
cp config.example.json config.json
nano config.json
```
Fill in your credentials:
- `api_id` / `api_hash`: Get these from [my.telegram.org](https://my.telegram.org)
- `phone`: Your phone number with country code (e.g., `+919876543210`)
- `bot_token`: Your admin bot token from [@BotFather](https://t.me/BotFather)
- `admin_id`: Your personal Telegram User ID (get it from [@userinfobot](https://t.me/userinfobot))

### 5️⃣ Login (Generate Session)

Run the interactive login script directly on the server to authenticate your Userbot:
```bash
python3 login.py
```
1. It will use the credentials from `config.json`.
2. Enter the OTP code Telegram sends you.
3. This creates a `userbot.session` file locally.

### 6️⃣ Create AlwaysData Service

1. Go to **AlwaysData Admin** → **Advanced** → **Services** → **Add a service**
2. Configure:
   - **Name:** `amazon-bot`
   - **Type:** **Program**
   - **Command:** `/home/YOUR_USERNAME/bot/venv/bin/python3 bot.py`
   - **Working directory:** `/home/YOUR_USERNAME/bot`
3. Make sure **Paused** is **unchecked**.
4. **Save** the service (it will start automatically).

Check your live logs at: `Advanced → Services → amazon-bot → Logs`

---

## 🎮 How to Use (Admin Commands)

Send `/start` to your bot on Telegram. **You must be the authorized admin (set in `config.json`) to use the bot.**

### 🔗 Amazon Affiliate Settings:
- `/set_tag <tag>` — Set your Amazon affiliate tag (e.g., `my_tag-21`)
- `/clear_tag` — Remove your affiliate tag
- `/set_domain <domain>` — Set default Amazon domain (e.g., `amazon.in` or `amazon.com`)

### 📡 Routing Posts:
- `/add_source <@username/ID>` — Add a source channel to monitor
- `/set_dest <@username/ID>` — Set the global destination where all posts go

*Type `/help` in the bot to see all commands for adding word replacements, blocking words, and viewing your dashboard!*

---

## 🧹 Database Cleanup (Auto Maintenance)

The bot stores duplicate ASINs for 1 hour to prevent spam. You can set up an Alwaysdata Scheduled Task to prune these database logs and save space automatically.

1. Go to **AlwaysData Admin** → **Advanced** → **Scheduled Tasks** → **Add**
2. **Command:** `cd /home/YOUR_USERNAME/bot && venv/bin/python3 test_cleanup.py`
3. **Schedule:** `@daily`
4. **Save**
