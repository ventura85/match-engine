from engine.comments import format_names


def test_placeholder_name_is_formatted_out():
    txt = "{name} strzela z dystansu!"
    out = format_names(txt, {"name": "Kowalski"})
    assert "{" not in out and "}" not in out
    assert "Kowalski" in out

