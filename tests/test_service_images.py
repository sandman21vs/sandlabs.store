"""Tests for thumbnail generation helpers."""

from pathlib import Path

from PIL import Image

from services.service_images import ensure_thumbnail, generate_thumbnail, get_thumbnail_relpath


def _create_png(path: Path, size=(1200, 800), color=(240, 180, 30, 255)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, color).save(path, format="PNG")


def test_generate_thumbnail_creates_webp_and_resizes(tmp_path):
    source = tmp_path / "source.png"
    dest = tmp_path / "thumb" / "source.webp"
    _create_png(source, size=(1200, 600))

    generate_thumbnail(str(source), str(dest), max_width=400, quality=80)

    assert dest.exists()
    with Image.open(dest) as img:
        assert img.format == "WEBP"
        assert img.width == 400
        assert img.height == 200


def test_get_thumbnail_relpath_preserves_images_prefix():
    assert get_thumbnail_relpath("images/jade1.png") == "images/thumb/jade1.webp"
    assert get_thumbnail_relpath("jade1.png") == "images/thumb/jade1.webp"


def test_ensure_thumbnail_generates_and_returns_public_path(tmp_path):
    base_dir = tmp_path / "images"
    source = base_dir / "nested" / "jade1.png"
    _create_png(source, size=(1000, 500))

    public_path = ensure_thumbnail(str(base_dir), "images/nested/jade1.png")
    thumb_path = base_dir / "thumb" / "nested" / "jade1.webp"

    assert public_path == "images/thumb/nested/jade1.webp"
    assert thumb_path.exists()


def test_ensure_thumbnail_falls_back_for_missing_source(tmp_path):
    base_dir = tmp_path / "images"
    base_dir.mkdir()
    assert ensure_thumbnail(str(base_dir), "images/missing.png") == "images/missing.png"
