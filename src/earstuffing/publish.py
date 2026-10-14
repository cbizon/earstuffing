"""Upload episodes and the feed to Cloudflare R2."""

from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from earstuffing.config import keychain_account, keychain_secret
from earstuffing.feed import build_feed
from earstuffing.library import cached_audio, rendered_episodes


def r2_client(r2: dict):
    if not r2["account_id"]:
        raise RuntimeError("r2.account_id is not set in earstuffing.toml")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{r2['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=keychain_account(r2["keychain_service"]),
        aws_secret_access_key=keychain_secret(r2["keychain_service"]),
        region_name="auto",
    )


def _remote_rendered_at(client, bucket: str, key: str) -> str | None:
    """The rendered-at stamp on an uploaded episode, or None if it is not uploaded."""
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return None
        raise
    return head["Metadata"].get("rendered-at", "")


def feed_base_url(r2: dict) -> str:
    if not r2["public_url"] or not r2["prefix"]:
        raise RuntimeError("r2.public_url and r2.prefix must be set in earstuffing.toml")
    return f"{r2['public_url'].rstrip('/')}/{r2['prefix']}"


def publish(config: dict) -> tuple[list[str], str]:
    """Upload any missing episode audio, then rewrite the feed. Returns (uploaded slugs, feed URL).

    Local audio is transient: it is deleted from the cache once R2 has the current render.
    """
    r2, data_dir, audio_cache = config["r2"], config["paths"]["data_dir"], config["paths"]["audio_cache"]
    base_url = feed_base_url(r2)
    client = r2_client(r2)
    episodes = rendered_episodes(data_dir)

    uploaded = []
    for ep in episodes:
        key = f"{r2['prefix']}/episodes/{ep['slug']}.mp3"
        path: Path = cached_audio(audio_cache, ep["slug"])
        # Re-rendered audio replaces the uploaded copy.
        if _remote_rendered_at(client, r2["bucket"], key) != ep["rendered_at"]:
            if not path.exists():
                raise FileNotFoundError(f"{ep['slug']} is not on R2 and {path} is gone; re-render it")
            client.upload_file(
                str(path), r2["bucket"], key,
                ExtraArgs={"ContentType": "audio/mpeg", "Metadata": {"rendered-at": ep["rendered_at"]}},
            )
            uploaded.append(ep["slug"])
        path.unlink(missing_ok=True)

    client.put_object(
        Bucket=r2["bucket"],
        Key=f"{r2['prefix']}/feed.xml",
        Body=build_feed(episodes, config["feed"], base_url),
        ContentType="application/rss+xml",
        CacheControl="max-age=300",
    )
    return uploaded, f"{base_url}/feed.xml"
