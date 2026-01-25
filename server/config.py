import os

from dotenv import load_dotenv

load_dotenv()

# ---- Server hostname ----

HOSTNAME = os.environ.get("HOSTNAME")
if not HOSTNAME:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

SERVICE_DID = os.environ.get("SERVICE_DID") or f"did:web:{HOSTNAME}"

# ---- API client login ----

HANDLE = os.environ.get("HANDLE")
PASSWORD = os.environ.get("PASSWORD")

# ---- Feed URIs ----

LOVELIVE_URI = os.environ.get("LOVELIVE_URI")
if not LOVELIVE_URI:
    raise RuntimeError(
        "Publish your feed first (run publish_feed.py) to obtain its URI. "
        'Set this URI to "LOVELIVE_URI" environment variable.'
    )

# ---- User list URIs ----

LOVELIVE_INCLUDE_LIST_URI = os.environ.get("LOVELIVE_INCLUDE_LIST_URI")
LOVELIVE_MEDIA_INCLUDE_LIST_URI = os.environ.get("LOVELIVE_MEDIA_INCLUDE_LIST_URI")
LOVELIVE_IGNORE_LIST_URI = os.environ.get("LOVELIVE_IGNORE_LIST_URI")

# ---- Database tuning pragmas ----

DB_MMAP_SIZE = int(os.environ.get("DB_MMAP_SIZE") or "134217728")  # default 128MB
DB_CACHE_SIZE = int(os.environ.get("DB_CACHE_SIZE") or "2000")
DB_JOURNAL_SIZE_LIMIT = int(os.environ.get("DB_JOURNAL_SIZE_LIMIT") or "134217728")
DB_WAL_AUTOCHECKPOINT = int(os.environ.get("DB_WAL_AUTOCHECKPOINT") or "100")

# ---- Firehose relay hostnames ----

REPOS_FIREHOSE_HOSTNAME = os.environ.get("REPOS_FIREHOSE_HOSTNAME")
