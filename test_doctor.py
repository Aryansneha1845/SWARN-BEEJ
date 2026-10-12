"""Fasal Doctor tests (no net, no API key). Run: python test_doctor.py"""
import asyncio
import io
import os
from PIL import Image
import app
from fastapi import UploadFile

os.environ["VISION_PROVIDER"] = "none"
fails = []


def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + f" | {name} {extra}")
    if not cond:
        fails.append(name)


def img_bytes(w=400, h=400, color=(90, 140, 70)):
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, "JPEG")
    return b.getvalue()


# 1. seed counts
with app.get_con() as con:
    check("crops=5", con.execute("SELECT COUNT(*) FROM crops").fetchone()[0] == 5)
    check("problems=15", con.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 15)
    check("treatments=15", con.execute("SELECT COUNT(*) FROM treatments").fetchone()[0] == 15)
    check("videos=30 DEMO", con.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 30
          and con.execute("SELECT COUNT(*) FROM videos WHERE verified=1").fetchone()[0] == 0)
    check("zones>=4", con.execute("SELECT COUNT(*) FROM zones").fetchone()[0] >= 4)

# 2. photo quality
check("tiny->retake", app.photo_quality(Image.new("RGB", (100, 100), (200, 30, 30)))[0] == "retake")
check("normal->ok", app.photo_quality(Image.new("RGB", (500, 500), (90, 140, 70)))[0] == "ok")

# 3. manual path
m = app.diagnose_manual(app.ManualIn(crop="paddy", problem="p-blb"))
check("manual ok", m["ok"] and m["needs_expert"] and m["demo"]
      and m["problems"][0]["treatment"] and "disclaimer_hi" in m)
m2 = app.diagnose_manual(app.ManualIn(crop="paddy", problem="nope"))
check("manual bad -> ok False", m2["ok"] is False)

# 4. diagnose with provider none -> manual fallback (async endpoint, call directly)
raw = img_bytes()
up = UploadFile(filename="leaf.jpg", file=io.BytesIO(raw))
r = asyncio.run(app.diagnose(image=up))
check("diagnose fallback needs_manual", r["ok"] and r.get("needs_manual") and "crops" in r)

# 5. diagnose with mocked vision
app.vision_diagnose = lambda img, lang="hi": {"crop_key": "paddy",
                                              "problems": [{"name": "Bacterial leaf blight", "confidence": 0.72}]}
up2 = UploadFile(filename="leaf.jpg", file=io.BytesIO(img_bytes()))
r2 = asyncio.run(app.diagnose(image=up2))
check("diagnose mock maps p-blb", r2["ok"] and not r2.get("needs_manual")
      and r2["problems"][0]["key"] == "p-blb" and r2["top_confidence"] == 0.72
      and r2["demo"] and "log_id" in r2, str(r2.get("problems", [{}])[0].get("key")))
lid = r2["log_id"]

# 6. bad file
up3 = UploadFile(filename="x.txt", file=io.BytesIO(b"not an image at all............"))
r3 = asyncio.run(app.diagnose(image=up3))
check("diagnose bad file -> ok False", r3["ok"] is False)

# 7. feedback
f = app.diagnose_feedback(app.DiagFbIn(log_id=lid, correct=True))
with app.get_con() as con:
    fb = con.execute("SELECT feedback FROM diagnosis_log WHERE id=?", (lid,)).fetchone()[0]
check("feedback saved", f["ok"] and fb == 1)

# 8. match helper
check("match 'blast' -> p-blast", app.match_problem_key("Blast") == "p-blast")
check("match '' -> None", app.match_problem_key("") is None)

# 9. context offline fallback (bad coords + unknown district, empty cache key unlikely hit)
c = app.context(lat="abc", lon="xyz", district="NowhereXYZ")
check("context fallback JSON", c["ok"] is False and "error" in c and c["cached"] is False)

print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}")
raise SystemExit(1 if fails else 0)
