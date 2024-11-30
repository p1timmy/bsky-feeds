import os

SERVICE_DID = os.environ.get("SERVICE_DID")
HOSTNAME = os.environ.get("HOSTNAME")


if not HOSTNAME:
    raise RuntimeError('You should set "HOSTNAME" environment variable first.')

if not SERVICE_DID:
    SERVICE_DID = f"did:web:{HOSTNAME}"


LOVELIVE_URI = os.environ.get("LOVELIVE_URI")
if not LOVELIVE_URI:
    raise RuntimeError(
        "Publish your feed first (run publish_feed.py) to obtain its URI. "
        'Set this URI to "LOVELIVE_URI" environment variable.'
    )
