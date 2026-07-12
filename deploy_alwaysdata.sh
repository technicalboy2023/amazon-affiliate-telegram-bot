#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Update system packages ==="
apt-get update && apt-get upgrade -y

echo "=== 2. Install system deps ==="
apt-get install -y git python3-venv python3-pip sqlite3

echo "=== 3. Clone/update repo ==="
cd ~
if [ -d amazon-affiliate-telegram-bot ]; then
  cd amazon-affiliate-telegram-bot && git pull
else
  git clone https://github.com/technicalboy2023/amazon-affiliate-telegram-bot.git
  cd amazon-affiliate-telegram-bot
fi

echo "=== 4. Setup virtual environment ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "=== 5. Create .env ==="
if [ ! -f .env ]; then
  cat > .env <<EOF
BOT_TOKEN=
ADMIN_TELEGRAM_ID=7475571284
EOF
  echo ".env created — you MUST edit it with your BOT_TOKEN"
  echo "Run: nano .env"
else
  echo ".env already exists"
fi

echo "=== 6. Create data directory ==="
mkdir -p data

echo "=== 7. Database check ==="
if [ -f data/affiliate.db ]; then
  echo "Existing DB found, backing up..."
  cp data/affiliate.db "data/affiliate.db.backup.$(date +%s)"
fi

echo ""
echo "========================================="
echo " Setup complete! Next steps:"
echo "========================================="
echo ""
echo " 1. Edit .env:  nano ~/amazon-affiliate-telegram-bot/.env"
echo "    (set BOT_TOKEN from @BotFather)"
echo ""
echo " 2. Test run:"
echo "    cd ~/amazon-affiliate-telegram-bot"
echo "    source .venv/bin/activate"
echo "    python main.py"
echo "    (CTRL+C to stop, verify no errors)"
echo ""
echo " 3. Set up auto-restart Service:"
echo "    https://admin.alwaysdata.com/service/"
echo "    Type:     Program"
echo "    Command:  /home/achal/amazon-affiliate-telegram-bot/.venv/bin/python /home/achal/amazon-affiliate-telegram-bot/main.py"
echo "    Work dir: /home/achal/amazon-affiliate-telegram-bot"
echo "    Auto-restart: yes"
echo ""
echo " 4. First login via bot:"
echo "    Send /login in Telegram → scan QR code"
echo "========================================="
