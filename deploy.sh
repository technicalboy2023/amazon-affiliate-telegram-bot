#!/usr/bin/env bash
# ============================================================
# AlwaysData FREE deployment script for Amazon Affiliate Bot
# Run this ONCE via SSH on your alwaysdata account
# ============================================================
set -e

echo "=== 1. Cloning repository ==="
cd ~
git clone https://github.com/technicalboy2023/amazon-affiliate-telegram-bot.git affilate
cd affilate

echo "=== 2. Creating .env file ==="
cat > .env << 'EOF'
BOT_TOKEN=your_bot_token_here
ADMIN_TELEGRAM_ID=your_telegram_id_here
EOF
echo "⚠ IMPORTANT: Edit .env with your real BOT_TOKEN and ADMIN_TELEGRAM_ID before running!"

echo "=== 3. Creating Python virtualenv ==="
python -m venv .venv
source .venv/bin/activate

echo "=== 4. Installing dependencies ==="
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "=== 5. Testing the bot ==="
echo "Run manually first: cd ~/affilate && .venv/bin/python main.py"
echo ""
echo "=== 6. Set up as a Service in admin panel ==="
echo "Go to: Advanced > Services > Add a service"
echo "  Name: amazon-affiliate-bot"
echo "  Command: /home/$(whoami)/affilate/.venv/bin/python /home/$(whoami)/affilate/main.py"
echo "  Working directory: /home/$(whoami)/affilate"
echo "  Environment variables: (leave blank - uses .env)"
echo "  Monitoring command: (leave blank)"
echo ""
echo "✅ Done! The service will auto-start and auto-restart on crash."
