#!/usr/bin/env python3

# NO NEED TO TOUCH ANYTHING HERE, please add the variables below to .env instead

import os

import validators
from atproto import Client, models
from click import secho, style
from dotenv import load_dotenv
from tld import get_tld, update_tld_names

load_dotenv()

# YOUR bluesky handle
# Ex: user.bsky.social
HANDLE: str = os.environ.get("HANDLE")

# YOUR bluesky password, or preferably an App Password (found in your client settings)
# Ex: abcd-1234-efgh-5678
PASSWORD: str = os.environ.get("PASSWORD")

# The hostname of the server where feed server will be hosted
# Ex: feed.bsky.dev
HOSTNAME: str = os.environ.get("HOSTNAME")

# A short name for the record that will show in urls
# Lowercase with no spaces.
# Ex: whats-hot
RECORD_NAME: str = os.environ.get("RECORD_NAME")

# A display name for your feed
# Ex: What's Hot
DISPLAY_NAME: str = os.environ.get("DISPLAY_NAME")

# (Optional) A description of your feed
# Ex: Top trending content from the whole network
DESCRIPTION: str | None = os.environ.get("DESCRIPTION")

# (Optional) The path to an image to be used as your feed's avatar
# Ex: ./path/to/avatar.jpeg
AVATAR_PATH: str | None = os.environ.get("AVATAR_PATH")

# (Optional). Only use this if you want a service did different from did:web
SERVICE_DID: str | None = os.environ.get("SERVICE_DID")


def check_params():
    required_params = {
        "HANDLE": HANDLE,
        "PASSWORD": PASSWORD,
        "HOSTNAME": HOSTNAME,
        "RECORD_NAME": RECORD_NAME,
        "DISPLAY_NAME": DISPLAY_NAME,
    }
    missing_params = [item[0] for item in required_params.items() if not item[1]]
    if missing_params:
        raise RuntimeError(
            "Missing required parameters (add them to your .env file):"
            f" {', '.join(missing_params)}"
        )

    update_tld_names(fail_silently=True)
    if (
        validators.domain(HOSTNAME) is not True
        or get_tld(HOSTNAME, fail_silently=True, fix_protocol=True) is None
    ):
        raise RuntimeError(
            "HOSTNAME must be set to a valid internet domain for the feed to work"
        )


def main():
    check_params()

    client = Client()
    secho(f"Logging in to Bluesky as @{HANDLE}...")
    client.login(HANDLE, PASSWORD)

    feed_did = SERVICE_DID or f"did:web:{HOSTNAME}"

    avatar_blob = None
    if AVATAR_PATH:
        with open(AVATAR_PATH, "rb") as f:
            secho("Uploading feed avatar...")
            avatar_data = f.read()
            avatar_blob = client.upload_blob(avatar_data).blob

    secho("Sending feed info...")
    response = client.com.atproto.repo.put_record(
        models.ComAtprotoRepoPutRecord.Data(
            repo=client.me.did,
            collection=models.ids.AppBskyFeedGenerator,
            rkey=RECORD_NAME,
            record=models.AppBskyFeedGenerator.Record(
                did=feed_did,
                display_name=DISPLAY_NAME,
                description=DESCRIPTION,
                avatar=avatar_blob,
                created_at=client.get_current_time_iso(),
            ),
        )
    )

    secho("Successfully published!", fg="green")
    secho(f"Feed URI: {style(response.uri, underline=True)}", bold=True)


if __name__ == "__main__":
    main()
