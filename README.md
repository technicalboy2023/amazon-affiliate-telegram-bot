# 🤖 Telegram Amazon Affiliate Bot

Automatically forward Amazon product links from source Telegram channels to your destination channel, replacing them with your **affiliate links** in real-time.

Works with any Amazon domain (`.in`, `.com`, etc.) and supports **media posts** (photos, videos, documents), **word replacements**, **blocked words**, **header/footer** customization, and **duplicate ASIN detection**.

---

## 📋 Features

| Feature | Description |
|---------|-------------|
| 🔄 **Auto Forwarding** | Monitor multiple source channels, auto-forward with affiliate links |
| 🔗 **Link Conversion** | Replace any Amazon URL with your affiliate tag |
| 📸 **Media Support** | Handles photos, videos, GIFs, documents with captions |
| ✂️ **Word Replacements** | Find-and-replace text (e.g., "Shop Now" → "Buy Now") |
| 🚫 **Block Words** | Skip posts containing specific words |
| 📝 **Header/Footer** | Prepend/append text to every forwarded post |
| ⏱️ **Delay Control** | Set delay between forwards to avoid spam |
| 🚦 **Pause/Resume** | Pause forwarding at any time, resume later |
| 📊 **Real-Time Stats** | See messages received, forwarded, and last activity |
| 🧹 **Auto Cleanup** | Scheduled cleanup of old DB rows (via AlwaysData Tasks) |
| 🔐 **File-Based Session** | No complex OTP flow — generate session locally and upload |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram Bot   │────▶│  Control Commands │────▶│  Settings/Stats │
│  (Aiogram)      │     │  (/status, /help) │     │  (PostgreSQL)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         ▲
┌─────────────────┐     ┌──────────────────┐            │
│  Source Channel │────▶│  ChannelMonitor  │────────────┘
│  (Telegram)     │     │  (Telethon)      │  Logs forwards
└─────────────────┘     └──────────────────┘
                               │
                               ▼
┌─────────────────┐     ┌──────────────────┐
│  Link Engine    │────▶│  Destination     │
│  (Amazon Aff.)  │     │  Channel         │
└─────────────────┘     └──────────────────┘
```

### Components

- **Bot (Aiogram)** — Handles all `/commands` from admin. Manages settings, shows stats.
- **Userbot (Telethon)** — Logs in as your Telegram account to read source channels and post to destination.
- **ChannelMonitor** — Listens to source channels in real-time, processes each message.
- **Link Engine** — Detects Amazon URLs and replaces them with your affiliate links.
- **PostCustomizer** — Applies word replacements, blocked words, header/footer.
- **DuplicateChecker** — Prevents forwarding the same ASIN within the configured window (default: 1 hour).
- **PostgreSQL** — Stores settings, stats, processed messages, and duplicate cache.

---

## 🚀 Setup on Alwaysdata (Step by Step)

### Prerequisites

1. **AlwaysData account** — https://www.alwaysdata.com
2. **Telegram Bot Token** — From [@BotFather](https://t.me/BotFather)
3. **Telegram API Credentials** — From https://my.telegram.org/apps
4. **SSH access** — Enable in AlwaysData Admin → Advanced → SSH

---

### 1️⃣ Create PostgreSQL Database

1. Go to **AlwaysData Admin** → **SQL** → **Add a database**
2. Choose **PostgreSQL** (any version)
3. Note the **database name**, **username**, and **password**
4. Your database URL will be:
   ```
   postgresql+asyncpg://USER:PASSWORD@postgresql-YOUR_ACCOUNT.alwaysdata.net:5432/DB_NAME
   ```
   ⚠️ **Important:** If your password contains `@`, replace it with `%40` (URL encoding)

---

### 2️⃣ Create Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save the **bot token** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

---

### 3️⃣ Get API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your Telegram account
3. Create a new app if you don't have one
4. Note your **API ID** and **API Hash**

---

### 4️⃣ SSH into AlwaysData

```bash
ssh YOUR_USERNAME@ssh-YOUR_ACCOUNT.alwaysdata.net
# Example:
ssh achal@ssh-achal.alwaysdata.net
```

---

### 5️⃣ Clone Repository

```bash
cd ~
git clone https://github.com/technicalboy2023/amazon-affiliate-telegram-bot.git
cd amazon-affiliate-telegram-bot
```

---

### 6️⃣ Create Virtual Environment & Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 7️⃣ Configure .env

```bash
cp .env.example .env
nano .env
```

Fill in your real values:
```ini
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+911234567890
ADMIN_TELEGRAM_ID=123456789     # Your Telegram user ID
DATABASE_URL=postgresql+asyncpg://user:password@postgresql-your_account.alwaysdata.net:5432/db_name
DEFAULT_AFFILIATE_TAG=yourtag-21
DEFAULT_AMAZON_DOMAIN=amazon.in
LOG_LEVEL=INFO
```

**How to get your Telegram User ID:** Send a message to [@userinfobot](https://t.me/userinfobot) on Telegram.

**URL encoding for passwords:** If your DB password contains special characters, encode them:
- `@` → `%40`
- `#` → `%23`
- `!` → `%21`
- `$` → `%24`

