"""Fill official Category-II template -> docs/SWARN-BEEJ_Screen-1_Official.pptx
NEVER touches the original in Downloads. Run: python docs/fill_official.py"""
import shutil
from pathlib import Path
from pptx import Presentation
from pptx.util import Pt

SRC = Path(r"C:\Users\santosh\Downloads\Open Submission-DIPLOMA & HIGHER EDUCATION.pptx")
DST = Path(__file__).parent / "SWARN-BEEJ_Screen-1_Official.pptx"
shutil.copy2(SRC, DST)
p = Presentation(str(DST))

BODY = {
    0: ("SWARN-BEEJ (स्वर्ण-बीज): नकली बीज पकड़ो — स्कैन, बिल, शिकायत\n"
        "Local REG-001-OP • Village/Panchayat, Agriculture & Rural Economy\n"
        "Category-II • Solo, self-mentored • TRL 2 → 6 • Hindi offline PWA"),
    1: ("Team Leader: Aryan Singh (solo developer, Python/PWA)\n"
        "Formal mentor: none — self-mentored solo entry (allowed)\n"
        "Support: college + Kisan Call Centre 1800-180-1551 + KVK package of practices"),
    2: ("Punjab-Haryana ke chhote kisan nakli beej/keetnashak se 40–90% fasal gawa dete hain. "
        "Packet asli lagta hai, QR copy/fake, bill nahi milta — bina bill मुआवज़ा bhi nahi "
        "(Sirsa guar case 2012, 90% loss, 5-saal muqadma). Operational context: gaon ki dukaan, "
        "basic phone, weak network, Hindi-speaking farmer at shop counter."),
    3: ("Secondary evidence (verified): PIB 11-Feb-2025 — 2023-24 me 3,630 seed + 8,988 fertiliser + "
        "2,222 pesticide samples substandard; Bathinda Aug-2024 + Haryana Jan-2026 me spurious stock seized.\n"
        "Field photos/interviews: Phase-2 (Week 1–2) planned — remote video-call survey of 10 farmer families + "
        "15 packet photos + 5 bills. Current status: PENDING (honestly stated)."),
    4: ("SATHI portal exists but B2B/English/desktop-only — kisan ke phone par offline Hindi me nahi chalta. "
        "Dealer list closed; QR verification last-mile tak nahi pahunchta. Gap: Hindi voice + offline-first + "
        "bill-as-evidence + reused-QR check — koi existing app ye combo nahi deta."),
    5: ("SWARN-BEEJ PWA: (1) Scan & Sach — brand+batch+QR → GREEN/YELLOW/RED + confidence% + Hindi voice; "
        "(2) Bill Suraksha — bill photo+GPS+date save; (3) Shikayat Draft — 1-tap Hindi arzi (Copy/WhatsApp/PDF); "
        "(4) Fasal Doctor — leaf photo → problem + ilaaj + video + mausam/zone. Safe-default: unknown = YELLOW."),
    6: ("[Kisan phone] → PWA (offline-first, cached licensed list) → /api/verify (normalize + match + expiry + "
        "QR-batch + reuse-track) → signal + confidence → Bill/Complaint/Fasal-Doctor modules → SQLite "
        "(%LOCALAPPDATA%, WAL) → Officer dashboard/stats. Diagram: hand-drawn flow attached in video pitch."),
    7: ("Working: batch-prefix substring match on normalized (UPPER, no space/hyphen) text; expiry compare; "
        "QR must contain batch-prefix else YELLOW; same QR on different batch → reused flag; empty/unknown → "
        "YELLOW (never false GREEN). Voice via speechSynthesis hi-IN; offline via service-worker cache."),
    8: ("Validation (synthetic 19-case set, test_accuracy.py): 19/19 = 100% — 6 GREEN, 7 YELLOW, 2 RED + "
        "normalize/empty/expiry edge cases. Confidence: GREEN 92, RED 88–90, YELLOW 55–65. Field target: 85% "
        "on 60 real packets; final authority Agri officer. No fake-data claims."),
    9: ("Cost: app FREE for farmer; hosting < ₹2,000 (Render free tier); total BOM ≈ ₹2,000 one-time. "
        "Benefit: 1 acre ≈ ₹12,000 loss bachta (guar 7–8 q @₹30k, 40% loss). Scale: PB/HR → HP apple, UK masala."),
    10: ("Beneficiaries: lakhs of smallholders buying inputs every season; Agri officers "
        "get structured complaints with bill+GPS evidence. Replicable across states (same engine, new lists)."),
    11: ("Built: FastAPI+SQLite PWA live (Scan/Bill/Shikayat/Doctor/Officer), 19/19 + 16/16 tests, 17-district "
        "zone DB, Hindi UI. Demo: GREEN/YELLOW/RED one-tap + screen recording ready for video pitch."),
    12: ("User interaction: 10 phone interviews (farmer families of classmates) + Kisan Call Centre 1800-180-1551 "
        "expert call — PLANNED Week 1, status pending. Questions: nakli case? bill milta? QR check?"),
    13: ("W1: survey + PPT + 15 packet photos. W2: MVP + 60-sample test. W3: 15-farmer field test + 5-min video. "
        "W4: refine + final report + jury demo. Milestones weekly, solo-executable."),
    14: ("Solo: survey + build + test + report — Team Leader Aryan Singh. "
        "No formal mentor; advisory via college, Kisan Call Centre 1800-180-1551, KVK practices. "
        "No fabrication team needed (pure software)."),
    15: ("No lab/fab needed (software-only). Resources: laptop + Android phone + internet for CDN first-load. "
        "Institutional support: college (self-declared solo entry)."),
    16: ("Entry TRL-2 (concept + working MVP, synthetic validation) → Target TRL-6 (field-tested, 15 farmers, "
        "85% on 60 packets). TRL-4-6 National track NOT claimed — Local track only."),
    17: ("Technical drawings: app screen-flow + API map (in video pitch). Key logic: normalize→match→expiry→"
        "QR→reuse→signal; accuracy harness test_accuracy.py (deterministic, qr_scans reset per run)."),
    18: ("Prior art: Plantix (disease ID, no fake-input check), SATHI portal (B2B traceability, no farmer UI), "
        "generic QR scanners (no licensed-list logic). Survey date: Oct 2026 (web). Gap confirmed."),
    19: ("Lab/fab access: not required. Field access: agro shops near home + remote farmer video-calls + "
        "college peers. Fabrication: nil (PWA, no hardware)."),
    20: ("Novelty: reused-QR cross-packet flag + bill-as-evidence-chain + SATHI last-mile Hindi offline bundle. "
        "IPR: low — open approach recommended; no patent claimed. Honest scope: process innovation, not device."),
    21: ("PIB 11-Feb-2025 (seed/fertiliser/pesticide samples) • SATHI portal (seed traceability) • "
        "CGWB groundwater notes • Open-Meteo (weather, no key) • PAU 6-zone + Haryana Kisan Ayog I/II/III • "
        "ICAR/KVK package of practices (treatments source) • Bathinda/Haryana seizure news (2024/2026)"),
}

for idx, text in BODY.items():
    s = p.slides[idx]
    body = s.shapes[1]
    tf = body.text_frame
    tf.clear()
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.text = "•  " + line if not line.startswith(("SWARN", "Team Leader", "Solo:")) else line
        par.font.size = Pt(18)
        par.font.name = "Nirmala UI"
        par.space_after = Pt(8)

p.save(str(DST))
print("saved:", DST, "| slides:", len(p.slides._sldIdLst))
