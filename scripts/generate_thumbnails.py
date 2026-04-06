"""Generate thumbnails for all images in static/images/."""

import os
import sys


ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from services.service_images import THUMB_DIR, ensure_thumbnail, get_thumbnail_relpath


IMAGES_DIR = os.path.join(ROOT, "static", "images")


def main():
    created = 0
    existing = 0

    for dirpath, _dirnames, filenames in os.walk(IMAGES_DIR):
        rel_dir = os.path.relpath(dirpath, IMAGES_DIR)
        if rel_dir == THUMB_DIR or rel_dir.startswith(f"{THUMB_DIR}{os.sep}"):
            continue

        for fname in sorted(filenames):
            rel_file = fname if rel_dir == "." else os.path.join(rel_dir, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue

            thumb_public_before = get_thumbnail_relpath(rel_file)
            thumb_rel_before = thumb_public_before.replace("images/", "", 1) if thumb_public_before.startswith("images/") else thumb_public_before
            thumb_path = os.path.join(IMAGES_DIR, thumb_rel_before)
            already_exists = os.path.exists(thumb_path)
            thumb_public = ensure_thumbnail(IMAGES_DIR, rel_file)
            thumb_rel = thumb_public.replace("images/", "", 1) if thumb_public.startswith("images/") else thumb_public
            if os.path.exists(thumb_path):
                if already_exists:
                    existing += 1
                else:
                    created += 1
            print(f"{rel_file} -> {thumb_rel}")

    print(f"Processed thumbnails: created={created} existing={existing}")


if __name__ == "__main__":
    main()
