"""Image optimization helpers for product thumbnails."""

import os

from PIL import Image


THUMB_DIR = "thumb"
THUMB_MAX_WIDTH = 400
THUMB_QUALITY = 80
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def get_images_base_dir(app):
    return os.path.join(app.static_folder, "images")


def _normalize_relpath(filename):
    normalized = (filename or "").replace("\\", "/").lstrip("/")
    if normalized.startswith("images/"):
        return normalized[7:]
    return normalized


def _to_public_path(relpath):
    return f"images/{relpath.replace(os.sep, '/')}"


def get_thumbnail_relpath(filename):
    """Return the public thumbnail path for an image path."""
    relpath = _normalize_relpath(filename)
    if not relpath:
        return filename
    if relpath.startswith(f"{THUMB_DIR}/"):
        return _to_public_path(relpath)
    name, _ext = os.path.splitext(relpath)
    return _to_public_path(f"{THUMB_DIR}/{name}.webp")


def generate_thumbnail(source_path, dest_path, max_width=THUMB_MAX_WIDTH, quality=THUMB_QUALITY):
    """Resize image to max_width and save it as WebP."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with Image.open(source_path) as img:
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_size = (max_width, max(1, int(img.height * ratio)))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(dest_path, format="WEBP", quality=quality)


def ensure_thumbnail(base_dir, filename):
    """Generate a thumbnail when possible and return its public path."""
    relpath = _normalize_relpath(filename)
    if not relpath:
        return filename
    if relpath.startswith(f"{THUMB_DIR}/"):
        return _to_public_path(relpath)

    ext = os.path.splitext(relpath)[1].lower()
    if ext not in _IMAGE_EXTENSIONS:
        return filename

    source_path = os.path.join(base_dir, relpath)
    if not os.path.exists(source_path):
        return filename

    thumb_public = get_thumbnail_relpath(filename)
    thumb_rel = _normalize_relpath(thumb_public)
    thumb_path = os.path.join(base_dir, thumb_rel)
    if not os.path.exists(thumb_path):
        generate_thumbnail(source_path, thumb_path)
    return thumb_public
