from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from services.service_btc_price import fiat_to_sats


SATS_CODE = "SATS"
PRICING_MODE_SATS = "sats"
PRICING_MODE_FIAT = "fiat"

SUPPORTED_FIAT_CURRENCIES = {
    "CHF": {"label": "Swiss Franc", "prefix": "CHF ", "decimals": 2},
    "USD": {"label": "US Dollar", "prefix": "USD ", "decimals": 2},
    "EUR": {"label": "Euro", "prefix": "EUR ", "decimals": 2},
    "BRL": {"label": "Brazilian Real", "prefix": "R$ ", "decimals": 2},
}

ADMIN_ENABLED_CURRENCIES = (SATS_CODE, "CHF")

_SATS_PATTERN = re.compile(r"([0-9\.\,\s]+)\s*sats", re.IGNORECASE)
_CURRENCY_PATTERNS = {
    "BRL": re.compile(r"R\$\s*([0-9\.\,\s]+)", re.IGNORECASE),
    "CHF": re.compile(r"CHF\s*([0-9\.\,\s]+)|([0-9\.\,\s]+)\s*CHF", re.IGNORECASE),
    "USD": re.compile(r"USD\s*([0-9\.\,\s]+)|\$\s*([0-9\.\,\s]+)", re.IGNORECASE),
    "EUR": re.compile(r"EUR\s*([0-9\.\,\s]+)|€\s*([0-9\.\,\s]+)", re.IGNORECASE),
}


def normalize_currency_code(currency_code):
    code = (currency_code or "").strip().upper()
    return code if code else None


def _to_decimal(value):
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value

    text = str(value).strip()
    if not text:
        return None
    text = text.replace(" ", "")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")

    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def normalize_decimal_string(value, currency_code):
    amount = _to_decimal(value)
    if amount is None:
        return None

    decimals = SUPPORTED_FIAT_CURRENCIES.get(currency_code, {}).get("decimals", 2)
    quant = Decimal("1").scaleb(-decimals)
    normalized = amount.quantize(quant, rounding=ROUND_HALF_UP)
    return format(normalized, f".{decimals}f")


def format_sats(amount_sats):
    return f"{int(amount_sats or 0):,} sats".replace(",", " ")


def format_fiat_display(amount_fiat, currency_code):
    code = normalize_currency_code(currency_code)
    meta = SUPPORTED_FIAT_CURRENCIES.get(code)
    if meta is None:
        return str(amount_fiat or "")

    normalized = normalize_decimal_string(amount_fiat, code)
    if normalized is None:
        return ""
    return f"{meta['prefix']}{normalized}"


def parse_legacy_display_price(display_text):
    text = (display_text or "").strip()
    if not text:
        return None

    sats_match = _SATS_PATTERN.search(text)
    if sats_match:
        digits = re.sub(r"[^\d]", "", sats_match.group(1) or "")
        if digits:
            return {
                "pricing_mode": PRICING_MODE_SATS,
                "currency_code": SATS_CODE,
                "amount_sats": int(digits),
                "amount_fiat": None,
            }

    for currency_code, pattern in _CURRENCY_PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        raw_amount = next((group for group in match.groups() if group), "")
        normalized = normalize_decimal_string(raw_amount, currency_code)
        if normalized is None:
            continue
        return {
            "pricing_mode": PRICING_MODE_FIAT,
            "currency_code": currency_code,
            "amount_fiat": normalized,
            "amount_sats": 0,
        }

    return None


