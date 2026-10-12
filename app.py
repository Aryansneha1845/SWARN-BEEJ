"""SWARN-BEEJ v3 : Scan & Sach + Bill Suraksha + Shikayat Draft
SEVA FIRST RYIC 2026 (Local REG-001). Minimal backend.
Run: pip install -r requirements.txt ; python app.py  -> http://127.0.0.1:8000
"""
import os
import re
import secrets
import shutil
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, Header, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

BASE = Path(__file__).parent

# ---------- .env (API keys live here, never in code) ----------
def load_dotenv():
    p = BASE / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))

load_dotenv()

def vision_status():
    provider = os.environ.get("VISION_PROVIDER", "none").lower()
    key = bool(os.environ.get("GEMINI_API_KEY", ""))
    return {"provider": provider, "key_present": key,
            "ready": provider not in ("none", "") and (provider == "mock" or key)}


# ---------- Admin token (free auth): token lives ONLY in env/.env, never code ----------
def ensure_admin_token():
    tok = os.environ.get("ADMIN_TOKEN", "")
    if tok:
        return tok
    tok = secrets.token_urlsafe(32)
    try:
        with open(BASE / ".env", "a", encoding="utf-8") as f:
            f.write(f"\nADMIN_TOKEN={tok}\n")
    except Exception:
        pass
    os.environ["ADMIN_TOKEN"] = tok
    return tok


ADMIN_TOKEN = ensure_admin_token()


async def require_admin(request: Request):
    tok = request.headers.get("x-admin-token", "")
    if not tok or not secrets.compare_digest(tok, ADMIN_TOKEN):
        return JSONResponse(status_code=401, content={"ok": False, "error": "Admin token chahiye (X-Admin-Token)."})
    return None

# ---------- DB location: %LOCALAPPDATA% (OneDrive locks the project-folder DB) ----------
def _db_path() -> Path:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    d = Path(local) / "SWARN-BEEJ"
    d.mkdir(parents=True, exist_ok=True)
    new_db = d / "swarnbeej.db"
    old_db = BASE / "swarnbeej.db"
    if not new_db.exists() and old_db.exists():
        try:
            shutil.copy2(old_db, new_db)  # one-time migrate (keeps complaints)
        except Exception:
            pass
    return new_db

DB = _db_path()

@contextmanager
def get_con():
    con = sqlite3.connect(str(DB), timeout=10)
    try:
        con.execute("PRAGMA journal_mode=WAL;")
        yield con
        con.commit()
    finally:
        con.close()

# ---------- JSON errors (never HTML) ----------
app = FastAPI(title="SWARN-BEEJ")

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return HTMLResponse(status_code=404, content=(
            "<!DOCTYPE html><html lang='hi'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>404 - SWARN-BEEJ</title>"
            "<style>body{font-family:system-ui,sans-serif;background:#fffaf0;color:#1d1c16;"
            "display:flex;align-items:center;justify-content:center;min-height:90vh;margin:0}"
            ".c{text-align:center;padding:24px}.b{display:inline-block;margin-top:16px;padding:14px 28px;"
            "background:#0f3d24;color:#fff;border-radius:14px;text-decoration:none;font-weight:bold}</style></head>"
            "<body><div class='c'><div style='font-size:64px'>🌾</div>"
            "<h1>404 — Ye panna nahi mila</h1>"
            "<p>गलत पता? Home wapas jao.</p>"
            "<a class='b' href='/'>🏠 Home jao</a></div></body></html>"))
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"ok": False, "error": "Invalid input", "detail": str(exc)[:300]})

@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": "Server error"})

app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

# ---------- CORS: same-origin only (no cross-site API access) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
    max_age=600,
)

# ---------- Rate limit (in-memory, per IP) + security headers ----------
RATE = {}
RATE_LIMIT_API = (120, 60)   # 120 req / 60s per IP on /api/*
RATE_LIMIT_HEAVY = (20, 60)  # 20 req / 60s for diagnose/verify


def _hit(key: str, limit: int, window: int) -> bool:
    now = time.time()
    arr = [t for t in RATE.get(key, []) if now - t < window]
    arr.append(now)
    RATE[key] = arr
    if len(RATE) > 5000:
        RATE.clear()
    return len(arr) > limit


@app.middleware("http")
async def sec_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = (request.client.host if request.client else "?")
        heavy = request.url.path.startswith(("/api/diagnose", "/api/verify"))
        lim, win = RATE_LIMIT_HEAVY if heavy else RATE_LIMIT_API
        key = ip + ("#h" if heavy else "#a")
        if _hit(key, lim, win):
            return JSONResponse(status_code=429, content={"ok": False, "error": "Bahut requests — 1 min ruko (rate limit)."})
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=(self)"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://api.open-meteo.com https://www.youtube.com; "
        "frame-src https://www.youtube-nocookie.com; "
        "worker-src 'self' blob:; object-src 'none'; base-uri 'self'")
    return resp

# ---------- Seed ----------
SEED_PRODUCTS = [
    ("IFFCO", "Wheat HD-2967", "HD2967", "2027-12-31", 1),
    ("IFFCO", "Guar HG-563", "HG563", "2027-10-31", 1),
    ("KRIBHCO", "Paddy Pusa-44", "PUSA44", "2027-03-31", 1),
    ("National Seeds", "Mustard RH-30", "RH30", "2027-11-30", 1),
    ("Bayer", "Cotton Surpass", "BCSUP", "2027-09-30", 1),
    ("UPL", "Pesticide Saaf", "SAAF75", "2027-12-31", 1),
    ("Syngenta", "Maize NK-30", "NK30", "2027-01-31", 1),
    ("FAKE-NoLicence", "Sasta Beej Gold", "FAKE", "2025-01-01", 0),
    ("TestCo", "Old Stock Demo", "OLD99", "2023-01-01", 1),
]

