# pinterest-auto

Automatically read product images from a local folder, generate SEO-optimised Pinterest metadata (title, description, keywords, board category) with GPT-4o Vision, and post pins to promote your Etsy shop.

---

## How it works

```
images/  (your product photos)
   └─► GPT-4o Vision  →  title + description + keywords + board category
                                         │
                                         ▼
                              Pinterest API v5  →  pin created on the right board
```

1. **Image discovery** — scans `./images/` for `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` files.
2. **AI analysis** — sends each image to GPT-4o with a prompt tuned for Etsy/Pinterest marketing.
3. **Board resolution** — automatically finds or creates the matching board on your Pinterest account.
4. **Pin creation** — uploads the image file and creates the pin with the generated metadata.
5. **Duplicate tracking** — `posted_images.json` records what has already been posted so re-runs are safe.

---

## Setup

### 1 — Clone & install dependencies

```bash
cd pinterest-auto
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2 — Create your `.env` file

```bash
cp .env.example .env
```

Then fill in the values:

| Variable | Where to get it |
|---|---|
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `PINTEREST_ACCESS_TOKEN` | [developers.pinterest.com](https://developers.pinterest.com/) → create an app → generate token |
| `ETSY_SHOP_NAME` | Your Etsy shop name |
| `ETSY_SHOP_URL` | `https://www.etsy.com/shop/YourShopName` |
| `IMAGE_FOLDER` | Path to your product image folder (default: `./images`) |

**Pinterest token scopes required:** `boards:read`, `boards:write`, `pins:read`, `pins:write`, `media:write`

### 3 — Add your images

```bash
mkdir images
cp /path/to/your/product/photos/*.jpg images/
```

### 4 — Run

```bash
# Post all new images
python main.py

# Analyze only — print metadata without posting anything
python main.py --dry-run

# Post at most 5 pins this run
python main.py --limit 5

# Use a different image folder
python main.py --folder /path/to/photos

# Re-post images that were already posted
python main.py --repost
```

---

## File structure

```
pinterest-auto/
├── main.py              # Entry point & orchestration
├── image_analyzer.py    # GPT-4o Vision → title/description/keywords/board
├── pinterest_client.py  # Pinterest API v5 wrapper (boards + pins)
├── config.py            # Loads settings from .env
├── requirements.txt
├── .env.example         # Copy to .env and fill in secrets
├── .gitignore
└── images/              # Put your product photos here (gitignored)
```

---

## Board categories

The AI picks one of the following board categories per image. Boards are created automatically if they don't exist on your account:

- Home Decor
- Fashion & Accessories
- Art & Prints
- Jewelry
- Wedding
- Baby & Kids
- Gifts
- Craft Supplies
- Seasonal & Holiday
- Food & Recipes
- Beauty & Skincare
- Stationery & Paper
- Other

You can override the mapping in `config.py` → `BOARD_MAP` to pin to specific existing board IDs.

