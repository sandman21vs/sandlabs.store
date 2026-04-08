import json
import os
from copy import deepcopy

from flask import g, has_request_context, redirect, request, session, url_for


SUPPORTED_LANGS = ("pt", "en", "es", "de")
DEFAULT_LANG = "pt"
_TRANSLATIONS = {}


def _translations_root():
    return os.path.join(os.path.dirname(__file__), "translations")


def _deep_merge(base, extra):
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _load_lang(lang):
    lang_dir = os.path.join(_translations_root(), lang)
    merged = {}
    if not os.path.isdir(lang_dir):
        return merged

    for filename in sorted(os.listdir(lang_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(lang_dir, filename)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        _deep_merge(merged, data)
    return merged


def reload_translations():
    global _TRANSLATIONS
    loaded = {}
    for lang in SUPPORTED_LANGS:
        loaded[lang] = _load_lang(lang)
    _TRANSLATIONS = loaded


def _lookup(data, key):
    current = data
    for part in (key or "").split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def get_translations(lang):
    target = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    return deepcopy(_TRANSLATIONS.get(target, {}))


def get_lang(session, request):
    stored = session.get("lang")
    if stored in SUPPORTED_LANGS:
        return stored

    accept = request.headers.get("Accept-Language", "")
    for part in accept.split(","):
        code = part.strip().split(";")[0].split("-")[0].lower()
        if code in SUPPORTED_LANGS:
            return code
    return DEFAULT_LANG


def t(key, lang, **kwargs):
    value = _lookup(_TRANSLATIONS.get(lang, {}), key)
    if value is None and lang != DEFAULT_LANG:
        value = _lookup(_TRANSLATIONS.get(DEFAULT_LANG, {}), key)
    if value is None:
        value = key
    if kwargs and isinstance(value, str):
        return value.format(**kwargs)
    return value


def localize_products(products, lang):
    catalog = get_translations(lang).get("catalog", {})
    localized = []
    for product in products:
        item = deepcopy(product)
        product_keys = catalog.get("products", {}).get(product.get("id"), {})

        item["nome"] = product_keys.get("name", item.get("nome", ""))
        item["resumo"] = product_keys.get("summary", item.get("resumo", ""))
        item["detalhesHTML"] = product_keys.get("details_html", item.get("detalhesHTML", ""))
        item["buyButtonText"] = product_keys.get("buy_button_text", item.get("buyButtonText", ""))

        badge = item.get("badge")
        if badge and product_keys.get("badge_text"):
            badge["text"] = product_keys["badge_text"]

        price_map = product_keys.get("prices", {})
        for price in item.get("preco", []):
            key = str(price.get("id") or price.get("label") or "")
            localized_price = price_map.get(key) or price_map.get(price.get("label", ""))
            if localized_price:
                price["label"] = localized_price.get("label", price.get("label", ""))
                price["valor"] = localized_price.get("value", price.get("valor", ""))

        option_map = product_keys.get("options", {})
        for option in item.get("options", []):
            opt_key = option.get("title") or option.get("type")
            localized_option = option_map.get(opt_key, {})
            if localized_option.get("title"):
                option["title"] = localized_option["title"]
            for input_key in ("inputs", "input"):
                if input_key not in option or input_key not in localized_option:
                    continue
                localized_inputs = localized_option[input_key]
                if isinstance(option[input_key], list):
                    for entry, localized_entry in zip(option[input_key], localized_inputs):
                        entry["label"] = localized_entry.get("label", entry.get("label", ""))
                elif isinstance(option[input_key], dict):
                    option[input_key]["label"] = localized_inputs.get("label", option[input_key].get("label", ""))

        localized.append(item)
    return localized


def current_lang():
    if has_request_context():
        return getattr(g, "lang", session.get("lang", DEFAULT_LANG))
    return DEFAULT_LANG


def translate(key, **kwargs):
    return t(key, current_lang(), **kwargs)


def init_app(app):
    @app.before_request
    def _set_request_lang():
        lang = get_lang(session, request)
        session["lang"] = lang
        g.lang = lang

    @app.context_processor
    def _inject_i18n():
        lang = getattr(g, "lang", DEFAULT_LANG)
        return {
            "lang": lang,
            "supported_langs": SUPPORTED_LANGS,
            "t": lambda key, **kwargs: t(key, lang, **kwargs),
            "js_i18n": get_translations(lang),
        }

    @app.route("/set-lang/<lang>")
    def set_lang(lang):
        if lang in SUPPORTED_LANGS:
            session["lang"] = lang
        referrer = request.referrer
        if referrer:
            return redirect(referrer)
        return redirect(url_for("public.index"))


reload_translations()
