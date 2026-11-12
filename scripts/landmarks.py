# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Named places of Helenaveen: style overrides and extra geometry for buildings, plus the viewer's place list.

Sources: Monumenten in Nederland, Noord-Brabant (1997), Rijksmonumenten photos on Wikimedia Commons,
OpenStreetMap, and AHN for tower positions and heights.

Output: data/build/landmarks.json
"""

import json

import numpy as np

from config import BUILD, RAW
from geo import wgs_to_rd

# Local stories supplied by the resident; address positions resolved from BAG.
BUILDINGS = []
POINTS = [
    {"name": "Jutfaseweg 42", "addr": "Jutfaseweg 42", "kind": "Buurtverhaal", "text": 'Hier wonen de "tweendjes van de buurt".', "address": "Jutfaseweg 42, Utrecht"},
    {"name": "Amaliastraat 53", "addr": "Amaliastraat 53", "kind": "Buurtverhaal", "text": "De woning van de opperbaas van de regio. Een bewonersbijdrage voor deze kaart.", "address": "Amaliastraat 53, Utrecht"},
]
POINTS += [{'name': 'Mobach Keramiek', 'latlon': (52.0702362, 5.1104442), 'kind': 'In en rond Rivierenwijk', 'text': 'Keramiek aan de Jutfaseweg: een herkenningspunt langs de Vaartsche Rijn en een plek waar de wijk aan het water raakt.', 'more': 'https://www.openstreetmap.org/node/34050700'}, {'name': 'Meisje met schelp', 'latlon': (52.0733002, 5.12095), 'kind': 'In en rond Rivierenwijk', 'text': 'Een klein kunstwerk tussen de woonstraten. Juist zulke plekken maken een wandeling door de wijk persoonlijk.', 'more': 'https://www.openstreetmap.org/node/8586709855'}, {'name': 'Nieuw Rotsoord stadsboerderij', 'latlon': (52.07408004516128, 5.122222538709678), 'kind': 'In en rond Rivierenwijk', 'text': 'Een groene ontmoetingsplek aan de overkant van het water, voor een uitstapje vanuit de wijk.', 'more': 'https://www.openstreetmap.org/way/107339388'}, {'name': 'Watertoren Utrecht (Heuveloord)', 'latlon': (52.075496059016395, 5.120785581967213), 'kind': 'In en rond Rivierenwijk', 'text': 'Aan de overkant van de Vaartsche Rijn markeert de watertoren Rotsoord: een opvallend oriëntatiepunt vanuit Rivierenwijk.', 'more': 'https://www.openstreetmap.org/way/299564140'}]
CATEGORIES = [("buurtverhalen", "Buurtverhalen", ["Amaliastraat 53", "Jutfaseweg 42"]), ("ontdekken", "In en rond de wijk", ['Mobach Keramiek', 'Meisje met schelp', 'Nieuw Rotsoord stadsboerderij', 'Watertoren Utrecht (Heuveloord)'])]

# What the viewer shows when a place is clicked; the rest of an entry is for the render.
INFO = ("note", "kind", "text", "address", "web", "more", "photo", "stop")

# A steel lattice telecom mast next to the A67 (three antenna entries in OSM, one structure in AHN).
MASTS = []


def point_in_ring(x, y, ring):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, np.roll(ring, -1, axis=0)):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


ADDRESSES = None


def address_xy(name):
    """RD position of a BAG address such as "Geldersestraat 3" (data/raw/addresses.json, from scripts/fetch.py)."""
    global ADDRESSES
    if ADDRESSES is None:
        ADDRESSES = {label.replace(", Utrecht", "").split(", ")[0]: (x, y) for x, y, label in json.loads((RAW / "addresses.json").read_text())}
    return ADDRESSES[name]


def building_at(rings, x, y):
    for rid, ring, a in rings:
        if point_in_ring(x, y, ring):
            return rid, a
    return None, None


def main():
    feats = [json.loads(line) for line in open(RAW / "3dbag.jsonl")]
    rings = []
    for f in feats:
        t = f["transform"]
        V = np.array(f["vertices"], dtype=np.float64) * t["scale"] + t["translate"]
        co = f["CityObjects"][f["id"]]
        rings.append((f["id"], V[co["geometry"][0]["boundaries"][0][0]][:, :2], co["attributes"]))

    out = {"buildings": {}, "places": [], "masts": [], "hotspots": [], "categories": []}
    for b in BUILDINGS:
        if "addrs" in b:
            pts = [address_xy(a) for a in b["addrs"]]
            pids = [building_at(rings, *pt)[0] for pt in pts]
            assert all(pids), f"{b['name']}: no building at {b['addrs']}"
            x, y = np.mean(pts, axis=0)
            out["places"].append({"name": b["name"], "note": b.get("note"), "x": x, "y": y, "h": 4.0})
            out["hotspots"].append({"name": b["name"], "pids": pids, "x": x, "y": y, **{k: b[k] for k in INFO if k in b}})
            print(f"{b['name']}: {', '.join(pids)}")
            continue
        x, y = b["at"] if "at" in b else wgs_to_rd(*b["latlon"])
        pid, attrs = None, None
        for rid, ring, a in rings:
            if point_in_ring(x, y, ring):
                pid, attrs = rid, a
                break
        if pid is None:
            d = [(np.hypot(*(ring.mean(0) - (x, y))), rid, a) for rid, ring, a in rings]
            dist, pid, attrs = min(d, key=lambda t: t[0])
            if dist > 20:
                pid = None
        height = ((attrs or {}).get("b3_h_dak_max") or 0) - ((attrs or {}).get("b3_h_maaiveld") or 0)
        if "tower" in b:
            height = b["tower"]["top"]
        elif "turret" in b:
            height = b["turret"]["top"]
        out["places"].append({"name": b["name"], "note": b.get("note"), "x": x, "y": y, "h": round(height, 1)})
        if pid and "style" in b:
            out["buildings"][pid] = {k: v for k, v in b.items() if k not in ("at", "latlon", *INFO)}
        if pid:
            out["hotspots"].append({"name": b["name"], "pid": pid, "x": x, "y": y, **{k: b[k] for k in INFO if k in b}})
        print(f"{b['name']}: {pid or 'no building'}")
    for p in POINTS:
        x, y = p["at"] if "at" in p else address_xy(p["addr"]) if "addr" in p else wgs_to_rd(*p["latlon"])
        out["places"].append({"name": p["name"], "note": p.get("note"), "x": x, "y": y, "h": 2.0})
        out["hotspots"].append({"name": p["name"], "x": x, "y": y, **{k: p[k] for k in INFO if k in p}})
    for m in MASTS:
        x, y = wgs_to_rd(*m["latlon"])
        out["masts"].append({**{k: v for k, v in m.items() if k != "latlon"}, "x": x, "y": y})
    names = {h["name"] for h in out["hotspots"]}
    for key, label, members in CATEGORIES:
        missing = [n for n in members if n not in names]
        assert not missing, f"{label}: no hotspot for {missing}"
        out["categories"].append({"key": key, "label": label, "names": members})
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "landmarks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