def resolve_price_snapshot(price):
    price_data = dict(price or {})
    pricing_mode = (price_data.get("pricing_mode") or "").strip().lower()
    currency_code = normalize_currency_code(price_data.get("currency_code"))
    amount_sats = int(price_data.get("amount_sats") or 0)
    amount_fiat = price_data.get("amount_fiat")

    if pricing_mode == PRICING_MODE_FIAT and currency_code and currency_code != SATS_CODE:
        normalized_fiat = normalize_decimal_string(amount_fiat, currency_code)
        resolved_sats = fiat_to_sats(normalized_fiat or 0, currency_code) if normalized_fiat else 0
        display_text = price_data.get("display_text") or format_fiat_display(normalized_fiat, currency_code)
        return {
            **price_data,
            "pricing_mode": PRICING_MODE_FIAT,
            "currency_code": currency_code,
            "amount_fiat": normalized_fiat,
            "amount_sats": amount_sats,
            "resolved_amount_sats": resolved_sats,
            "display_text": display_text,
            "display_text_resolved": display_text,
            "sats_display": f"~{format_sats(resolved_sats)}" if resolved_sats > 0 else None,
        }

    if pricing_mode == PRICING_MODE_SATS or amount_sats > 0:
        display_text = price_data.get("display_text") or format_sats(amount_sats)
        return {
            **price_data,
            "pricing_mode": PRICING_MODE_SATS,
            "currency_code": SATS_CODE,
            "amount_fiat": None,
            "amount_sats": amount_sats,
            "resolved_amount_sats": amount_sats,
            "display_text": display_text,
            "display_text_resolved": display_text,
            "sats_display": display_text if amount_sats > 0 else None,
        }

    legacy = parse_legacy_display_price(price_data.get("display_text"))
    if legacy:
        return resolve_price_snapshot({**price_data, **legacy})

    return {
        **price_data,
        "pricing_mode": PRICING_MODE_SATS,
        "currency_code": currency_code or SATS_CODE,
        "amount_fiat": amount_fiat,
        "amount_sats": amount_sats,
        "resolved_amount_sats": 0,
        "display_text": price_data.get("display_text") or "",
        "display_text_resolved": price_data.get("display_text") or "",
        "sats_display": None,
    }


def normalize_price_record(price, index=0):
    raw = dict(price or {})
    label = (raw.get("label") or "").strip()
    if not label:
        raise ValueError("Price label is required.")

    pricing_mode = (raw.get("pricing_mode") or "").strip().lower()
    currency_code = normalize_currency_code(raw.get("currency_code"))

    if not pricing_mode:
        if currency_code and currency_code != SATS_CODE:
            pricing_mode = PRICING_MODE_FIAT
        elif raw.get("amount_fiat") not in (None, ""):
            pricing_mode = PRICING_MODE_FIAT
        elif int(raw.get("amount_sats") or 0) > 0:
            pricing_mode = PRICING_MODE_SATS
        else:
            legacy = parse_legacy_display_price(raw.get("display_text"))
            if legacy:
                pricing_mode = legacy["pricing_mode"]
                currency_code = legacy["currency_code"]
                raw.setdefault("amount_fiat", legacy.get("amount_fiat"))
                raw.setdefault("amount_sats", legacy.get("amount_sats", 0))
            else:
                pricing_mode = PRICING_MODE_SATS

    if pricing_mode == PRICING_MODE_FIAT:
        currency_code = currency_code or normalize_currency_code(raw.get("currency")) or "CHF"
        if currency_code == SATS_CODE:
            raise ValueError("Fiat prices must use a fiat currency code.")
        if currency_code not in SUPPORTED_FIAT_CURRENCIES:
            raise ValueError(f"Unsupported fiat currency: {currency_code}")

        amount_fiat = normalize_decimal_string(raw.get("amount_fiat"), currency_code)
        if amount_fiat is None or Decimal(amount_fiat) <= 0:
            raise ValueError(f"Fiat amount for '{label}' must be greater than zero.")

        return {
            "label": label,
            "pricing_mode": PRICING_MODE_FIAT,
            "currency_code": currency_code,
            "amount_fiat": amount_fiat,
            "amount_sats": int(raw.get("amount_sats") or 0),
            "display_text": raw.get("display_text") or format_fiat_display(amount_fiat, currency_code),
            "sort_order": int(raw.get("sort_order", index)),
        }

    amount_sats = int(raw.get("amount_sats") or 0)
    if amount_sats <= 0:
        raise ValueError(f"Sats amount for '{label}' must be greater than zero.")

    return {
        "label": label,
        "pricing_mode": PRICING_MODE_SATS,
        "currency_code": SATS_CODE,
        "amount_fiat": None,
        "amount_sats": amount_sats,
        "display_text": raw.get("display_text") or format_sats(amount_sats),
        "sort_order": int(raw.get("sort_order", index)),
    }
