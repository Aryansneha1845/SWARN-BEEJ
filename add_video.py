"""Curate Fasal Doctor videos. oEmbed verifies existence (no API key needed).
Usage:
  python add_video.py --list                        # DEMO vs verified status
  python add_video.py <problem_key> <youtube_id> [channel]
  python add_video.py --check <youtube_id>          # existence check only, no DB write
Get IDs by watching DD Kisan / ICAR / KVK / state-agri videos yourself.
NEVER mark a video verified without watching it.
"""
import json
import re
import sys
import urllib.request
from datetime import date

import app

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def oembed(ytid):
    url = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=" + ytid + "&format=json"
    with urllib.request.urlopen(url, timeout=12) as r:
        return json.load(r)


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        with app.get_con() as con:
            rows = con.execute("SELECT problem_key, youtube_id, channel, verified FROM videos ORDER BY problem_key").fetchall()
        for p, y, c, v in rows:
            print(f"{'OK ' if v else 'DEMO'} | {p:10} | {y or '-':12} | {c or '-'}")
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        ytid = sys.argv[2]
        assert ID_RE.match(ytid), "bad ID format"
        d = oembed(ytid)
        print("exists:", d.get("title"), "| by", d.get("author_name"))
        return
    if len(sys.argv) < 3:
        print(__doc__)
        return
    pkey, ytid = sys.argv[1], sys.argv[2]
    channel = sys.argv[3] if len(sys.argv) > 3 else ""
    assert ID_RE.match(ytid), "bad ID format (11 chars)"
    d = oembed(ytid)  # raises if video missing/private
    print("verified exists:", d.get("title"), "| by", d.get("author_name"))
    if not channel:
        channel = d.get("author_name", "")
    with app.get_con() as con:
        row = con.execute("SELECT id FROM videos WHERE problem_key=? AND verified=0 LIMIT 1", (pkey,)).fetchone()
        if not row:
            print("no DEMO slot left for", pkey)
            return
        con.execute("UPDATE videos SET youtube_id=?, channel=?, verified=1, verified_date=? WHERE id=?",
                    (ytid, channel, date.today().isoformat(), row[0]))
    print(f"saved: {pkey} -> {ytid} ({channel})")


if __name__ == "__main__":
    main()
