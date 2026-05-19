"""
Pinterest Auto-Poster — main entry point.

Usage:
  python main.py                    # process all images in IMAGE_FOLDER
  python main.py --dry-run          # analyze images but don't post to Pinterest
  python main.py --folder ./pics    # override image folder
  python main.py --limit 5          # post at most 5 pins this run
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

import config
import image_analyzer
import pinterest_client

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Tracker file (remembers which images were already posted) ─────────────────
POSTED_LOG = Path("posted_images.json")


def load_posted() -> set:
    if POSTED_LOG.exists():
        return set(json.loads(POSTED_LOG.read_text()))
    return set()


def save_posted(posted: set) -> None:
    POSTED_LOG.write_text(json.dumps(sorted(posted), indent=2))


# ── Image discovery ───────────────────────────────────────────────────────────

def discover_images(folder: Path) -> list[Path]:
    images = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in config.SUPPORTED_EXTENSIONS:
            images.append(path)
    return images


# ── Board resolution ──────────────────────────────────────────────────────────

def resolve_board_id(board_category: str, boards: list[dict], board_cache: dict) -> str:
    """
    Map an AI-suggested board_category to a real Pinterest board id.
    Uses BOARD_MAP from config if available, otherwise auto-matches by name
    or creates a new board.
    """
    if board_category in config.BOARD_MAP:
        return config.BOARD_MAP[board_category]

    if board_category in board_cache:
        return board_cache[board_category]

    board_id = pinterest_client.find_or_create_board(board_category, boards)
    board_cache[board_category] = board_id
    return board_id


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-post Pinterest pins from local images.")
    parser.add_argument("--folder", default=config.IMAGE_FOLDER, help="Path to image folder.")
    parser.add_argument("--limit", type=int, default=config.MAX_PINS_PER_RUN,
                        help="Max pins to post (0 = unlimited).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze images and print metadata without posting.")
    parser.add_argument("--repost", action="store_true",
                        help="Re-post images that were already posted previously.")
    args = parser.parse_args()

    image_folder = Path(args.folder)
    if not image_folder.is_dir():
        log.error("Image folder not found: %s", image_folder)
        sys.exit(1)

    # Validate required env vars
    if not config.OPENAI_API_KEY:
        log.error("OPENAI_API_KEY is not set. Please check your .env file.")
        sys.exit(1)
    if not args.dry_run and not config.PINTEREST_ACCESS_TOKEN:
        log.error("PINTEREST_ACCESS_TOKEN is not set. Please check your .env file.")
        sys.exit(1)

    images = discover_images(image_folder)
    if not images:
        log.warning("No supported images found in %s", image_folder)
        return

    posted = load_posted()
    if not args.repost:
        images = [img for img in images if img.name not in posted]
        log.info("%d new image(s) to process (skipping %d already posted).",
                 len(images), len(posted) - (len(posted) - len(posted)))

    if args.limit > 0:
        images = images[: args.limit]

    log.info("Will process %d image(s).", len(images))

    # Fetch boards once (skip in dry-run)
    boards: list[dict] = []
    board_cache: dict = {}
    if not args.dry_run:
        log.info("Fetching Pinterest boards…")
        boards = pinterest_client.get_boards()
        log.info("Found %d board(s).", len(boards))

    success_count = 0
    fail_count = 0

    for idx, image_path in enumerate(images, start=1):
        log.info("[%d/%d] Analyzing %s …", idx, len(images), image_path.name)

        # ── 1. Analyze image ──────────────────────────────────────────────────
        try:
            metadata = image_analyzer.analyze_image(image_path)
        except Exception as exc:
            log.error("  ✗ Failed to analyze %s: %s", image_path.name, exc)
            fail_count += 1
            continue

        title = metadata.get("title", "")
        description = metadata.get("description", "")
        keywords = metadata.get("keywords", [])
        board_category = metadata.get("board_category", "Other")

        log.info("  Title      : %s", title)
        log.info("  Board      : %s", board_category)
        log.info("  Keywords   : %s", ", ".join(keywords[:5]) + ("…" if len(keywords) > 5 else ""))
        log.info("  Description: %s…", description[:80])

        if args.dry_run:
            print("\n--- DRY RUN METADATA ---")
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
            print("------------------------\n")
            success_count += 1
            continue

        # ── 2. Resolve board ──────────────────────────────────────────────────
        try:
            board_id = resolve_board_id(board_category, boards, board_cache)
            log.info("  Board ID   : %s", board_id)
        except Exception as exc:
            log.error("  ✗ Could not resolve board '%s': %s", board_category, exc)
            fail_count += 1
            continue

        # ── 3. Post pin ───────────────────────────────────────────────────────
        try:
            pin = pinterest_client.create_pin(
                board_id=board_id,
                image_path=image_path,
                title=title,
                description=description,
                keywords=keywords,
                link=config.ETSY_SHOP_URL,
            )
            pin_id = pin.get("id", "unknown")
            log.info("  ✓ Pin created: https://www.pinterest.com/pin/%s/", pin_id)
            posted.add(image_path.name)
            save_posted(posted)
            success_count += 1
        except Exception as exc:
            log.error("  ✗ Failed to post pin for %s: %s", image_path.name, exc)
            fail_count += 1

        # Rate-limit safety pause
        if idx < len(images):
            time.sleep(config.DELAY_BETWEEN_PINS)

    log.info("Done. %d posted, %d failed.", success_count, fail_count)


if __name__ == "__main__":
    main()
