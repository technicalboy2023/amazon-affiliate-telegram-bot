# 🤖 Amazon Affiliate Telegram Bot (Lightweight Edition)

Automatically forward Amazon product links from source Telegram channels to your destination channel, replacing them with your **affiliate links** in real-time.

This project has been completely rebuilt to be extremely lightweight and stable. It uses **SQLite** and a single `asyncio` loop (`Telethon` + `python-telegram-bot`), making it perfect for Alwaysdata's 256MB free tier. No heavy PostgreSQL or Aiogram required!

---

## 📋 Features

- 🔄 **Auto Forwarding** — Monitor multiple source channels, auto-forward with affiliate links
- 🔗 **Link Conversion** — Replace any Amazon URL (`amzn.to`, `amazon.in`, etc.) with your affiliate tag
- 📸 **Media Support** — Handles photos, videos, GIFs, documents with captions
- ✂️ **Word Replacements** — Find-and-replace text (e.g., "Shop Now" → "Buy Now")
- 🚫 **Block Words** — Skip posts containing specific words
- 📝 **Header/Footer** — Prepend/append text to every forwarded post
- ⏱️ **Delay Control** — Set delay between forwards to avoid spam
- 🚦 **Pause/Resume** — Pause forwarding at any time, resume later
- 📊 **Real-Time Stats** — See messages received, forwarded, and skipped
- 🛡️ **Duplicate Detection** — Automatically extracts the Amazon ASIN and prevents posting the same product twice within 1 hour. No spam!

---

## 🚀 Setup on Alwaysdata (Step by Step)

### 1️⃣ SSH into AlwaysData

```bash
ssh YOUR_USERNAME@ssh-YOUR_ACCOUNT.alwaysdata.net
```

### 2️⃣ Clone Repository

```bash
cd ~
git clone https://github.com/technicalboy2023/amazon-affiliate-telegram-bot.git bot
cd bot
```

### 3️⃣ Create Virtual Environment & Install

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
- `bot_token`: Your admin bot token from [@BotFather](https://t.me/BotFather)
- `api_id` / `api_hash`: Your credentials from [my.telegram.org](https://my.telegram.org)
- `admin_id`: Your personal Telegram User ID (get it from [@userinfobot](https://t.me/userinfobot))

### 5️⃣ Login (Generate Session)

Run the interactive login script directly on the server:
```bash
python3 login.py
```
1. Enter your phone number (e.g. `+919876543210`)
2. Enter the OTP code Telegram sends you.
3. This creates a `userbot.session` file locally. No complex `.env` needed!

### 6️⃣ Create AlwaysData Service

1. Go to **AlwaysData Admin** → **Advanced** → **Services** → **Add a service**
2. Configure:
   - **Name:** `amazon-bot`
   - **Type:** **Program**
   - **Command:** `/home/YOUR_USERNAME/bot/venv/bin/python3 bot.py`
   - **Working directory:** `/home/YOUR_USERNAME/bot`
3. Make sure **Paused** is **unchecked**.
4. **Save** the service (it will start automatically).

Check logs at: `Advanced → Services → amazon-bot → Logs`

---

## 🎮 How to Use (Admin Commands)

Send `/start` to your bot on Telegram. You must be the admin!

**Amazon Affiliate Settings:**
- `/set_tag <tag>` — Set your Amazon affiliate tag (e.g. `my_tag-21`)
- `/clear_tag` — Remove your affiliate tag
- `/set_domain <domain>` — Set default amazon domain (e.g. `amazon.in`)

**Routing Posts:**
- `/add_source <@username/ID>` — Monitor a new channel
- `/set_dest <@username/ID>` — Set the global destination channel

*Type `/help` in the bot to see all commands for adding word replacements, blocking words, and viewing stats!*

---

## 🧹 Database Cleanup (Optional)

The bot stores duplicate ASINs for 1 hour. You can set up an Alwaysdata Scheduled Task to prune the database logs to save space.

- **Command:** `cd /home/YOUR_USERNAME/bot && venv/bin/python3 test_cleanup.py`
- **Schedule:** `@daily`
