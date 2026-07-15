"""Static contracts for thumbnail loading and product image zoom."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_product_cards_use_lazy_webp_thumbnails_with_original_fallback():
    home_js = _read("static/js/render-home.js")
    products_js = _read("static/js/render-produtos.js")

    for source in (home_js, products_js):
        assert "thumb/${match[2]}.webp" in source
        assert "loading:" in source and "'lazy'" in source
        assert "decoding:" in source and "'async'" in source
        assert "addEventListener('error'" in source

    assert "const fullPaths = imagens.map((src) => src)" in products_js
    assert "lightbox.open(fullPaths, currentIndex)" in products_js


def test_lightbox_keeps_navigation_accessibility_and_adds_both_zoom_modes():
    lightbox_js = _read("static/js/lightbox.js")
    style_css = _read("static/css/style.css")

    for token in (
        "lightbox-zoom",
        "lightbox-highres",
        "zoom-lens",
        "backgroundPosition",
        "pointerdown",
        "pointermove",
        "lostpointercapture",
        "translate(${touchPanX}px, ${touchPanY}px)",
        "MAX_TOUCH_ZOOM",
        "ArrowLeft",
        "ArrowRight",
        "aria-hidden', 'false",
        "aria-hidden', 'true",
    ):
        assert token in lightbox_js

    for selector in (".lightbox-zoom", ".lightbox-highres", ".zoom-lens"):
        assert selector in style_css
