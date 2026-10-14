from pathlib import Path

import pytest

from earstuffing import library

BIB = """@ARTICLE{Schaffer2021-xy,
  title   = "Mapping the multiscale structure of biological systems",
  author  = "Schaffer, Leah V and Ideker, Trey",
  journal = "Cell Syst.",
  year    =  2021,
  doi     = "10.1016/j.cels.2021.05.012"
}

@INPROCEEDINGS{Sap2018-ab,
  title     = "{ATOMIC}: An Atlas of Machine Commonsense for {If-Then} Reasoning",
  author    = "Sap, Maarten and Le Bras, Ronan",
  booktitle = "AAAI",
  year      =  2018,
  file      = "All Papers/S/renamed by hand.pdf"
}

@ARTICLE{Nofile2020-zz,
  title  = "A paper with no PDF",
  author = "Nobody, A",
  year   = 2020
}
"""


@pytest.fixture
def paperpile(tmp_path: Path) -> Path:
    root = tmp_path / "Paperpile"
    s = root / "All Papers" / "S"
    s.mkdir(parents=True)
    for name in [
        "Schaffer and Ideker 2021 - Mapping the multiscale structure of biological systems.pdf",
        "Sap et al. 2018 - ATOMIC - An Atlas of Machine Commonsense for If-Then Reasoning.pdf",
        "renamed by hand.pdf",
    ]:
        (s / name).write_bytes(b"%PDF-1.4")
    (root / "Listen.bib").write_text(BIB)
    return root


def test_read_bib(paperpile):
    entries = {e["key"]: e for e in library.read_bib(paperpile / "Listen.bib")}
    e = entries["Schaffer2021-xy"]
    assert e["slug"] == "schaffer2021-xy"
    assert e["authors"] == ["Leah V Schaffer", "Trey Ideker"]
    assert e["venue"] == "Cell Syst."
    assert e["year"] == "2021"
    assert entries["Sap2018-ab"]["title"] == "ATOMIC: An Atlas of Machine Commonsense for If-Then Reasoning"
    assert entries["Sap2018-ab"]["venue"] == "AAAI"


def test_find_pdf_by_title_and_file_field(paperpile):
    entries = {e["key"]: e for e in library.read_bib(paperpile / "Listen.bib")}
    pdfs = library.index_pdfs(paperpile)
    assert library.find_pdf(entries["Schaffer2021-xy"], paperpile, pdfs).name.startswith("Schaffer")
    assert library.find_pdf(entries["Sap2018-ab"], paperpile, pdfs).name == "renamed by hand.pdf"
    assert library.find_pdf(entries["Nofile2020-zz"], paperpile, pdfs) is None


def test_find_pdf_truncated_filename_title(paperpile):
    long_title = "A very long title that Paperpile will truncate when naming the file on disk"
    (paperpile / "All Papers" / "S" / "Smith 2020 - A very long title that Paperpile will.pdf").write_bytes(b"")
    entry = {"title": long_title, "file": ""}
    pdf = library.find_pdf(entry, paperpile, library.index_pdfs(paperpile))
    assert pdf.name == "Smith 2020 - A very long title that Paperpile will.pdf"


def test_find_pdf_middle_elided_filename_title(paperpile):
    title = (
        "A unified framework for rule learning: Integrating commonsense knowledge from "
        "LLMs with structured knowledge from knowledge graphs"
    )
    name = (
        "Hao et al. 2026 - A unified framework for rule learning - Integrating co ... "
        "e knowledge from LLMs with structured knowledge from knowledge graphs.pdf"
    )
    (paperpile / "All Papers" / "S" / name).write_bytes(b"")
    pdfs = library.index_pdfs(paperpile)
    assert library.find_pdf({"title": title, "file": ""}, paperpile, pdfs).name == name
    other = {"title": "A unified framework for something else entirely", "file": ""}
    assert library.find_pdf(other, paperpile, pdfs) is None


def test_episode_lifecycle(tmp_path):
    meta = {"slug": "x2020", "title": "T", "authors": [], "year": "", "venue": "", "doi": "", "url": ""}
    assert library.episode_status(tmp_path, "x2020") == "new"
    d = library.create_episode(tmp_path, meta)
    assert library.read_meta(tmp_path, "x2020")["number"] == 1
    library.create_episode(tmp_path, {**meta, "slug": "y2021"})
    assert library.read_meta(tmp_path, "y2021")["number"] == 2
    assert library.episode_status(tmp_path, "x2020") == "needs_script"
    with pytest.raises(FileExistsError):
        library.create_episode(tmp_path, meta)
    (d / library.SCRIPT).write_text("Hello.")
    (d / library.SUMMARY).write_text("Summary.")
    assert library.episode_status(tmp_path, "x2020") == "needs_audio"
    assert library.rendered_episodes(tmp_path) == []
    library.update_meta(tmp_path, "x2020", rendered_at="2026-10-11T12:00:00+00:00")
    # Rendered is recorded in meta.json; no local audio is kept.
    assert library.episode_status(tmp_path, "x2020") == "rendered"
    assert [m["slug"] for m in library.rendered_episodes(tmp_path)] == ["x2020"]


def test_hub_name_is_obsidian_safe():
    meta = {"number": 3, "title": "ATOMIC: An Atlas of [If-Then] Reasoning?  " + "word " * 50}
    name = library.hub_name(meta)
    assert name.startswith("Paper 3 - ATOMIC An Atlas of If-Then Reasoning word")
    assert not library.UNSAFE_NAME.search(name)
    assert len(name) <= 160 and not name.endswith(" ")


def test_write_hub(tmp_path):
    meta = {"slug": "x2020", "title": "Old title", "authors": ["A B", "C D"], "year": "2020",
            "venue": "", "doi": "10.1/x", "url": "", "pdf": "/papers/My Paper.pdf"}
    d = library.create_episode(tmp_path, meta)
    stale = library.write_hub(tmp_path, "x2020")
    assert stale.name == "Paper 1 - Old title.md"
    text = stale.read_text()
    assert text.startswith("---\nnumber: 1\n")
    assert '  - "Paper 1"' in text and "[PDF](<file:///papers/My%20Paper.pdf>)" in text
    assert "Script" not in text and "## Discussion" not in text

    library.update_meta(tmp_path, "x2020", title="New title", summary="It works.")
    (d / library.SCRIPT).write_text("Hello.")
    (d / library.DISCUSSION).write_text("# Discussion\n")
    hub = library.write_hub(tmp_path, "x2020")
    assert hub.name == "Paper 1 - New title.md" and not stale.exists()
    text = hub.read_text()
    assert "It works." in text
    assert "> ![[episodes/x2020/script.md]]" in text
    assert "![[episodes/x2020/discussion.md]]" in text and "## Voice notes" not in text
