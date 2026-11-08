import sys
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
R = Path(__file__).resolve().parent.parent / "results" / "h1_forward"
eq = pd.read_csv(R / "paper_equity.csv", parse_dates=["date"]).set_index("date")
mm = pd.read_csv(R / "paper_monthly_random.csv")
mt = pd.read_csv(R / "paper_trades_min_funding.csv", parse_dates=["date"])
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8984"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
fig = plt.figure(figsize=(12, 8.2), facecolor=SURF)
gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1], hspace=0.42)
ax = fig.add_subplot(gs[0]); ax.set_facecolor(SURF)
x = eq.index
ax.fill_between(x, eq.h1_p05, eq.h1_p95, color=BLUE, alpha=.10, lw=0)
ax.fill_between(x, eq.h1_p25, eq.h1_p75, color=BLUE, alpha=.22, lw=0)
ax.plot(x, eq.h1_median, color=BLUE, lw=2)
ax.plot(x, eq.baseline_median, color=GRAY, lw=2)
ax.plot(x, eq.h1_min_funding.ffill(), color=ORANGE, lw=2, ls=(0, (4, 2)))
ax.axhline(100, color=INK2, lw=.8, alpha=.5)
ax.axvspan(pd.Timestamp("2026-10-26", tz="UTC"), pd.Timestamp("2026-10-30", tz="UTC"), color=GRAY, alpha=.12, lw=0)
ax.text(pd.Timestamp("2026-10-28", tz="UTC"), ax.get_ylim()[0] + 1, "data\nhilang", ha="center", va="bottom", fontsize=8, color=INK2)
last = x[-1]
def lab(y, t, c): ax.annotate(t, (last, y), xytext=(8, 0), textcoords="offset points", va="center", color=INK, fontsize=9.5,
                              bbox=dict(boxstyle="round,pad=0.25", fc=SURF, ec=c, lw=1.2))
lab(eq.h1_min_funding.ffill().iloc[-1], f"H1 · funding paling negatif  \\${eq.h1_min_funding.ffill().iloc[-1]:.2f}", ORANGE)
lab(eq.h1_median.iloc[-1], f"H1 · pilih acak (median)  \\${eq.h1_median.iloc[-1]:.2f}", BLUE)
lab(eq.baseline_median.iloc[-1], f"Tanpa sinyal · koin acak  \\${eq.baseline_median.iloc[-1]:.2f}", GRAY)
ax.set_xlim(x[0], last + pd.Timedelta(days=1))
ax.grid(axis="y", color=GRID, lw=.8); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.set_ylabel("Ekuitas (USD)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.set_title("Paper trade H1 · modal \\$100 · 3 slot × ~\\$6 · hold 48 jam · 1 Ags – 31 Okt 2026",
             loc="left", fontsize=13, color=INK, fontweight="semibold", pad=24)
ax.text(0, 1.02, "Pita biru = rentang 200 simulasi pilih acak (gelap: 25–75%, terang: 5–95%). "
        "Garis oranye bukan aturan terdaftar — hanya pembanding.", transform=ax.transAxes, fontsize=9, color=INK2)
fig.subplots_adjust(right=0.74, left=0.07, top=0.9, bottom=0.07)
# monthly PnL
b = fig.add_subplot(gs[1]); b.set_facecolor(SURF)
months = ["2026-08", "2026-09", "2026-10"]; names = ["Agustus", "September", "Oktober"]
rmed = [mm[m].median() for m in months]
mf = mt.groupby(mt.date.dt.strftime("%Y-%m")).pnl.sum().reindex(months).fillna(0).tolist()
mb = pd.read_csv(R / "paper_monthly_baseline.csv")
bmon = [mb[m].median() for m in months]
w = .26; xi = np.arange(3)
for off, vals, c, n in ((-w, bmon, GRAY, "Tanpa sinyal"), (0, rmed, BLUE, "H1 acak (median)"), (w, mf, ORANGE, "H1 funding paling negatif")):
    bars = b.bar(xi + off, vals, w - .03, color=c, label=n, edgecolor=SURF, lw=2)
    for xx, v in zip(xi + off, vals):
        b.text(xx, v + (0.4 if v >= 0 else -0.4), f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5, color=INK)
b.axhline(0, color=INK2, lw=.8)
b.set_xticks(xi, names); b.set_ylabel("PnL bulanan (USD)")
b.grid(axis="y", color=GRID, lw=.8); b.set_axisbelow(True)
for s in ("top", "right"): b.spines[s].set_visible(False)
b.legend(frameon=False, ncol=3, loc="upper right", fontsize=9, bbox_to_anchor=(1.0, 1.22))
b.set_ylim(min(min(rmed), min(mf), min(bmon)) - 3, max(max(rmed), max(mf), max(bmon)) + 3)
out = R / "paper_trade_3bulan.png"; fig.savefig(out, dpi=150, facecolor=SURF); print(out)
