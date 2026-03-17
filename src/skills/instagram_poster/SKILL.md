---
name: instagram_poster
description: "Instagram content publishing skill. Renders HTML/CSS templates to images, uploads to Cloudinary, and publishes via Instagram Graph API."
entry_point: poster.py
---

# Instagram Poster

Automated Instagram publishing pipeline. It takes content, renders it into high-quality 1080x1080 images using HTML/CSS templates, uploads them to a CDN, and publishes them to an Instagram Business account.

### 🔧 Tools / Functions
- `upload_image(file_path)`: Upload a local image to Cloudinary and return the public URL.
- `create_media_container(image_url, caption)`: Create an Instagram media container for the given image and caption.
- `publish_media(creation_id)`: Finalize and publish the media container to the Instagram feed.
- `post_to_instagram(image_url, caption)`: Execute the full posting pipeline (create → publish).

### 📝 Examples
- "Post this image to Instagram with caption 'Hello World'" -> Post appears on the linked IG account.

### 🛠️ Requirements
- `cloudinary`, `requests`
- Instagram Business Account with Graph API Access Token
- Cloudinary API credentials (configured in `config.py`)
