"""
Uses OpenAI GPT-4o Vision to analyze a product image and generate
Pinterest-ready metadata: title, description, keywords, and board category.
"""
import base64
import json
import re
from pathlib import Path

from openai import OpenAI

import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are an expert Pinterest marketer and SEO copywriter specializing in Etsy shop promotion.
Analyze the product image and generate optimized Pinterest pin metadata.
Always respond with valid JSON only — no markdown fences, no extra text.
"""

_USER_PROMPT_TEMPLATE = """\
Analyze this product image for an Etsy shop called "{shop_name}".
{shop_url_hint}

Return a JSON object with exactly these keys:
{{
  "title": "Engaging Pinterest pin title (max 100 chars, include primary keyword near the start)",
  "description": "SEO-rich description (150-500 chars). Highlight product benefits, mention the Etsy shop, include a soft call-to-action. Do NOT use hashtags here.",
  "keywords": ["keyword1", "keyword2", ...],   // 10-15 highly relevant search keywords
  "board_category": "One of: Home Decor | Fashion & Accessories | Art & Prints | Jewelry | Wedding | Baby & Kids | Gifts | Craft Supplies | Seasonal & Holiday | Food & Recipes | Beauty & Skincare | Stationery & Paper | Other"
}}

Guidelines:
- Title: start with the product type, be descriptive, avoid clickbait
- Description: write naturally, weave in 3-5 keywords, end with shop link hint
- Keywords: mix broad (e.g. "handmade gifts") and specific (e.g. "personalized wooden name sign") terms
- board_category: choose the single best match from the list above
"""


def _encode_image(image_path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) for the given image file."""
    suffix = image_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def analyze_image(image_path: Path) -> dict:
    """
    Analyze a product image and return a dict with keys:
      title, description, keywords (list), board_category
    """
    b64, media_type = _encode_image(image_path)

    shop_url_hint = (
        f'The Etsy shop URL is: {config.ETSY_SHOP_URL}'
        if config.ETSY_SHOP_URL
        else ""
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": _USER_PROMPT_TEMPLATE.format(
                            shop_name=config.ETSY_SHOP_NAME,
                            shop_url_hint=shop_url_hint,
                        ),
                    },
                ],
            },
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences if the model adds them
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    metadata = json.loads(raw)

    # Normalise keywords to a flat list of strings
    if isinstance(metadata.get("keywords"), str):
        metadata["keywords"] = [k.strip() for k in metadata["keywords"].split(",")]

    return metadata
