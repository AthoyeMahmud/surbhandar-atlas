"""Run directly: python test_atlas.py."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from atlas import load_catalogue, map_payload, normalize, search_catalogue


def check():
    rows, index = load_catalogue()  # Validates all 10,819 rows and all 270,475 neighbour entries.
    assert normalize("  ARTIST—Song! ") == "artist song"
    assert normalize("বাংলা গান") == "বাংলা গান"
    sample = next(i for i, row in enumerate(rows) if row["artist"] and row["album"])
    assert sample in search_catalogue(index, rows[sample]["title"])
    assert sample in search_catalogue(index, rows[sample]["artist"])
    assert sample in search_catalogue(index, rows[sample]["album"])
    assert sample in search_catalogue(index, rows[sample]["aliases"][0])
    assert search_catalogue(index, "unlikely-no-match-9fe8ca79") == []
    payload = map_payload(rows, sample)
    assert len(payload["positions"]) == 10819
    assert payload["neighbors"] == rows[sample]["neighbors"]
    assert len(payload["labels"]) == 26
    assert set(payload) == {"positions", "bands", "selected", "neighbors", "matches", "focused", "labels", "revision"}
    assert all(set(label) == {"title", "artist"} for label in payload["labels"].values())
    empty = map_payload(rows)
    assert empty["neighbors"] == [] and empty["labels"] == {}

    app = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=30).run()
    assert not app.exception, [e.message for e in app.exception]
    app.text_input[0].set_value("unlikely-no-match-9fe8ca79").run()
    assert not app.exception and any("No matches" in info.value for info in app.info)
    app.text_input[0].set_value(rows[sample]["title"]).run()
    assert not app.exception
    app.button(key=f"search_{sample}").click().run()
    assert not app.exception and app.session_state["selected"] == sample
    neighbor = rows[sample]["neighbors"][0]
    assert sum((b.key or "").startswith("neighbor_") for b in app.button) == 25
    app.button(key=f"neighbor_{neighbor}").click().run()
    assert not app.exception and app.session_state["selected"] == neighbor
    app.toggle[0].set_value(True).run()
    assert not app.exception and app.session_state["focus"] is True
    next(b for b in app.button if b.label == "Reset view").click().run()
    assert not app.exception and app.session_state["selected"] is None
    assert app.session_state["focus"] is False
    next(b for b in app.button if b.label == "Surprise me").click().run()
    assert not app.exception and 0 <= app.session_state["selected"] < len(rows)
    print("PASS: full catalogue, exact neighbour order, search, payload boundary, and browsing controls")


if __name__ == "__main__":
    check()
