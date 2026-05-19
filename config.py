"""
Configuration settings for Pinterest Auto Poster
"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Pinterest OAuth2
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
PINTEREST_APP_ID = os.getenv("PINTEREST_APP_ID")
PINTEREST_APP_SECRET = os.getenv("PINTEREST_APP_SECRET")

# Etsy shop info (used to personalise generated content)
ETSY_SHOP_NAME = os.getenv("ETSY_SHOP_NAME", "My Etsy Shop")
ETSY_SHOP_URL = os.getenv("ETSY_SHOP_URL", "")

# Image folder
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER", "./images")

# Supported image extensions
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Pinterest board mapping  (board name → board id)
# Leave empty to auto-fetch from your Pinterest account
BOARD_MAP: dict[str, str] = {}

# How many pins to post per run (0 = all images)
MAX_PINS_PER_RUN = int(os.getenv("MAX_PINS_PER_RUN", "0"))

# Seconds to wait between consecutive pin requests (rate-limit safety)
DELAY_BETWEEN_PINS = float(os.getenv("DELAY_BETWEEN_PINS", "3"))
