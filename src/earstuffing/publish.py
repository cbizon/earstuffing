"""Upload episodes and the feed to Cloudflare R2."""

from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from earstuffing.config import keychain_account, keychain_secret
from earstuffing.feed import build_feed
from earstuffing.library import AUDIO, episode_dir, rendered_episodes


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


def _exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise
    return True


def feed_base_url(r2: dict) -> str:
    if not r2["public_url"] or not r2["prefix"]:
        raise RuntimeError("r2.public_url and r2.prefix must be set in earstuffing.toml")
    return f"{r2['public_url'].rstrip('/')}/{r2['prefix']}"


def publish(config: dict) -> tuple[list[str], str]:
    """Upload any missing episode audio, then rewrite the feed. Returns (uploaded slugs, feed URL)."""
    r2, data_dir = config["r2"], config["paths"]["data_dir"]
    base_url = feed_base_url(r2)
    client = r2_client(r2)
    episodes = rendered_episodes(data_dir)

    uploaded = []
    for ep in episodes:
        key = f"{r2['prefix']}/episodes/{ep['slug']}.mp3"
        if not _exists(client, r2["bucket"], key):
            path: Path = episode_dir(data_dir, ep["slug"]) / AUDIO
            client.upload_file(str(path), r2["bucket"], key, ExtraArgs={"ContentType": "audio/mpeg"})
            uploaded.append(ep["slug"])

    client.put_object(
        Bucket=r2["bucket"],
        Key=f"{r2['prefix']}/feed.xml",
        Body=build_feed(episodes, config["feed"], base_url),
        ContentType="application/rss+xml",
        CacheControl="max-age=300",
    )
    return uploaded, f"{base_url}/feed.xml"
