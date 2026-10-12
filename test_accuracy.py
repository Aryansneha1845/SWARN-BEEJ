"""Accuracy check without real packets. Run: python test_accuracy.py"""
import csv
from pathlib import Path
import app
from app import VerifyIn, get_con

# deterministic: clear QR reuse memory so re-runs don't flag same-batch repeats
with get_con() as con:
    con.execute("DELETE FROM qr_scans")

csv_path = Path(__file__).parent / "docs" / "demo_testset.csv"
rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
ok = 0
print(f"Total cases: {len(rows)}  (db: {app.DB})")
for r in rows:
    got = app.verify(VerifyIn(brand=r["brand"], batch=r["batch"], qr_text=r["qr_text"]))["signal"]
    exp = r["expected"].strip().upper()
    mark = "OK" if got == exp else f"FAIL(got {got})"
    if got == exp:
        ok += 1
    print(f"{mark:12} | brand={r['brand']!r} batch={r['batch']!r} -> {got} (exp {exp}) | {r['note']}")
print(f"\nAccuracy: {ok}/{len(rows)} = {ok/len(rows)*100:.1f}%")
print("Note: synthetic set. Safe-default: unknown/empty -> YELLOW (officer verify).")
