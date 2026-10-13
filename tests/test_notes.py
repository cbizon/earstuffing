import json

import pytest

from earstuffing import library, notes

METAS = [
    {"number": 1, "slug": "schatz", "title": "Explaining Drug Discovery Hypotheses Using Knowledge Graph Patterns"},
    {"number": 2, "slug": "hao", "title": "A unified framework for rule learning"},
    {"number": 14, "slug": "x", "title": "Something else"},
]


@pytest.mark.parametrize(
    "text, n",
    [("14", 14), ("fourteen", 14), ("twenty-one", 21), ("twenty one more", 21), ("forty", 40), ("two.", None)],
)
def test_words_to_number(text, n):
    if text == "two.":
        assert notes.spoken_number("Paper two. I wonder") == 2
    else:
        assert notes.words_to_number(text) == n


@pytest.mark.parametrize(
    "transcript, n",
    [("Paper 2: I wonder whether", 2), ("paper fourteen, how does", 14), ("Paper number 3.", 3),
     ("For paper two, I think", 2), ("Another note for paper two: I'm curious", 2),
     ("So, paper two is weak", 2), ("I wonder about papers", None),
     ("This one is long and only much later in the note do I say compare to paper one", None)],
)
def test_spoken_number(transcript, n):
    assert notes.spoken_number(transcript) == n


def test_match_spoken_overrides_playing():
    sidecar = {"media_title": "1 · Explaining Drug Discovery Hypotheses Using Knowledge Graph Patterns"}
    meta, how = notes.match_episode(sidecar, "Paper 2: thought", METAS)
    assert meta["slug"] == "hao" and how == "spoken paper 2"


def test_match_from_playing_title_number_and_text():
    meta, _ = notes.match_episode({"media_title": "14 · Something else"}, "a thought", METAS)
    assert meta["slug"] == "x"
    meta, how = notes.match_episode({"media_title": "A unified framework for rule learning"}, "hmm", METAS)
    assert meta["slug"] == "hao" and how == "playing in Pocket Casts"


def test_match_unknown_spoken_number_is_unmatched():
    meta, how = notes.match_episode({"media_title": "1 · Explaining"}, "Paper 9, something", METAS)
    assert meta is None and how == "spoken paper 9"


def test_no_match():
    meta, _ = notes.match_episode({"media_title": "Some other podcast"}, "remember milk", METAS)
    assert meta is None


def test_vocabulary_prompt_newest_first_and_capped():
    prompt = notes.vocabulary_prompt(METAS, ["AMIE", "LLM"], limit=120)
    assert "Terms: AMIE, LLM." in prompt
    assert "Something else" in prompt and "Explaining" not in prompt
    assert len(prompt) <= 120


def test_file_note_and_processed(tmp_path):
    library.create_episode(tmp_path, {"slug": "hao", "title": "T", "authors": [], "year": "", "venue": "", "doi": "", "url": ""})
    meta = library.read_meta(tmp_path, "hao")
    sidecar = {"id": "n1", "recorded_at": "2026-10-11T12:00:00+00:00", "media_title": "1 · T", "position_ms": 400000}
    entry = notes.note_entry(sidecar, "Paper 1: good point.", "spoken paper 1")
    assert '_Matched by spoken paper 1. Recorded 6:40 into "1 · T"._' in entry
    path = notes.file_note(tmp_path, meta, entry)
    assert path == tmp_path / "episodes" / "hao" / "notes.md"
    assert "Paper 1: good point." in path.read_text()
    unmatched = notes.file_note(tmp_path, None, entry)
    assert unmatched == tmp_path / "notes" / "unmatched.md"
    notes.mark_processed(tmp_path, "n1")
    assert notes.processed_ids(tmp_path) == {"n1"}


@pytest.mark.integration
def test_transcribe_real_audio(tmp_path):
    from earstuffing import tts
    from earstuffing.config import keychain_secret, load_config

    config = load_config()
    key = keychain_secret(config["tts"]["keychain_service"], config["tts"]["keychain_account"])
    audio = tmp_path / "note.mp3"
    tts.render("Paper fourteen. I wonder whether the AMIE rules from ROBOKOP hold up.", audio, config["tts"], key)
    text = notes.transcribe(audio, config["transcribe"], config["tts"]["endpoint"], key, "ROBOKOP, AMIE")
    assert notes.spoken_number(text) == 14
    assert "ROBOKOP" in text
