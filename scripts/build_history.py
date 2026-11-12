"""Resident stories form the Rivierenwijk tour; no Helenaveen content."""
import json
import urllib.request
import urllib.parse
import urllib.error
import time
from config import BUILD

def commons_thumb(name, width=960):  # Wikimedia only serves a fixed set of thumbnail widths
    h = hashlib.md5(name.encode()).hexdigest()
    q = urllib.parse.quote(name)
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{width}px-{q}"


def download(url, tries=6):
    """Wikimedia rate-limits bursts of thumbnail requests; wait politely and retry."""
    req = urllib.request.Request(url, headers={"User-Agent": "isometric-helenaveen/0.1 (personal map)"})
    for attempt in range(tries):
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
            time.sleep(3)
            return data
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(15 * (attempt + 1))



def main():
    landmarks = json.loads((BUILD / "landmarks.json").read_text())
    stops = [{"n": i, "year": "Buurtverhaal", "title": p["name"], "text": p.get("text", ""), "x": p["x"], "y": p["y"], "h": 0, "zoom": 1.2, "photos": [], "source": {"label": "OpenStreetMap" if p.get("more") else "Bewonersbijdrage", "url": p.get("more", "#Amaliastraat-53")}} for i, p in enumerate(landmarks["hotspots"], 1)]
    (BUILD / "history").mkdir(parents=True, exist_ok=True)
    (BUILD / "history.json").write_text(json.dumps({"stops": stops}, ensure_ascii=False))

if __name__ == "__main__":
    main()
