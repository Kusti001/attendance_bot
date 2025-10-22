from dotenv import load_dotenv
import os
from datetime import timezone, timedelta

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///bot.db")
CODE_INTERVAL = int(os.getenv("TOTP_INTERVAL", 20))
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",")]

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))