import os

from dotenv import load_dotenv

load_dotenv()

HOSTNAME = os.environ.get("HOSTNAME")
if not HOSTNAME:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

SERVICE_DID = os.environ.get("SERVICE_DID")
if not SERVICE_DID:
    SERVICE_DID = f"did:web:{HOSTNAME}"


LOVELIVE_URI = os.environ.get("LOVELIVE_URI")
if not LOVELIVE_URI:
    raise RuntimeError(
        "Publish your feed first (run publish_feed.py) to obtain its URI. "
        'Set this URI to "LOVELIVE_URI" environment variable.'
    )


DB_MMAP_SIZE = int(os.environ.get("DB_MMAP_SIZE") or "134217728")  # default 128MB
DB_CACHE_SIZE = int(os.environ.get("DB_CACHE_SIZE") or "2000")
DB_JOURNAL_SIZE_LIMIT = int(os.environ.get("DB_JOURNAL_SIZE_LIMIT") or "134217728")
DB_WAL_AUTOCHECKPOINT = int(os.environ.get("DB_WAL_AUTOCHECKPOINT") or "100")