Example: `Aman@4899` → `Aman%404899`

---

### 8️⃣ Generate Session File

Since the server (alwaysdata) is located in France, Telegram blocks OTP login from there. Instead, **generate the session on your local machine** and upload it.

#### On your LOCAL PC/Mac/Phone:

```bash
# Install Telethon
pip install telethon

# Run the session generator
python scripts/generate_session.py
```

The script will:
1. Auto-read API ID, Hash, Phone from `.env` (if available)
2. Send an OTP to your Telegram
3. Create a `userbot_session.session` file

#### Upload session to server:

```bash
scp userbot_session.session YOUR_USERNAME@ssh-YOUR_ACCOUNT.alwaysdata.net:~/amazon-affiliate-telegram-bot/
# Example:
scp userbot_session.session achal@ssh-achal.alwaysdata.net:/home/achal/amazon-affiliate-telegram-bot/
```

---

### 9️⃣ Create AlwaysData Service

1. Go to **AlwaysData Admin** → **Advanced** → **Services** → **Add a service**
2. Configure:
   - **Name:** `affiliate-bot`
   - **Type:** **Program**
   - **Command:** `/home/YOUR_USERNAME/amazon-affiliate-telegram-bot/.venv/bin/python main.py`
   - **Working directory:** `/home/YOUR_USERNAME/amazon-affiliate-telegram-bot`
   - **Environment:** Leave default
3. **Save** the service (it will start automatically)

**Check logs:** `Advanced → Services → affiliate-bot → Logs`

---

### 🔟 Verify Bot is Running

On Telegram, open your bot and send:
```
/start
/status
```

You should see:
```
Userbot: 🟢 connected
Monitoring: 🟢 active
```

---

### 🔁 Updating the Bot

```bash
ssh YOUR_USERNAME@ssh-YOUR_ACCOUNT.alwaysdata.net
cd ~/amazon-affiliate-telegram-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt --quiet
# Then restart: AlwaysData Admin → Advanced → Services → affiliate-bot → Save
```

---

### 🧹 Auto Cleanup (Database)

Set up a **Scheduled Task** to clean old database rows:

1. **AlwaysData Admin** → **Advanced** → **Scheduled Tasks** → **Add**
2. Configure:
   - **Command:** `cd /home/YOUR_USERNAME/amazon-affiliate-telegram-bot && .venv/bin/python scripts/cleanup.py`
   - **Schedule:** `0 0 */7 * *` (every 7 days at midnight)

This keeps `processed_messages`, `duplicate_cache`, and `daily_stats` tables clean (retains 3 days of data).

---

## 📖 Bot Commands

### 📋 Info
| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all commands |
| `/status` | Current status with real-time stats |
| `/config` | View all runtime settings |
| `/stats` | Today's statistics |
| `/history` | Recent forwarded messages |
| `/errors` | Recent errors |
| `/ping` | Health check |

### ⚙️ Control
| Command | Description |
|---------|-------------|
| `/pause` | Pause forwarding |
| `/stop` | Stop monitoring |
| `/resume` | Resume forwarding |
| `/reload` | Restart monitor with updated settings |
| `/logout` | Disconnect userbot |

