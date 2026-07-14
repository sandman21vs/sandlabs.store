import os

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-please")
# BIP39 mnemonic used as the master secret for PII encryption + blind indexes.
# Preferred over SHIPPING_DATA_KEY; the latter is kept for backward compat and
# as a dev fallback. Keep this out of the database and out of version control.
MASTER_MNEMONIC = os.environ.get("MASTER_MNEMONIC", "")
MASTER_MNEMONIC_PASSPHRASE = os.environ.get("MASTER_MNEMONIC_PASSPHRASE", "")
SHIPPING_DATA_KEY = os.environ.get("SHIPPING_DATA_KEY", "")
DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "data", "sandlabs.db"),
)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
COINOS_API_KEY = os.environ.get("COINOS_API_KEY", "")
COINOS_WEBHOOK_SECRET = os.environ.get("COINOS_WEBHOOK_SECRET", "")
COINOS_ENABLED = os.environ.get("COINOS_ENABLED", "0") == "1"
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