def init_db():
    with get_con() as con:
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS products
            (id INTEGER PRIMARY KEY, brand TEXT, product TEXT, batch_prefix TEXT, expiry TEXT, licensed INTEGER)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bills
            (id INTEGER PRIMARY KEY, shop TEXT, bill_date TEXT, batch_text TEXT, created TEXT)""")
        for col in ["ALTER TABLE bills ADD COLUMN lat TEXT DEFAULT ''", "ALTER TABLE bills ADD COLUMN lon TEXT DEFAULT ''",
                    "ALTER TABLE bills ADD COLUMN ts TEXT DEFAULT ''", "ALTER TABLE bills ADD COLUMN photo_note TEXT DEFAULT ''"]:
            try:
                cur.execute(col)
            except Exception:
                pass
        cur.execute("""CREATE TABLE IF NOT EXISTS complaints
            (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, shop TEXT, district TEXT, detail TEXT, created TEXT,
             lat TEXT DEFAULT '', lon TEXT DEFAULT '', ts TEXT DEFAULT '', photo_note TEXT DEFAULT '')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS qr_scans
            (qr TEXT PRIMARY KEY, brand TEXT, batch TEXT, cnt INTEGER, first_seen TEXT, last_seen TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS feedback
            (id INTEGER PRIMARY KEY, signal TEXT, brand TEXT, batch TEXT, qr_text TEXT, correct INTEGER, note TEXT, created TEXT)""")
        if cur.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            cur.executemany("INSERT INTO products(brand,product,batch_prefix,expiry,licensed) VALUES(?,?,?,?,?)", SEED_PRODUCTS)
        else:
            have = {r[0] for r in cur.execute("SELECT batch_prefix FROM products").fetchall()}
            for p in SEED_PRODUCTS:
                if p[2] not in have:
                    cur.execute("INSERT INTO products(brand,product,batch_prefix,expiry,licensed) VALUES(?,?,?,?,?)", p)

init_db()

# ================= Fasal Doctor =================
import hashlib
import io
import json as _json
import urllib.request
import urllib.parse
from PIL import Image, ImageStat

UPLOADS = DB.parent / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

DOCTOR_CROPS = [
    ("wheat", "गेहूं", "Wheat", "Rabi"),
    ("paddy", "धान", "Paddy", "Kharif"),
    ("cotton", "कपास", "Cotton", "Kharif"),
    ("mustard", "सरसों", "Mustard", "Rabi"),
    ("maize", "मक्का", "Maize", "Kharif"),
]
# (key, crop_key, name_hi, name_en, symptoms_hi)
DOCTOR_PROBLEMS = [
    ("w-rust-y", "wheat", "पीला रतुआ", "Yellow rust", "पत्तियों पर पीली धारियाँ, पत्ती सूखना"),
    ("w-rust-b", "wheat", "भूरा रतुआ", "Brown rust", "पत्तियों पर भूरे फफोले, दाना हल्का"),
    ("w-aphid", "wheat", "माहू (एफिड)", "Aphid", "बालियों पर हरे-काले कीट, चिपचिपा रस"),
    ("p-blb", "paddy", "जीवाणु पत्ती झुलसा", "Bacterial leaf blight", "पत्ती किनारों से पीलापन-सफेदी, सूखना"),
    ("p-blast", "paddy", "झोंका (ब्लास्ट)", "Blast", "पत्ती पर आँख जैसी धब्बे, गर्दन टूटना"),
    ("p-stem", "paddy", "तना छेदक", "Stem borer", "बीच की गोभ सूखना (डेड हार्ट), सफेद बाली"),
    ("c-white", "cotton", "सफेद मक्खी", "Whitefly", "पत्ती नीचे सफेद मक्खी, पत्ती पीली-मुड़ना"),
    ("c-pink", "cotton", "गुलाबी सुंडी", "Pink bollworm", "टिंडे में छेद, फूल झड़ना"),
    ("c-curl", "cotton", "पत्ती मरोड़ विषाणु", "Leaf curl virus", "पत्तियाँ मुड़ना, नसें मोटी, बौनापन"),
    ("m-wrust", "mustard", "सफेद रतुआ", "White rust", "पत्ती नीचे सफेद फफोले, फूल विकृत"),
    ("m-aphid", "mustard", "चेपा (माहू)", "Mustard aphid", "फूल-फलियों पर हरे कीट, दाना हल्का"),
    ("m-alt", "mustard", "अल्टरनेरिया झुलसा", "Alternaria blight", "पत्ती-फली पर गोल भूरे धब्बे"),
    ("z-faw", "maize", "फॉल आर्मीवर्म", "Fall armyworm", "गोभ में छेद, हरी विष्ठा, पत्ती कुतरी"),
    ("z-tlb", "maize", "टर्सिकम पत्ती झुलसा", "Turcicum leaf blight", "पत्ती पर लंबी नाव जैसे भूरे धब्बे"),
    ("z-zinc", "maize", "जस्ता कमी", "Zinc deficiency", "नई पत्ती सफेद धारीदार, बढ़वार रुकना"),
]
# problem_key -> (steps_hi, source). No dose numbers (safety).
DOCTOR_TREATMENTS = {
    "w-rust-y": ("रोगग्रस्त पत्तियाँ हटाकर नष्ट करें।\nखेत में पानी न ठहरने दें।\nअनुशंसित फफूँदनाशी ही लेबल पढ़कर प्रयोग करें।\nKVK/कृषि अधिकारी से पुष्टि कराएँ।", "ICAR-सामान्य सलाह"),
    "w-rust-b": ("प्रतिरोधी किस्म अगली बार चुनें।\nरोग दिखते ही KVK से सलाह लें।\nलेबल पढ़कर ही दवा छिड़कें, अवधि का पालन करें।", "ICAR-सामान्य सलाह"),
    "w-aphid": ("शुरुआत में नीम-आधारित छिड़काव।\nअधिक प्रकोप पर अनुशंसित कीटनाशी लेबल अनुसार।\nफूल अवस्था में सुबह/शाम छिड़कें।", "KVK-सामान्य सलाह"),
    "p-blb": ("बीज उपचार अगली फसल में।\nखेत का पानी निकालकर सुखाएँ।\nरोगग्रस्त पौधे उखाड़कर दबाएँ।", "ICAR-सामान्य सलाह"),
    "p-blast": ("नाइट्रोजन अधिक न डालें।\nरोग दिखते ही कृषि अधिकारी से दवा पूछें।\nप्रतिरोधी किस्म अपनाएँ।", "ICAR-सामान्य सलाह"),
    "p-stem": ("फेरोमोन ट्रैप लगाएँ।\nअंडे वाले पत्ते नष्ट करें।\nआर्थिक सीमा पर ही दवा, सलाह लेकर।", "KVK-सामान्य सलाह"),
    "c-white": ("पीले चिपचिपे ट्रैप।\nनीम तेल शुरुआती अवस्था में।\nसफेद मक्खी अधिक हो तो KVK सलाह से दवा।", "KVK-सामान्य सलाह"),
    "c-pink": ("टिंडे तोड़कर नष्ट करें।\nफेरोमोन ट्रैप से निगरानी।\nबीटी कपास + शरणार्थी पंक्ति नियम मानें।", "ICAR-सामान्य सलाह"),
    "c-curl": ("रोगी पौधे उखाड़ें।\nसफेद मक्खी नियंत्रण ज़रूरी।\nस्वस्थ बीज व समय पर बुआई।", "KVK-सामान्य सलाह"),
    "m-wrust": ("रोगी पत्ते हटाएँ।\nसरसों-गेहूं फसल चक्र अपनाएँ।\nदवा KVK सलाह से ही।", "ICAR-सामान्य सलाह"),
    "m-aphid": ("फूल आने पर निगरानी बढ़ाएँ।\nलेडीबर्ड जैसे मित्र कीट बचाएँ।\nअधिक प्रकोप पर सलाह लेकर छिड़काव।", "KVK-सामान्य सलाह"),
    "m-alt": ("बीज उपचार करें।\nफसल अवशेष न जलाएँ, दबाएँ।\nदवा लेबल अनुसार।", "ICAR-सामान्य सलाह"),
    "z-faw": ("गोभ में रेत-नीम मिश्रण पारंपरिक उपाय।\nफेरोमोन ट्रैप।\nशुरुआती हमले पर ही नियंत्रण संभव — देर न करें।", "KVK-सामान्य सलाह"),
    "z-tlb": ("रोगरोधी किस्म चुनें।\nसंतुलित खाद दें।\nदवा KVK सलाह से।", "ICAR-सामान्य सलाह"),
    "z-zinc": ("मिट्टी जाँच कराएँ (Soil Health Card)।\nजस्ता उर्वरक सलाह अनुसार दें।\nगोबर की खाद मिलाएँ।", "Soil Health Card सलाह"),
}
DOCTOR_ZONES = [
    # Punjab — PAU 6 agro-climatic zones (Zone1 sub-mountain, 3 central plain, 4 western plain, 5 western)
    ("Bathinda", "पश्चिमी क्षेत्र (PAU Zone-5)", "रेतीली-मरुस्थलीय (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Ludhiana", "मध्य मैदानी क्षेत्र (PAU Zone-3)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Amritsar", "मध्य मैदानी क्षेत्र (PAU Zone-3)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Jalandhar", "मध्य मैदानी क्षेत्र (PAU Zone-3)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Patiala", "मध्य मैदानी क्षेत्र (PAU Zone-3)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Mansa", "पश्चिमी क्षेत्र (PAU Zone-5)", "रेतीली-मरुस्थलीय (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Ferozepur", "पश्चिमी मैदानी क्षेत्र (PAU Zone-4, कपास-सरसों)", "जलोढ़-रेतीली (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Moga", "पश्चिमी मैदानी क्षेत्र (PAU Zone-4, कपास-सरसों)", "जलोढ़-रेतीली (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Gurdaspur", "उप-पर्वतीय क्षेत्र (PAU Zone-1)", "पहाड़ी-जलोढ़ (ब्लॉक अनुसार — Soil Health Card देखें)", "तुलनात्मक रूप से बेहतर — ब्लॉक रिपोर्ट देखें"),
    # Haryana — Haryana Kisan Ayog 3 zones (I: 8 eastern dists, II: 7 central, III: 7 arid)
    ("Sirsa", "Zone-II (Haryana Kisan Ayog)", "रेतीली दोमट, दक्षिण-पश्चिम में मरुस्थलीय (HSAC)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Hisar", "Zone-II (Haryana Kisan Ayog)", "सिरोज़म/रेतीली दोमट, कुछ मरुस्थलीय (HSAC)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Karnal", "Zone-I (Haryana Kisan Ayog; धान-गेहूं)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Kurukshetra", "Zone-I (Haryana Kisan Ayog; धान-गेहूं)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Jind", "Zone-II (Haryana Kisan Ayog)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Fatehabad", "Zone-II (Haryana Kisan Ayog)", "रेतीली दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
    ("Bhiwani", "Zone-III शुष्क (Haryana Kisan Ayog; बाजरा-सरसों)", "रेतीली (ब्लॉक अनुसार — Soil Health Card देखें)", "वर्षा कम — सूक्ष्म सिंचाई अपनाएँ"),
    ("Rohtak", "Zone-II (Haryana Kisan Ayog)", "जलोढ़ दोमट (ब्लॉक अनुसार — Soil Health Card देखें)", "कई ब्लॉकों में अत्यधिक दोहन — CGWB रिपोर्ट देखें"),
]

def init_doctor():
    with get_con() as con:
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS crops(key TEXT PRIMARY KEY, name_hi TEXT, name_en TEXT, season TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS problems(key TEXT PRIMARY KEY, crop TEXT, name_hi TEXT, name_en TEXT, symptoms_hi TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS treatments(problem_key TEXT PRIMARY KEY, steps_hi TEXT, source TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY, problem_key TEXT, youtube_id TEXT, lang TEXT, channel TEXT, verified INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS zones(district TEXT PRIMARY KEY, agro_zone TEXT, soil_note TEXT, groundwater_note TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS diagnosis_log(id INTEGER PRIMARY KEY, photo_hash TEXT, result_json TEXT, confidence REAL, feedback INTEGER DEFAULT -1, created TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS weather_cache(key TEXT PRIMARY KEY, payload TEXT, created TEXT)")
        try:
            cur.execute("ALTER TABLE videos ADD COLUMN verified_date TEXT DEFAULT ''")
        except Exception:
            pass
        if cur.execute("SELECT COUNT(*) FROM crops").fetchone()[0] == 0:
            cur.executemany("INSERT INTO crops VALUES(?,?,?,?)", DOCTOR_CROPS)
            cur.executemany("INSERT INTO problems VALUES(?,?,?,?,?)", DOCTOR_PROBLEMS)
            cur.executemany("INSERT INTO treatments VALUES(?,?,?)",
                            [(k, v[0], v[1]) for k, v in DOCTOR_TREATMENTS.items()])
            vids = []
            for (k, _c, _h, _e, _s) in DOCTOR_PROBLEMS:
                vids.append((k, "", "hi", "", 0, ""))
                vids.append((k, "", "hi", "", 0, ""))
            cur.executemany("INSERT INTO videos(problem_key,youtube_id,lang,channel,verified,verified_date) VALUES(?,?,?,?,?,?)", vids)
        # upsert zones (new districts reach existing DBs; corrected zone names overwrite)
        for z in DOCTOR_ZONES:
            cur.execute("INSERT INTO zones VALUES(?,?,?,?) ON CONFLICT(district) DO UPDATE SET agro_zone=excluded.agro_zone, soil_note=excluded.soil_note, groundwater_note=excluded.groundwater_note", z)

init_doctor()

def photo_quality(img: Image.Image):
    w, h = img.size
    if w < 224 or h < 224:
        return "retake", "फोटो बहुत छोटी है — पत्ता close-up में दोबारा लें।"
    try:
        mean = ImageStat.Stat(img.convert("L")).mean[0]
        if mean < 28:
            return "retake", "फोटो बहुत अंधेरी है — रोशनी में दोबारा लें।"
    except Exception:
        pass
    return "ok", ""

def vision_diagnose(img: Image.Image, lang: str = "hi"):
    """Provider interface. Returns dict {crop_key, problems:[{name,confidence}]} or None.
    VISION_PROVIDER=none (default) -> None (manual fallback). Keys via env only, never hardcoded."""
    provider = os.environ.get("VISION_PROVIDER", "none").lower()
    if provider == "mock":
        return {"crop_key": "paddy", "problems": [{"name": "Bacterial leaf blight", "confidence": 0.72}]}
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return None
        try:
            import base64
            buf = io.BytesIO()
            img.copy().resize((512, 512)).convert("RGB").save(buf, "JPEG", quality=70)
            payload = _json.dumps({"contents": [{"parts": [
                {"text": "Identify crop + top-3 disease/pest with confidence 0-1. Reply ONLY JSON: {\"crop_key\": \"wheat|paddy|cotton|mustard|maize\", \"problems\": [{\"name\": \"...\", \"confidence\": 0.0}]}"},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}]}]}).encode()
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + key,
                data=payload, headers={"Content-Type": "application/json"})
            out = _json.load(urllib.request.urlopen(req, timeout=25))
            txt = out["candidates"][0]["content"]["parts"][0]["text"]
            txt = txt[txt.find("{"):txt.rfind("}") + 1]
            d = _json.loads(txt)
            assert d.get("crop_key") and isinstance(d.get("problems"), list)
            return d
        except Exception:
            return None
    return None

def problem_envelope(pkey: str):
    with get_con() as con:
        pr = con.execute("SELECT key,crop,name_hi,name_en,symptoms_hi FROM problems WHERE key=?", (pkey,)).fetchone()
        if not pr:
            return None
        tr = con.execute("SELECT steps_hi,source FROM treatments WHERE problem_key=?", (pkey,)).fetchone()
        vrows = con.execute("SELECT youtube_id,lang,channel,verified FROM videos WHERE problem_key=? ORDER BY verified DESC", (pkey,)).fetchall()
    v = vrows[0] if vrows else ("", "hi", "", 0)
    return {"key": pr[0], "crop": pr[1], "name_hi": pr[2], "name_en": pr[3], "symptoms_hi": pr[4],
            "treatment": tr[0] if tr else "", "source": tr[1] if tr else "",
            "video": {"youtube_id": v[0], "lang": v[1], "channel": v[2], "verified": bool(v[3])}}

def match_problem_key(name: str):
    n = norm(name)
    if not n:
        return None
    with get_con() as con:
        rows = con.execute("SELECT key,name_hi,name_en FROM problems").fetchall()
    for k, hi, en in rows:
        if norm(en) in n or n in norm(en) or norm(hi).replace(" ", "") in n.replace(" ", ""):
            return k
    return None

# ---------- Normalize ----------
def norm(s: str) -> str:
    """strip + UPPERCASE + remove spaces/hyphens. '' stays ''."""
    return re.sub(r"[\s\-]+", "", (s or "").strip().upper())

def track_qr(qr: str, brand: str, batch: str):
    """(reused, count). Reused = same QR seen before with DIFFERENT brand/batch."""
    if not qr:
        return False, 0
    now = datetime.now().isoformat(timespec="seconds")
    with get_con() as con:
        cur = con.cursor()
        row = cur.execute("SELECT brand, batch, cnt FROM qr_scans WHERE qr=?", (qr,)).fetchone()
        if row is None:
            cur.execute("INSERT INTO qr_scans(qr,brand,batch,cnt,first_seen,last_seen) VALUES(?,?,?,?,?,?)",
                        (qr, brand, batch, 1, now, now))
            return False, 1
        reused = (row[0] != brand) or (row[1] != batch)
        cur.execute("UPDATE qr_scans SET cnt=cnt+1, last_seen=? WHERE qr=?", (now, qr))
        return reused, row[2] + 1

def days_to_expiry(expiry: str):
    try:
        return (datetime.strptime(expiry, "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return None

# ---------- Models (length-capped: abuse/DoS protection) ----------
class VerifyIn(BaseModel):
    brand: str = Field(default="", max_length=120)
    batch: str = Field(default="", max_length=120)
    qr_text: str = Field(default="", max_length=500)

class BillIn(BaseModel):
    shop: str = Field(default="", max_length=120)
    bill_date: str = Field(default="", max_length=20)
    batch_text: str = Field(default="", max_length=120)
    lat: str = Field(default="", max_length=30)
    lon: str = Field(default="", max_length=30)
    ts: str = Field(default="", max_length=40)
    photo_note: str = Field(default="", max_length=120)

class ComplaintIn(BaseModel):
    name: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=20)
    shop: str = Field(default="", max_length=120)
    district: str = Field(default="", max_length=120)
    detail: str = Field(default="", max_length=1000)
    lat: str = Field(default="", max_length=30)
    lon: str = Field(default="", max_length=30)
    ts: str = Field(default="", max_length=40)
    photo_note: str = Field(default="", max_length=120)
    consent: bool = False

class FeedbackIn(BaseModel):
    signal: str = Field(default="", max_length=20)
    brand: str = Field(default="", max_length=120)
    batch: str = Field(default="", max_length=120)
    qr_text: str = Field(default="", max_length=500)
    correct: bool = True
    note: str = Field(default="", max_length=500)

class AddProductIn(BaseModel):
    brand: str = Field(default="", max_length=120)
    product: str = Field(default="", max_length=120)
    batch_prefix: str = Field(default="", max_length=60)
    expiry: str = Field(default="", max_length=20)
    licensed: int = 1

# ---------- Pages ----------
@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE / "templates" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    st = vision_status()
    return {"ok": True, "app": "SWARN-BEEJ", "db": str(DB),
            "vision": st["provider"], "vision_ready": st["ready"]}

@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import FileResponse
    return FileResponse(str(BASE / "static" / "favicon.svg"))

# ---------- Legal pages (DPDP Act 2023 aligned; solo-project scale) ----------
GRIEVANCE = "Aryan Singh — beastaryan249@gmail.com"

LEGAL_PAGES = {
    "privacy": ("Privacy Policy / गोपनीयता नीति", """
<p><b>Data stays on your machine.</b> SWARN-BEEJ runs on your own computer/phone-server.
Nothing is sold, no ads, no analytics, no tracking cookies.</p>
<h3>What we collect (only what is needed)</h3>
<ul><li><b>Scan:</b> brand/batch/QR text is checked, never linked to you. Only an anonymous
QR-reuse counter (qr + brand + batch) is stored to catch copied QR codes.</li>
<li><b>Bill:</b> shop/date/batch (+GPS only if you tap “GPS जोड़ें”). Bill <b>photos never leave your phone</b> (preview only).</li>
<li><b>Complaint:</b> name/phone/shop/district/detail + consent flag — only after you tick consent.</li>
<li><b>Feedback/Diagnosis:</b> Haan/Na + photo hash (no raw photos stored except local compressed copy for your own log).</li></ul>
<h3>Why (purpose)</h3><p>Fake-input detection, evidence for your own complaint, accuracy improvement. Nothing else.</p>
<h3>Your rights (DPDP Act 2023)</h3><p>Access, correction, deletion, grievance redressal — contact: GRIEV.</p>
<h3>Retention</h3><p>Until you delete the local database file (swarnbeej.db). No cloud backup by us.</p>
<h3>Children</h3><p>Use with a parent/teacher for users under 18.</p>"""),
    "terms": ("Terms of Use / उपयोग शर्तें", """
<p>SWARN-BEEJ is a <b>student prototype</b> (SEVA FIRST RYIC 2026), provided as-is, no warranty.</p>
<ul><li>Results are <b>guidance only, never “100% genuine”</b>. Final call: Agri officer/KVK.</li>
<li>Report pesticide/seed advice on labels; never exceed label doses.</li>
<li>Acceptable use: no abuse, no spam, no overloading the server (rate limits apply).</li>
<li>Your content stays yours. App code/content: © Aryan Singh, 2026, for the Challenge.</li>
<li>Disputes: contact GRIEV first; jurisdiction: India.</li></ul>"""),
    "cookies": ("Cookie Policy / कुकी नीति", """
<p><b>No cookies. No analytics. No tracking.</b> No consent banner is needed because nothing non-essential is stored.</p>
<ul><li><b>What IS stored on your device:</b> service-worker cache (offline pages), localStorage (cached product list, last result) — both essential, both deletable via browser “clear site data”.</li>
<li><b>Third parties:</b> CDN scripts (Tailwind, jsDelivr, Google Fonts), YouTube-nocookie iframe (loads only if a verified video exists — none now), Open-Meteo weather (server-side fetch, your IP goes to them when you load weather).</li></ul>"""),
    "refund": ("Refund Policy / रिफंड नीति", """
<p><b>No payments are collected</b> — the app is free. So there is nothing to refund.</p>
<p>Any issue: contact GRIEV and it will be fixed or your local data deleted on request.</p>"""),
}


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return legal_page("privacy")


@app.get("/terms", response_class=HTMLResponse)
def terms():
    return legal_page("terms")


@app.get("/cookies", response_class=HTMLResponse)
def cookies():
    return legal_page("cookies")


@app.get("/refund", response_class=HTMLResponse)
def refund():
    return legal_page("refund")


def legal_page(key: str):
    title, body = LEGAL_PAGES[key]
    body = body.replace("GRIEV", GRIEVANCE)
    return ("<!DOCTYPE html><html lang='hi'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{title} - SWARN-BEEJ</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;padding:20px;"
            "font-size:17px;line-height:1.6;background:#fffaf0;color:#1d1c16}h1{color:#0f3d24}a{color:#0f3d24}</style></head>"
            f"<body><p><a href='/'>← SWARN-BEEJ</a></p><h1>{title}</h1>{body}"
            "<hr><p><a href='/privacy'>Privacy</a> • <a href='/terms'>Terms</a> • "
            "<a href='/cookies'>Cookies</a> • <a href='/refund'>Refund</a></p></body></html>")

# ---------- Selftest ----------
@app.get("/api/selftest")
def selftest():
    checks = {}
    try:
        with get_con() as con:
            checks["db_wal"] = con.execute("PRAGMA journal_mode;").fetchone()[0]
            checks["products"] = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    cases = [
        ({"brand": "IFFCO", "batch": "HG563-221", "qr_text": "HG563XYZ"}, "GREEN"),
        ({"brand": "IFFCO", "batch": "HG563-221", "qr_text": ""}, "YELLOW"),
        ({"brand": "FAKE-NoLicence", "batch": "FAKE-1", "qr_text": "x"}, "RED"),
        ({"brand": "UnknownCo", "batch": "ZZZ-1", "qr_text": "z"}, "YELLOW"),
        ({"brand": "", "batch": "", "qr_text": ""}, "YELLOW"),
    ]
    results = []
    all_ok = True
    for inp, exp in cases:
        got = verify(VerifyIn(**inp))["signal"]
        passed = got == exp
        all_ok = all_ok and passed
        results.append({"in": inp, "exp": exp, "got": got, "pass": passed})
    checks["verify_cases"] = results
    checks["vision"] = vision_status()
    # doctor checks (offline-safe: seed counts + manual envelope + photo-quality)
    try:
        with get_con() as con:
            checks["doc_crops"] = con.execute("SELECT COUNT(*) FROM crops").fetchone()[0]
            checks["doc_problems"] = con.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            checks["doc_treatments"] = con.execute("SELECT COUNT(*) FROM treatments").fetchone()[0]
            checks["doc_zones"] = con.execute("SELECT COUNT(*) FROM zones").fetchone()[0]
        tiny = Image.new("RGB", (100, 100), (200, 30, 30))
        checks["doc_quality_retake"] = photo_quality(tiny)[0] == "retake"
        menv = problem_envelope("p-blb")
        checks["doc_manual"] = bool(menv and menv["treatment"] and menv["video"] is not None)
        checks["doctor"] = (checks["doc_crops"] == 5 and checks["doc_problems"] == 15
                            and checks["doc_treatments"] == 15 and checks["doc_zones"] >= 4
                            and checks["doc_quality_retake"] and checks["doc_manual"])
    except Exception as e:
        checks["doctor"] = False
        checks["doctor_error"] = str(e)[:200]
    return {"ok": all_ok and checks["products"] >= 9 and checks.get("doctor", False), "checks": checks}

# ---------- APIs ----------
@app.get("/api/products")
def products(q: str = ""):
    with get_con() as con:
        rows = con.execute(
            "SELECT brand, product, batch_prefix, expiry, licensed FROM products WHERE brand LIKE ? OR product LIKE ? LIMIT 50",
            (f"%{q}%", f"%{q}%")).fetchall()
    return [{"brand": r[0], "product": r[1], "batch_prefix": r[2], "expiry": r[3], "licensed": bool(r[4])} for r in rows]

@app.post("/api/verify")
def verify(v: VerifyIn):
    brand_raw = (v.brand or "").strip()
    brand = norm(v.brand)
    batch = norm(v.batch)
    qr = norm(v.qr_text)

    rows = []
    with get_con() as con:
        rows = con.execute("SELECT brand, product, batch_prefix, expiry, licensed FROM products").fetchall()

    # FIX: empty brand/batch NEVER match (old bug: '' in 'iffco' == True)
    match = None
    if brand and batch:
        for r in rows:
            bnorm = norm(r[0])
            pnorm = norm(r[2])
            if (bnorm and bnorm in brand) or (brand in bnorm):
                if batch.startswith(pnorm) or pnorm in batch:
                    match = r
                    break
        if not match:
            for r in rows:
                pnorm = norm(r[2])
                if pnorm and (batch.startswith(pnorm) or pnorm in batch):
                    match = r
                    break

    # SAFE-DEFAULT: unknown => YELLOW
    if match is None:
        reused, cnt = track_qr(qr, brand, batch) if qr else (False, 0)
        return {"signal": "YELLOW",
                "reason_hi": "ब्रांड/बैच लाइसेंस सूची में नहीं मिला। अधिकारी से जाँच कराएँ और बिल रखें।",
                "reason_en": "Not in licensed list. Get officer verification.",
                "matched": None, "confidence": 55, "reused": reused, "qr_count": cnt,
                "why_hi": ["लाइसेंस सूची में नाम नहीं", "अधिकारी से जाँच ज़रूरी"], "expiry_soon": False}

    _brand, prod, _prefix, expiry, licensed = match
    matched = {"brand": _brand, "product": prod, "expiry": expiry}
    pnorm = norm(_prefix)
    dte = days_to_expiry(expiry)
    expiry_soon = (dte is not None) and (0 <= dte <= 30)

    if not licensed:
        reused, cnt = track_qr(qr, brand, batch) if qr else (False, 0)
        return {"signal": "RED", "reason_hi": f"{_brand} {prod} बिना लाइसेंस वाली एंट्री है। न खरीदें।",
                "reason_en": "Unlicensed entry.", "matched": matched, "confidence": 88,
                "reused": reused, "qr_count": cnt, "why_hi": ["लाइसेंस नहीं"], "expiry_soon": expiry_soon}
    try:
        if expiry < date.today().isoformat():
            reused, cnt = track_qr(qr, brand, batch) if qr else (False, 0)
            return {"signal": "RED", "reason_hi": f"एक्सपायरी {expiry} निकल चुकी है। न लें।",
                    "reason_en": "Expired.", "matched": matched, "confidence": 90,
                    "reused": reused, "qr_count": cnt, "why_hi": ["एक्सपायरी निकली"], "expiry_soon": False}
    except Exception:
        pass
    if not qr:
        return {"signal": "YELLOW", "reason_hi": f"{_brand} {prod} लाइसेंस सूची में मिला, पर क्यूआर खाली है। बिल ज़रूर लें।",
                "reason_en": "Matched but QR empty - take bill.", "matched": matched, "confidence": 65,
                "reused": False, "qr_count": 0, "why_hi": ["क्यूआर खाली"], "expiry_soon": expiry_soon}
    if pnorm not in qr:
        reused, cnt = track_qr(qr, brand, batch)
        return {"signal": "YELLOW", "reason_hi": "क्यूआर में बैच कोड नहीं मिला — नकली या दोबारा इस्तेमाल क्यूआर हो सकता है। बिल और फोटो रखें।",
                "reason_en": "QR does not contain batch - possible reused QR.", "matched": matched, "confidence": 62,
                "reused": reused, "qr_count": cnt, "why_hi": ["क्यूआर-बैच मेल नहीं"], "expiry_soon": expiry_soon}
    reused, cnt = track_qr(qr, brand, batch)
    if reused:
        return {"signal": "YELLOW",
                "reason_hi": "यह क्यूआर पहले दूसरे पैकेट पर स्कैन हुआ था — दोबारा इस्तेमाल का शक। अधिकारी से जाँच कराएँ।",
                "reason_en": "Same QR seen on different packet before - possible reuse.", "matched": matched,
                "confidence": 60, "reused": True, "qr_count": cnt,
                "why_hi": ["क्यूआर दोबारा इस्तेमाल"], "expiry_soon": expiry_soon}
    why = ["लाइसेंस मेल", "बैच मेल", "क्यूआर मेल"]
    if expiry_soon:
        why.append(f"एक्सपायरी {dte} दिन में")
    return {"signal": "GREEN", "reason_hi": f"{_brand} {prod} लाइसेंस सूची में मिला + बैच + क्यूआर मेल। फिर भी बिल लें।",
            "reason_en": "Licensed + batch + QR match.", "matched": matched, "confidence": 92,
            "reused": False, "qr_count": cnt, "why_hi": why, "expiry_soon": expiry_soon,
            "brand_shown": brand_raw}

@app.post("/api/bill")
def save_bill(b: BillIn):
    with get_con() as con:
        cur = con.cursor()
        cur.execute("INSERT INTO bills(shop,bill_date,batch_text,created,lat,lon,ts,photo_note) VALUES(?,?,?,date('now'),?,?,?,?)",
                    (b.shop, b.bill_date, b.batch_text, b.lat or "", b.lon or "",
                     b.ts or datetime.now().isoformat(timespec="seconds"), b.photo_note or ""))
        bid = cur.lastrowid
    return {"ok": True, "bill_id": bid, "msg_hi": f"बिल #{bid} सहेज गया। शिकायत में काम आएगा।"}

@app.post("/api/complaint")
def make_complaint(c: ComplaintIn):
    if not c.consent:
        return JSONResponse(status_code=400, content={"ok": False, "error": "शिकायत हेतु सहमति (consent) ज़रूरी है।"})
    ts = c.ts or datetime.now().isoformat(timespec="seconds")
    with get_con() as con:
        cur = con.cursor()
        try:
            cur.execute("ALTER TABLE complaints ADD COLUMN consent INTEGER DEFAULT 0")
        except Exception:
            pass
        cur.execute("INSERT INTO complaints(name,phone,shop,district,detail,created,lat,lon,ts,photo_note,consent) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (c.name, c.phone, c.shop, c.district, c.detail, date.today().isoformat(),
                     c.lat or "", c.lon or "", ts, c.photo_note or "", 1))
        cid = cur.lastrowid
    draft_hi = (
        f"सेवा में, कृषि अधिकारी, जिला {c.district}\n"
        f"विषय: नकली/संदिग्ध बीज-कीटनाशक की शिकायत (SWARN-BEEJ #{cid})\n"
        f"मैं {c.name} ({c.phone}) निवेदन करता हूँ कि दुकान '{c.shop}' से लिया गया input संदिग्ध है।\n"
        f"विवरण: {c.detail}\nबिल फोटो व पैकेट फोटो संलग्न है। जाँच कर कार्रवाई करें।\n"
        f"दिनांक: {date.today().isoformat()}"
    )
    return {"ok": True, "id": cid, "draft_hi": draft_hi}

@app.post("/api/feedback")
def feedback(f: FeedbackIn):
    with get_con() as con:
        con.execute("INSERT INTO feedback(signal,brand,batch,qr_text,correct,note,created) VALUES(?,?,?,?,?,?,date('now'))",
                    (f.signal, f.brand, f.batch, f.qr_text, 1 if f.correct else 0, f.note or ""))
    return {"ok": True, "msg_hi": "धन्यवाद! राय सहेज गई।"}

def mask_shop(s: str):
    s = (s or "").strip()
    if len(s) <= 2:
        return "***"
    return s[:2] + "***"

@app.get("/api/complaints")
def complaints_list(limit: int = 50):
    with get_con() as con:
        rows = con.execute("SELECT id, shop, district, detail, created FROM complaints ORDER BY id DESC LIMIT ?",
                           (limit,)).fetchall()
    return [{"id": r[0], "shop_masked": mask_shop(r[1]), "district": r[2], "detail": r[3], "created": r[4]} for r in rows]

@app.get("/api/stats")
def stats():
    with get_con() as con:
        by_dist = con.execute("SELECT district, COUNT(*) FROM complaints GROUP BY district ORDER BY COUNT(*) DESC LIMIT 12").fetchall()
        shops = con.execute("SELECT shop, COUNT(*) FROM complaints GROUP BY shop ORDER BY COUNT(*) DESC LIMIT 12").fetchall()
        reused = con.execute("SELECT COUNT(*) FROM qr_scans WHERE cnt>=2").fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
        fb = con.execute("SELECT COUNT(*), COALESCE(SUM(correct),0) FROM feedback").fetchone()
    return {"by_district": [{"district": (d or "Unknown"), "count": c} for d, c in by_dist],
            "shops_masked": [{"shop": mask_shop(s), "count": c} for s, c in shops],
            "qr_reused_types": reused, "total_complaints": total,
            "feedback_total": fb[0] or 0, "feedback_correct": fb[1] or 0}

@app.post("/api/admin/add_product")
async def add_product(p: AddProductIn, request: Request):
    denied = await require_admin(request)
    if denied is not None:
        return denied
    if not norm(p.brand) or not norm(p.batch_prefix):
        return {"ok": False, "msg": "ब्रांड और बैच-उपसर्ग ज़रूरी"}
    with get_con() as con:
        con.execute("INSERT INTO products(brand,product,batch_prefix,expiry,licensed) VALUES(?,?,?,?,?)",
                    (p.brand.strip(), (p.product or p.brand).strip(), norm(p.batch_prefix),
                     p.expiry or "2027-12-31", p.licensed))
    return {"ok": True, "msg_hi": "उत्पाद लाइसेंस सूची में जुड़ गया।"}

# ================= Fasal Doctor endpoints =================
DISCLAIMER_HI = "यह सलाह है। अंतिम निर्णय कृषि अधिकारी/KVK का।"
DISCLAIMER_EN = "This is guidance only. Final call: Agri officer/KVK."

def log_diagnosis(photo_hash: str, result: dict, conf):
    with get_con() as con:
        cur = con.cursor()
        cur.execute("INSERT INTO diagnosis_log(photo_hash,result_json,confidence,created) VALUES(?,?,?,date('now'))",
                    (photo_hash, _json.dumps(result, ensure_ascii=False)[:4000],
                     float(conf) if conf is not None else None))
        return cur.lastrowid

def doctor_envelope(items: list, demo: bool, needs_expert: bool, photo_quality: str):
    """items: [{envelope..., confidence}] -> top-3 result envelope."""
    probs = []
    for it in items[:3]:
        env = it["env"]
        probs.append({
            "key": env["key"], "name_hi": env["name_hi"], "name_en": env["name_en"],
            "symptoms_hi": env["symptoms_hi"], "confidence": it.get("confidence"),
            "treatment": env["treatment"], "source": env["source"], "video": env["video"]})
    top_conf = probs[0]["confidence"] if probs else None
    if top_conf is not None and top_conf < 0.6:
        needs_expert = True
    vid_demo = demo or not (probs and probs[0]["video"]["verified"] and probs[0]["video"]["youtube_id"])
    return {"ok": True, "photo_quality": photo_quality, "problems": probs,
            "top_confidence": top_conf, "needs_expert": needs_expert, "demo": vid_demo,
            "disclaimer_hi": DISCLAIMER_HI, "disclaimer_en": DISCLAIMER_EN}

@app.get("/api/problems")
def doctor_problems(crop: str = ""):
    with get_con() as con:
        crops = [{"key": r[0], "name_hi": r[1], "name_en": r[2], "season": r[3]}
                 for r in con.execute("SELECT key,name_hi,name_en,season FROM crops").fetchall()]
        if crop:
            probs = [{"key": r[0], "name_hi": r[1], "name_en": r[2], "symptoms_hi": r[3]}
                     for r in con.execute("SELECT key,name_hi,name_en,symptoms_hi FROM problems WHERE crop=?", (crop,)).fetchall()]
        else:
            probs = [{"key": r[0], "crop": r[1], "name_hi": r[2], "name_en": r[3]}
                     for r in con.execute("SELECT key,crop,name_hi,name_en FROM problems").fetchall()]
    return {"crops": crops, "problems": probs}

@app.post("/api/diagnose")
async def diagnose(image: UploadFile = File(...), lat: str = Form(""), lon: str = Form(""),
                   lang: str = Form("hi"), district: str = Form("")):
    raw = await image.read()
    if len(raw) > 8 * 1024 * 1024:
        return {"ok": False, "error": "फोटो 8MB से बड़ी है। छोटी फोटो लें।"}
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return {"ok": False, "error": "फोटो खुल नहीं रही। दूसरी फोटो लें।"}
    q, qmsg = photo_quality(img)
    if q == "retake":
        return {"ok": True, "photo_quality": "retake", "quality_msg": qmsg, "needs_manual": True,
                "disclaimer_hi": DISCLAIMER_HI, "disclaimer_en": DISCLAIMER_EN}
    phash = hashlib.sha256(raw).hexdigest()[:16]
    small = img.copy()
    small.thumbnail((1024, 1024))
    small.save(UPLOADS / f"{phash}.jpg", "JPEG", quality=70)
    vis = vision_diagnose(img, lang)
    if not vis:
        with get_con() as con:
            crops = [{"key": r[0], "name_hi": r[1], "name_en": r[2]} for r in con.execute("SELECT key,name_hi,name_en FROM crops").fetchall()]
        lid = log_diagnosis(phash, {"mode": "manual-needed"}, None)
        return {"ok": True, "photo_quality": "ok", "needs_manual": True, "crops": crops, "log_id": lid,
                "msg_hi": "AI उपलब्ध नहीं — फसल चुनकर समस्या देखें।",
                "disclaimer_hi": DISCLAIMER_HI, "disclaimer_en": DISCLAIMER_EN}
    items = []
    for p in (vis.get("problems") or [])[:3]:
        key = match_problem_key(p.get("name", ""))
        if not key:
            continue
        env = problem_envelope(key)
        if env:
            try:
                cf = float(p.get("confidence", 0))
            except Exception:
                cf = 0.0
            items.append({"env": env, "confidence": round(max(0.0, min(1.0, cf)), 2)})
    if not items:
        lid = log_diagnosis(phash, {"mode": "nomatch", "raw": str(vis)[:500]}, None)
        return {"ok": True, "photo_quality": "ok", "needs_manual": True, "log_id": lid,
                "msg_hi": "समस्या DB से मेल नहीं खाई — सूची से चुनें या अधिकारी से पूछें।",
                "disclaimer_hi": DISCLAIMER_HI, "disclaimer_en": DISCLAIMER_EN}
    env = doctor_envelope(items, demo=False, needs_expert=False, photo_quality="ok")
    env["crop_key"] = vis.get("crop_key", "")
    env["log_id"] = log_diagnosis(phash, env, env["top_confidence"])
    env["needs_manual"] = False
    return env

class ManualIn(BaseModel):
    crop: str = ""
    problem: str = ""

@app.post("/api/diagnose/manual")
def diagnose_manual(m: ManualIn):
    key = (m.problem or "").strip()
    with get_con() as con:
        ok = con.execute("SELECT COUNT(*) FROM problems WHERE key=? AND crop=?", (key, m.crop)).fetchone()[0]
    if not ok:
        return {"ok": False, "error": "सही फसल/समस्या चुनें।"}
    env = problem_envelope(key)
    out = doctor_envelope([{"env": env, "confidence": None}], demo=True, needs_expert=True, photo_quality="manual")
    out["crop_key"] = m.crop
    out["log_id"] = log_diagnosis("manual", out, None)
    out["needs_manual"] = False
    return out

class DiagFbIn(BaseModel):
    log_id: int = 0
    correct: bool = True

@app.post("/api/diagnose/feedback")
def diagnose_feedback(f: DiagFbIn):
    with get_con() as con:
        con.execute("UPDATE diagnosis_log SET feedback=? WHERE id=?", (1 if f.correct else 0, f.log_id))
    return {"ok": True, "msg_hi": "धन्यवाद! राय सहेज गई।"}

def fetch_weather(lat: float, lon: float):
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,precipitation&hourly=precipitation_probability"
           "&forecast_days=3&timezone=auto" % (lat, lon))
    with urllib.request.urlopen(url, timeout=10) as r:
        return _json.load(r)

@app.get("/api/context")
def context(lat: str = "", lon: str = "", district: str = ""):
    key = f"{(lat or '')[:6]},{(lon or '')[:6]},{norm(district)}"
    zone = None
    if district:
        dn = norm(district)
        with get_con() as con:
            rows = con.execute("SELECT district,agro_zone,soil_note,groundwater_note FROM zones").fetchall()
        for d, z, s, gw in rows:
            if norm(d) in dn or dn in norm(d):
                zone = {"district": d, "agro_zone": z, "soil_note": s, "groundwater_note": gw}
                break
    if not (lat and lon):
        # no GPS: zone only (weather needs location)
        if zone:
            return {"ok": True, "temp_c": None, "precip_now": None, "rain_prob_48h": None,
                    "spray_alert": False, "spray_hi": "", "zone": zone, "cached": False, "no_gps": True,
                    "disclaimer_hi": DISCLAIMER_HI}
        return {"ok": False, "zone": None, "cached": False,
                "error": "लोकेशन/ज़िला दें — मौसम के लिए GPS, ज़ोन के लिए ज़िला।"}
    try:
        la, lo = float(lat), float(lon)
        w = fetch_weather(la, lo)
        cur = (w.get("current") or {})
        probs = ((w.get("hourly") or {}).get("precipitation_probability") or [])[:48]
        pmax = max(probs) if probs else 0
        spray = pmax >= 50
        payload = {"ok": True, "temp_c": cur.get("temperature_2m"), "precip_now": cur.get("precipitation"),
                   "rain_prob_48h": pmax,
                   "spray_alert": spray,
                   "spray_hi": "48 घंटे में बारिश संभव — छिड़काव न करें।" if spray else "छिड़काव का मौसम ठीक है।",
                   "zone": zone, "cached": False,
                   "disclaimer_hi": DISCLAIMER_HI}
        with get_con() as con:
            con.execute("INSERT OR REPLACE INTO weather_cache(key,payload,created) VALUES(?,?,date('now'))",
                        (key, _json.dumps(payload, ensure_ascii=False)))
        return payload
    except Exception:
        with get_con() as con:
            row = con.execute("SELECT payload FROM weather_cache WHERE key=?", (key,)).fetchone()
        if row:
            d = _json.loads(row[0])
            d["cached"] = True
            d["zone"] = zone or d.get("zone")
            return d
        return {"ok": False, "zone": zone, "cached": False,
                "error": "मौसम नहीं मिला (नेट/लोकेशन)। ज़िला चुनकर ज़ोन देखें।"}

if __name__ == "__main__":
    import uvicorn
    # reload OFF in production (debug mode band). 0.0.0.0 = same-WiFi phone access.
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
