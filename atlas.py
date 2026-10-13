"""Small server-side catalogue for the Atlas browser."""

import gzip
import json
import math
import unicodedata
from pathlib import Path


DATA = Path(__file__).parent / "data" / "atlas.json.gz"
FIELDS = {"title", "artist", "album", "aliases", "position", "band", "neighbors"}


def normalize(text):
    return " ".join("".join(
        c if unicodedata.category(c)[0] not in "PS" else " "
        for c in unicodedata.normalize("NFKC", text).casefold()
    ).split())


def load_catalogue():
    with gzip.open(DATA, "rt", encoding="utf-8") as file:
        rows = json.load(file)
    if len(rows) != 10819:
        raise ValueError("The Atlas catalogue is incomplete.")
    for index, row in enumerate(rows):
        if (set(row) != FIELDS or not isinstance(row["title"], str) or not row["title"]
                or not all(isinstance(row[k], str) for k in ("artist", "album"))
                or not isinstance(row["aliases"], list)
                or not all(isinstance(name, str) for name in row["aliases"])
                or len(row["position"]) != 3
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in row["position"])
                or row["band"] not in (0, 1, 2)
                or len(row["neighbors"]) != 25 or len(set(row["neighbors"])) != 25
                or index in row["neighbors"]
                or not all(type(n) is int and 0 <= n < len(rows) for n in row["neighbors"])):
            raise ValueError("The Atlas catalogue contains an invalid recording.")
    search_index = [normalize(" ".join([r["title"], r["artist"], r["album"], *r["aliases"]])) for r in rows]
    return rows, search_index


def search_catalogue(search_index, query):
    words = normalize(query).split()
    return [i for i, text in enumerate(search_index) if all(word in text for word in words)]


def map_payload(rows, selected=None, matches=(), focused=False, revision=0):
    """Full geometry/topology and current-selection labels cross the browser boundary."""
    neighbors = rows[selected]["neighbors"] if selected is not None else []
    labels = {str(i): {key: rows[i][key] for key in ("title", "artist")}
              for i in ([selected, *neighbors] if selected is not None else [])}
    return {"positions": [r["position"] for r in rows], "bands": [r["band"] for r in rows],
            "adjacency": [r["neighbors"] for r in rows],
            "selected": selected, "neighbors": neighbors, "matches": list(matches),
            "focused": focused, "labels": labels, "revision": revision}
