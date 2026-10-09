"""Render actual pilot outputs; no fabricated recognition or reference labels."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(line) for line in (ROOT / "data/references.jsonl").read_text().splitlines() if line.strip()]
out = ROOT / "output/figures"
out.mkdir(parents=True, exist_ok=True)

canvas = Image.new("RGB", (1200, len(rows) * 100), "#fffdf8")
draw = ImageDraw.Draw(canvas)
for i, row in enumerate(rows):
    with Image.open(ROOT / row["image"]) as source:
        image = ImageOps.contain(source, (800, 75))
        canvas.paste(image, (380, i * 100 + 10))
    draw.text((10, i * 100 + 20), row["id"].replace("nypl-57733030-", "") + " | " + row["text"], fill="#23372f")
canvas.save(out / "pilot-crops.jpg", quality=90)

labels = ["Original color", "Grayscale", "Grayscale + contrast"]
reports = [json.loads((ROOT / f"output/reports/trocr-{variant}.json").read_text()) for variant in ["raw", "grayscale", "contrast"]]
plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout="constrained")
fig.patch.set_facecolor("#fffdf8")
for ax in axes:
    ax.set_facecolor("#fffdf8")
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)
colors = ["#b6b3a7", "#749581", "#325f47"]
cer = [r["overall"]["cer"] * 100 for r in reports]
matches = [r["amount_digit_sequence"]["rate"] * 100 for r in reports]
for ax, values, title, ymax in [(axes[0], cer, "Character error rate · 22 crops", 185),
                               (axes[1], matches, "Amount digit match · 8 eligible crops", 110)]:
    ax.bar(labels, values, color=colors, width=.6)
    ax.set_ylim(0, ymax); ax.set_ylabel("Percent"); ax.set_title(title, loc="left", pad=15)
    ax.tick_params(axis="x", labelsize=9)
    for i, value in enumerate(values):
        ax.text(i, value + ymax * .025, f"{value:.1f}%", ha="center", fontweight="bold")
fig.suptitle("Historical ledger preprocessing pilot", fontsize=18, x=.01, ha="left")
fig.supxlabel("One source page · assistant draft labels · exploratory, not independently validated accuracy", fontsize=10)
fig.savefig(out / "preprocessing-pilot.png", dpi=180)
plt.close(fig)

print("Rendered real crop contact sheet and provisional comparison figure")
