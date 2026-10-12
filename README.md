# SWARN-BEEJ 🌾 v3 — Nakli Beej Pehchano

SEVA FIRST RYIC 2026 • Local REG-001 • TRL 2→6 • FastAPI + SQLite, no build step.
DB lives at `%LOCALAPPDATA%\SWARN-BEEJ\swarnbeej.db` (WAL mode) — OneDrive won't lock it.

## Run
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:8000 (first load needs net for CDN; after that offline-ready).

## 3-step demo (judges, 60 sec)
1. **Scan:** Brand `IFFCO`, Batch `HG563-221`, QR `HG563XYZ` → **Jaanch karo** → green shield + 92% + Hindi voice. (i) sheet me YELLOW/RED demo buttons bhi hain.
2. **Bill:** Bill tab → dukaan + date + batch → Save.
3. **Shikayat:** form → Draft banao → Copy / WhatsApp.

Safe-default: unknown/empty brand-batch → YELLOW "officer se verify karao". Same QR dobara alag packet par → reused warning. App kabhi "100% asli" nahi bolta.

## Accuracy
```
python test_accuracy.py   # 19/19 synthetic (docs/demo_testset.csv)
python test_doctor.py     # 16/16, no net/key needed (mocked vision)
curl http://127.0.0.1:8000/api/selftest   # live: db_wal + verify + doctor seeds
```
Synthetic only. PPT me likho: "Demo-set 100%, field target 85% on 60 real samples, final authority Agri officer".

## Fasal Doctor 🌿 (naya tab)
Photo → crop/problem andaza + ilaaj + video + mausam/zone. Bina API key ke manual mode
(list se chuno) chalta hai.
**Videos (30 rows):** search se verified Hindi IDs nahi mile — galat link bharna jury risk
hai, isliye DEMO badge hai. Bharne ka tareeka:
```
python add_video.py --list                        # DEMO vs verified dekho
python add_video.py --check <youtube_id>          # video hai ya nahi (bina key)
python add_video.py p-blast <youtube_id> "DD Kisan"   # dekhne KE BAAD hi chalao
```
IDs DD Kisan / ICAR / KVK / state-agri videos khud dekhkar lo.
**Zones (17 zilon):** Punjab PAU 6-zone + Haryana Kisan Ayog I/II/III mapping verified;
mitt/groundwater generic + Soil Health Card/CGWB caveat ke saath.
**AI key:** `SWARN-BEEJ/.env` me ye 2 line likho, server restart karo — bas:
```
VISION_PROVIDER=gemini
GEMINI_API_KEY=tumhari-key (aistudio.google.com se free)
```
`/api/selftest` → `vision.ready:true` dikhe to AI chalu. Key code me kabhi mat likho.
