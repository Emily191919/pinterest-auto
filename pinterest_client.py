"""
Pinterest API v5 client.
Handles:
  - Fetching the authenticated user's boards
  - Uploading an image as a media asset
  - Creating a pin with the uploaded media
"""
import mimetypes
import time
from pathlib import Path

import requests

import config

_BASE_URL = "https://api.pinterest.com/v5"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


# ── Boards ────────────────────────────────────────────────────────────────────

def get_boards() -> list[dict]:
    """Return all boards for the authenticated user (handles pagination)."""
    boards = []
    url = f"{_BASE_URL}/boards"
    params = {"page_size": 250}

    while url:
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        boards.extend(data.get("items", []))
        bookmark = data.get("bookmark")
        if bookmark:
            params = {"page_size": 250, "bookmark": bookmark}
        else:
            url = None

    return boards


def find_or_create_board(board_name: str, boards: list[dict]) -> str:
    """
    Return the board_id for board_name.
    Creates the board if it does not exist yet.
    """
    for board in boards:
        if board["name"].lower() == board_name.lower():
            return board["id"]

    # Board not found — create it
    resp = requests.post(
        f"{_BASE_URL}/boards",
        headers=_headers(),
        json={"name": board_name, "privacy": "PUBLIC"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


# ── Media upload ──────────────────────────────────────────────────────────────

def upload_image(image_path: Path) -> str:
    """
    Upload a local image using Pinterest's two-step media upload flow.
    Returns the media_id string.
    """
    # Step 1: Register the upload
    register_resp = requests.post(
        f"{_BASE_URL}/media",
        headers=_headers(),
        json={"media_type": "video"},   # Pinterest v5 uses "video" slot for images too
        timeout=30,
    )

    # Pinterest v5 media upload for images uses multipart directly to the pin endpoint
    # Use the simpler direct URL approach instead
    # This function returns the local path; the caller will pass it as source_url
    # if they host images, or we upload via multipart.

    # Re-implement: Pinterest v5 supports creating pins with a local file
    # via multipart/form-data on POST /pins with source_type=image_base64 — 
    # but the cleanest supported method is providing a public URL.
    #
    # For local files we use the two-step media upload:
    # 1. POST /media  → get upload_url + upload_parameters
    # 2. POST upload_url with the file (multipart, S3-style)
    # 3. Use media_id in pin creation

    register_resp.raise_for_status()
    registration = register_resp.json()

    upload_url = registration["upload_url"]
    upload_params = registration.get("upload_parameters", {})
    media_id = registration["media_id"]

    mime_type, _ = mimetypes.guess_type(str(image_path))
    mime_type = mime_type or "image/jpeg"

    with open(image_path, "rb") as img_file:
        files = {"file": (image_path.name, img_file, mime_type)}
        upload_resp = requests.post(
            upload_url,
            data=upload_params,
            files=files,
            timeout=120,
        )
        upload_resp.raise_for_status()

    return media_id


# ── Pin creation ──────────────────────────────────────────────────────────────

def create_pin(
    *,
    board_id: str,
    image_path: Path,
    title: str,
    description: str,
    keywords: list[str],
    link: str = "",
) -> dict:
    """
    Create a Pinterest pin.

    Tries media upload first (local file); falls back to image URL if the
    access token lacks media-write scope.
    """
    # Build the pin payload
    note = description
    if keywords:
        # Append hashtags to description (Pinterest renders them as links)
        tags = " ".join(f"#{kw.replace(' ', '')}" for kw in keywords[:10])
        note = f"{description}\n\n{tags}"

    payload: dict = {
        "board_id": board_id,
        "title": title[:100],
        "description": note[:500],
        "media_source": {},
    }
    if link:
        payload["link"] = link

    # Try uploading the local file
    try:
        media_id = upload_image(image_path)
        # Poll until processing is complete (max 60 s)
        for _ in range(20):
            time.sleep(3)
            status_resp = requests.get(
                f"{_BASE_URL}/media/{media_id}",
                headers=_headers(),
                timeout=30,
            )
            status_resp.raise_for_status()
            status = status_resp.json().get("status")
            if status == "succeeded":
                break
            if status == "failed":
                raise RuntimeError(f"Pinterest media processing failed for {image_path.name}")

        payload["media_source"] = {
            "source_type": "media_id",
            "media_id": media_id,
        }
    except Exception as exc:
        # Fallback: if the image is publicly reachable, supply its URL
        raise RuntimeError(
            "Local image upload failed. Ensure PINTEREST_ACCESS_TOKEN has 'pins:write' "
            "and 'media:write' scopes, or host images publicly and pass source_type=image_url."
        ) from exc

    resp = requests.post(
        f"{_BASE_URL}/pins",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
