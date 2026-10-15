import subprocess

import pytest

from earstuffing.config import load_config, main_checkout, merge, require_current


def test_merge_nested():
    assert merge({"a": {"x": 1, "y": 2}, "b": 3}, {"a": {"y": 9}}) == {"a": {"x": 1, "y": 9}, "b": 3}


def test_local_overrides_and_required(tmp_path):
    base = tmp_path / "base.toml"
    base.write_text('[paths]\npaperpile_dir = ""\nbib_file = ""\ndata_dir = "data"\naudio_cache = "~/c"\n[tts]\nendpoint = ""\n')
    local = tmp_path / "local.toml"
    with pytest.raises(RuntimeError, match="paths.paperpile_dir, paths.bib_file, tts.endpoint"):
        load_config(base, local)
    local.write_text('[paths]\npaperpile_dir = "~/pp"\nbib_file = "/b.bib"\n[tts]\nendpoint = "https://e"\n')
    config = load_config(base, local)
    assert config["paths"]["bib_file"].as_posix() == "/b.bib"
    assert config["paths"]["paperpile_dir"].name == "pp"
    assert config["tts"]["endpoint"] == "https://e"


def test_main_checkout_from_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "-C", str(repo), "init", "-q"], check=True)
    subprocess.run([*git, "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    worktree = tmp_path / "wt"
    subprocess.run([*git, "-C", str(repo), "worktree", "add", "-q", str(worktree)], check=True)
    assert main_checkout(repo) == repo.resolve()
    assert main_checkout(worktree) == repo.resolve()


def test_require_current(tmp_path):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    origin = tmp_path / "origin.git"
    subprocess.run([*git, "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    local, other = tmp_path / "local", tmp_path / "other"
    for clone in (local, other):
        subprocess.run([*git, "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
    subprocess.run([*git, "-C", str(other), "commit", "-q", "--allow-empty", "-m", "one"], check=True)
    subprocess.run([*git, "-C", str(other), "push", "-q", "origin", "HEAD:main"], check=True)
    subprocess.run([*git, "-C", str(local), "pull", "-q", "origin", "main"], check=True)
    require_current(local)

    subprocess.run([*git, "-C", str(other), "commit", "-q", "--allow-empty", "-m", "two"], check=True)
    subprocess.run([*git, "-C", str(other), "push", "-q", "origin", "HEAD:main"], check=True)
    with pytest.raises(RuntimeError, match="1 commit\\(s\\) behind origin/main"):
        require_current(local)
    # Local commits ahead of origin are fine.
    subprocess.run([*git, "-C", str(local), "pull", "-q", "origin", "main"], check=True)
    subprocess.run([*git, "-C", str(local), "commit", "-q", "--allow-empty", "-m", "local"], check=True)
    require_current(local)
