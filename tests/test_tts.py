import pytest

from earstuffing import tts
from earstuffing.config import keychain_secret, load_config


def test_chunk_text_packs_paragraphs():
    text = "\n\n".join(["a" * 40, "b" * 40, "c" * 40])
    assert tts.chunk_text(text, 90) == ["a" * 40 + "\n\n" + "b" * 40, "c" * 40]


def test_chunk_text_splits_long_paragraph_by_sentence():
    para = " ".join(["This is sentence number %d." % i for i in range(20)])
    chunks = tts.chunk_text(para, 100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks).replace("\n\n", " ").replace(" ", "") == para.replace(" ", "")


def test_chunk_text_rejects_oversized_sentence():
    with pytest.raises(ValueError):
        tts.chunk_text("x" * 200, 100)


@pytest.mark.integration
def test_render_real_audio(tmp_path):
    config = load_config()
    key = keychain_secret(config["tts"]["keychain_service"], config["tts"]["keychain_account"])
    out = tmp_path / "out.mp3"
    duration = tts.render("First paragraph.\n\nSecond paragraph.", out, config["tts"], key)
    assert out.stat().st_size > 1000
    assert 1 < duration < 20
