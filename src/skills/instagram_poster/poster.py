# ============================================================
# skills/instagram_poster/poster.py — Cloudinary + Instagram
# ============================================================

import requests
import cloudinary
import cloudinary.uploader
from settings import settings as config
from skills.logger import log_audit, log_app

# ─── Cloudinary setup ──────────────────────────────────────
cloudinary.config(
    cloud_name=config.CLOUDINARY_CLOUD_NAME,
    api_key=config.CLOUDINARY_API_KEY,
    api_secret=config.CLOUDINARY_API_SECRET,
    secure=True,
)

GRAPH_API = "https://graph.facebook.com/v19.0"


# ─── Cloudinary ────────────────────────────────────────────
def upload_image(file_path: str) -> str:
    """Upload a local image to Cloudinary. Returns the public secure URL."""
    log_audit("CLOUDINARY_UPLOAD", f"Uploading image: {file_path}")

    try:
        result = cloudinary.uploader.upload(
            file_path,
            folder="instagram_posts",
            resource_type="image",
        )
        url = result.get("secure_url", "")
        log_audit("CLOUDINARY_UPLOAD", f"Upload success — URL: {url}")
        log_app(f"Cloudinary upload complete: {url}")
        return url

    except Exception as e:
        log_audit("CLOUDINARY_ERROR", f"Upload failed: {e}")
        log_app(f"Cloudinary error: {e}")
        raise


# ─── Instagram Graph API ──────────────────────────────────
def create_media_container(image_url: str, caption: str) -> str:
    """Create an Instagram media container. Returns creation_id."""
    log_audit("IG_CREATE_MEDIA", f"Creating media container — image: {image_url}")

    url = f"{GRAPH_API}/{config.IG_BUSINESS_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": config.INSTAGRAM_ACCESS_TOKEN,
    }

    resp = requests.post(url, data=payload, timeout=60)
    data = resp.json()
    log_audit("IG_CREATE_MEDIA", f"API response: {data}")

    if "id" not in data:
        error_msg = f"Instagram media creation failed: {data}"
        log_audit("IG_ERROR", error_msg)
        raise RuntimeError(error_msg)

    creation_id = data["id"]
    log_audit("IG_CREATE_MEDIA", f"Media container created — ID: {creation_id}")
    return creation_id


def publish_media(creation_id: str) -> str:
    """Publish the media container to Instagram. Returns post ID."""
    log_audit("IG_PUBLISH", f"Publishing media — creation_id: {creation_id}")

    url = f"{GRAPH_API}/{config.IG_BUSINESS_ID}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": config.INSTAGRAM_ACCESS_TOKEN,
    }

    resp = requests.post(url, data=payload, timeout=60)
    data = resp.json()
    log_audit("IG_PUBLISH", f"API response: {data}")

    if "id" not in data:
        error_msg = f"Instagram publish failed: {data}"
        log_audit("IG_ERROR", error_msg)
        raise RuntimeError(error_msg)

    post_id = data["id"]
    log_audit("IG_PUBLISH", f"Post published — ID: {post_id}")
    return post_id


async def post_to_instagram(image_url: str, caption: str, bot=None, chat_id=None) -> str:
    """
    Full Instagram posting pipeline: create container → publish.
    On error, logs full JSON and notifies via Telegram.
    """
    log_audit("IG_POST", "Starting full Instagram post flow")

    try:
        creation_id = create_media_container(image_url, caption)
        post_id = publish_media(creation_id)
        log_audit("IG_POST", f"✅ Successfully posted — Post ID: {post_id}")
        log_app(f"Instagram post published: {post_id}")
        return post_id

    except Exception as e:
        error_msg = f"❌ Instagram posting failed: {e}"
        log_audit("IG_POST_ERROR", error_msg)
        log_app(error_msg)

        if bot and chat_id:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ *Instagram Error*\n\n```\n{e}\n```",
                    parse_mode="Markdown",
                )
            except Exception as notify_err:
                log_audit("IG_NOTIFY_ERROR",
                          f"Failed to send Telegram error notification: {notify_err}")
        raise
