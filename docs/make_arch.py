"""System architecture diagram -> docs/architecture.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(12, 7))
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis("off")
fig.patch.set_facecolor("#FFFAF0")
ax.set_facecolor("#FFFAF0")

GREEN, GOLD, CREAM, DARK = "#0F3D24", "#F2B705", "#FFFFFF", "#1D1C16"


def box(x, y, w, h, title, sub, fc):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                       fc=fc, ec=GREEN, lw=1.6)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h - 0.45, title, ha="center", va="top",
            fontsize=10, weight="bold", color=DARK)
    ax.text(x + w / 2, y + h - 1.0, sub, ha="center", va="top",
            fontsize=8, color="#414942")


def arrow(x1, y1, x2, y2, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 color=GREEN, lw=1.6, mutation_scale=14))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, label, ha="center",
                fontsize=8, color=GREEN, weight="bold")


ax.text(6, 6.6, "SWARN-BEEJ — System Architecture (Local REG-001, TRL-2 to 6)",
        ha="center", fontsize=13, weight="bold", color=GREEN)

box(0.3, 3.6, 2.6, 2.0, "Kisan Phone", "PWA Hindi\nOffline-first\nCamera/GPS/Voice", CREAM)
box(4.7, 3.6, 2.6, 2.0, "FastAPI Server", "/api/verify /bill\n/complaint /diagnose\n/context", "#FFF3C4")
box(9.1, 3.6, 2.6, 2.0, "SQLite (WAL)", "Local DB\nNo cloud\nDPDP minimal", CREAM)

box(0.3, 0.7, 2.6, 1.9, "Verify Engine", "Normalize\nMatch-Expiry\nQR-Reuse\nGREEN/YELLOW/RED", "#E4F2E7")
box(4.7, 0.7, 2.6, 1.9, "Modules", "Bill+GPS  Shikayat\nFasal Doctor  Officer", CREAM)
box(9.1, 0.7, 2.6, 1.9, "External (free)", "Open-Meteo\nYouTube-nocookie\nSATHI lists", "#E4F2E7")

arrow(2.9, 4.6, 4.7, 4.6, "HTTP/JSON (local)")
arrow(7.3, 4.6, 9.1, 4.6, "SQL")
arrow(6.0, 3.6, 6.0, 2.6, "")
arrow(1.6, 3.6, 1.6, 2.6, "")
arrow(10.4, 3.6, 10.4, 2.6, "")
arrow(7.3, 1.65, 9.1, 1.65, "fetch")
arrow(4.7, 1.65, 2.9, 1.65, "")

fig.tight_layout()
fig.savefig("docs/architecture.png", dpi=160)
print("saved docs/architecture.png")