### 🔗 Affiliate
| Command | Description |
|---------|-------------|
| `/affiliate <tag>` | Set affiliate tag |
| `/clear_affiliate` | Clear affiliate tag |
| `/sources` | List source channels |
| `/add_source <channel>` | Add source channel |
| `/remove_source <channel>` | Remove source channel |
| `/dest <channel>` | Set destination channel |
| `/remove_dest` | Clear destination channel |
| `/domain <domain>` | Set Amazon domain (`amazon.in` / `amazon.com`) |
| `/set_delay <sec>` | Set delay between forwards |

### ✂️ Customization
| Command | Description |
|---------|-------------|
| `/add_replace Old➜New` | Add word replacement |
| `/remove_replace Old` | Remove replacement |
| `/list_replaces` | View all replacements |
| `/add_block Word` | Block posts containing word |
| `/remove_block Word` | Remove block rule |
| `/list_blocks` | View all block rules |
| `/set_header Text` | Add header to posts |
| `/set_footer Text` | Add footer to posts |
| `/clear_header` | Remove header |
| `/clear_footer` | Remove footer |

### 🔐 Auth
| Command | Description |
|---------|-------------|
| `/login` | Show session setup instructions |

---

## 📁 Project Structure

```
├── config/
│   └── settings.py          # App configuration (pydantic-settings)
├── core/
│   └── container.py         # DI container (all services)
├── database/
│   ├── engine.py            # SQLAlchemy async engine
│   ├── models/              # ORM models
│   │   ├── user.py
│   │   ├── message.py
│   │   ├── channel.py
│   │   ├── pipeline.py
│   │   ├── telegram_account.py
│   │   ├── stats.py
│   │   ├── duplicate.py
│   │   ├── settings.py
│   │   └── affiliate.py
│   └── repositories/
│       ├── base.py
│       └── message_repo.py
├── services/
│   ├── message_processor.py # Process text through link engine
│   ├── message_publisher.py # Send message to destination
│   ├── duplicate_checker.py # ASIN duplicate detection
│   ├── post_customizer.py   # Word replacements, header/footer
│   ├── settings_service.py  # Runtime settings (DB-backed)
│   ├── stats_service.py     # Daily statistics
│   ├── user_service.py      # User/pipeline management
│   └── link_engine/         # Amazon affiliate link conversion
├── telegram/
│   ├── bot/handlers/
│   │   ├── start.py         # All bot commands
│   │   └── login.py         # Session setup instructions
│   └── userbot/
│       ├── client.py        # Telethon client with watchdog
│       └── handlers/
│           └── monitor.py   # Real-time channel monitor
├── scripts/
│   ├── generate_session.py  # Local session file generator
│   └── cleanup.py           # DB cleanup (Scheduled Tasks)
├── tests/
│   ├── test_settings.py
│   └── test_link_engine_providers.py
├── main.py                  # Entry point
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── pyproject.toml           # Ruff config
```

---

## 🛠️ Development

### Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run tests
```bash
source .venv/bin/activate
pytest tests/ -v
```

### Lint
```bash
source .venv/bin/activate
ruff check .
```

### Environment variables
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

---

## ⚠️ Troubleshooting

### Bot won't start — "No saved session file found"
Run `scripts/generate_session.py` on your local machine, then upload the `userbot_session.session` file to the server.

### Database connection failed — "FATAL: password authentication failed"
Check your `DATABASE_URL` in `.env`. If your password contains special characters like `@`, `#`, or `!`, they must be **URL-encoded**:
- `@` → `%40`
- `#` → `%23`
- `!` → `%21`

### Forwarding not working — "/status" shows "stopped"
1. Make sure source and destination channels are configured: `/sources` and `/dest`
2. Run `/reload` to apply changes
3. Check service logs in AlwaysData Admin

### "⛔ Unauthorized" when sending commands
Only the admin (configured in `ADMIN_TELEGRAM_ID`) can send commands. Check your `.env` file.

---

## 📄 License

This project is licensed under the MIT License.
