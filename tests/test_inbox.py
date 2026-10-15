from earstuffing import inbox, library


def make_episode(data_dir, slug, rendered_at=None):
    library.create_episode(data_dir, {"slug": slug, "title": slug.upper(), "authors": [], "year": "",
                                      "venue": "", "doi": "", "url": ""})
    if rendered_at:
        library.update_meta(data_dir, slug, rendered_at=rendered_at)
    return library.episode_dir(data_dir, slug)


def test_first_review_shows_everything_then_only_additions(tmp_path):
    a = make_episode(tmp_path, "a", rendered_at="2026-10-01T00:00:00+00:00")
    make_episode(tmp_path, "b")
    (a / library.DISCUSSION).write_text("## Re: note 1\n\nFirst reply.\n")

    items = inbox.collect(tmp_path)
    assert [i["slug"] for i in items] == ["a"]
    assert items[0]["new_episode"] is True
    assert "First reply." in items[0]["new_discussion"]

    inbox.mark_reviewed(tmp_path)
    assert inbox.collect(tmp_path) == []

    with (a / library.DISCUSSION).open("a") as f:
        f.write("\n## Re: note 2\n\nSecond reply.\n")
    (item,) = inbox.collect(tmp_path)
    assert item["new_episode"] is False
    assert "Second reply." in item["new_discussion"]
    assert "First reply." not in item["new_discussion"]


def test_new_episode_after_review(tmp_path):
    make_episode(tmp_path, "a", rendered_at="2026-10-01T00:00:00+00:00")
    inbox.mark_reviewed(tmp_path)
    make_episode(tmp_path, "b", rendered_at="2999-01-01T00:00:00+00:00")
    (item,) = inbox.collect(tmp_path)
    assert item["slug"] == "b" and item["new_episode"] is True and item["new_discussion"] == ""


def test_hand_edited_discussion_is_shown_in_full(tmp_path):
    a = make_episode(tmp_path, "a")
    (a / library.DISCUSSION).write_text("A long first version of the discussion.\n")
    inbox.mark_reviewed(tmp_path)
    (a / library.DISCUSSION).write_text("Short.\n")
    (item,) = inbox.collect(tmp_path)
    assert item["discussion_edited"] is True
    assert item["new_discussion"] == "Short."
