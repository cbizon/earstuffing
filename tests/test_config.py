import pytest

from earstuffing.config import load_config, merge


def test_merge_nested():
    assert merge({"a": {"x": 1, "y": 2}, "b": 3}, {"a": {"y": 9}}) == {"a": {"x": 1, "y": 9}, "b": 3}


def test_local_overrides_and_required(tmp_path):
    base = tmp_path / "base.toml"
    base.write_text('[paths]\npaperpile_dir = ""\nbib_file = ""\ndata_dir = "data"\n[tts]\nendpoint = ""\n')
    local = tmp_path / "local.toml"
    with pytest.raises(RuntimeError, match="paths.paperpile_dir, paths.bib_file, tts.endpoint"):
        load_config(base, local)
    local.write_text('[paths]\npaperpile_dir = "~/pp"\nbib_file = "/b.bib"\n[tts]\nendpoint = "https://e"\n')
    config = load_config(base, local)
    assert config["paths"]["bib_file"].as_posix() == "/b.bib"
    assert config["paths"]["paperpile_dir"].name == "pp"
    assert config["tts"]["endpoint"] == "https://e"
