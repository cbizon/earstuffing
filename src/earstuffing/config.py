"""Configuration loading and keychain access."""

import subprocess
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main_checkout(root: Path) -> Path:
    """Return the main checkout of the repository containing root.

    Gitignored files (earstuffing.local.toml and the data/ symlink) exist only
    in the main checkout, not in worktrees, so they are resolved from there.
    """
    common_dir = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return Path(common_dir).parent


MAIN_ROOT = main_checkout(PROJECT_ROOT)
CONFIG_PATH = PROJECT_ROOT / "earstuffing.toml"
LOCAL_CONFIG_PATH = MAIN_ROOT / "earstuffing.local.toml"
REQUIRED = [("paths", "paperpile_dir"), ("paths", "bib_file"), ("tts", "endpoint")]


def merge(base: dict, override: dict) -> dict:
    """Recursively merge override into a copy of base."""
    out = dict(base)
    for key, value in override.items():
        out[key] = merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def load_config(path: Path = CONFIG_PATH, local_path: Path = LOCAL_CONFIG_PATH) -> dict:
    with path.open("rb") as f:
        config = tomllib.load(f)
    if local_path.exists():
        with local_path.open("rb") as f:
            config = merge(config, tomllib.load(f))
    missing = [f"{s}.{k}" for s, k in REQUIRED if not config[s][k]]
    if missing:
        raise RuntimeError(f"Set {', '.join(missing)} in {local_path.name}")
    paths = config["paths"]
    for key in ("paperpile_dir", "bib_file"):
        paths[key] = Path(paths[key]).expanduser()
    data_dir = Path(paths["data_dir"]).expanduser()
    paths["data_dir"] = data_dir if data_dir.is_absolute() else MAIN_ROOT / data_dir
    return config


def keychain_secret(service: str, account: str | None = None) -> str:
    """Return the password stored under a generic keychain item."""
    cmd = ["security", "find-generic-password", "-s", service, "-w"]
    if account:
        cmd += ["-a", account]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Keychain item {service!r} not found: {result.stderr.strip()}")
    return result.stdout.strip()


def keychain_account(service: str) -> str:
    """Return the account name stored on a generic keychain item."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Keychain item {service!r} not found: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith('"acct"<blob>='):
            return line.split("=", 1)[1].strip('"')
    raise RuntimeError(f"Keychain item {service!r} has no account name")
