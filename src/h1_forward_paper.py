"""Simulasi paper trade H1 di periode forward 2026-08-01..2026-10-31 (ILUSTRASI).

Aturan portofolio = src/portfolio.py apa adanya: modal $100, margin 3% x ekuitas
berjalan x leverage 2 (~$6/posisi), maks 3 posisi, hold 48 jam, gate stepSize pada
notional berjalan. Aturan pemilihan di antara ~48 kandidat/hari BELUM ditetapkan,
jadi yang utama = pilih acak (200 seed). "Funding paling negatif" ditampilkan
sebagai pembanding saja — itu bukan bagian H1 terdaftar.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import h1_forward as H
import portfolio as P

raw = pd.read_pickle(H.OUT / "panel_raw.pkl")
e = H.assemble(raw)
e["di"] = (e["date"] - pd.Timestamp("2026-08-01", tz="UTC")).dt.days   # hari kalender
d = e.dropna(subset=["net", "close_t", "step_size"])
H1 = d["H1"]
day0 = pd.Timestamp("2026-08-01", tz="UTC")

def run(mask, pick, seed):
    cv, tr = P.simulate(d, mask, pick, "net", seed=seed)
    cv["date"] = day0 + pd.to_timedelta(cv["di"], unit="D")
    tr["date"] = day0 + pd.to_timedelta(tr["exit_day"], unit="D")
    return cv, tr

seeds = range(200)
rnd = [run(H1, "random", s) for s in seeds]
base = [run(pd.Series(True, index=d.index), "random", s) for s in seeds]
mf_cv, mf_tr = run(H1, "min_funding", 0)

def table(runs):
    cvs = pd.concat([c.set_index("date")["equity"].rename(i) for i, (c, _) in enumerate(runs)], axis=1).ffill()
    return cvs
R, B = table(rnd), table(base)
out = pd.DataFrame({"h1_p05": R.quantile(.05, axis=1), "h1_p25": R.quantile(.25, axis=1),
                    "h1_median": R.median(axis=1), "h1_p75": R.quantile(.75, axis=1),
                    "h1_p95": R.quantile(.95, axis=1), "baseline_median": B.median(axis=1)})
out = out.join(mf_cv.set_index("date")["equity"].rename("h1_min_funding"))
res = H.RES
out.to_csv(res / "paper_equity.csv")

def summ(cv, tr):
    eq = cv["equity"].to_numpy(); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    m = tr.groupby(tr["date"].dt.strftime("%Y-%m"))["pnl"].sum().to_dict()
    return dict(final=eq[-1], pnl=eq[-1] - 100, n=len(tr), win=(tr["ret"] > 0).mean(),
                maxdd=dd, best=tr["pnl"].max(), worst=tr["pnl"].min(), monthly=m)
S_r = [summ(c, t) for c, t in rnd]; S_b = [summ(c, t) for c, t in base]
f = np.array([s["pnl"] for s in S_r]); fb = np.array([s["pnl"] for s in S_b])
print("H1 acak: PnL median %.2f  p5 %.2f  p95 %.2f  untung di %.0f%% seed  maxDD med %.1f%%  n %d  win %.1f%%"
      % (np.median(f), np.percentile(f, 5), np.percentile(f, 95), (f > 0).mean()*100,
         np.median([s["maxdd"] for s in S_r])*100, S_r[0]["n"], np.median([s["win"] for s in S_r])*100))
print("Baseline acak: PnL median %.2f p5 %.2f p95 %.2f" % (np.median(fb), np.percentile(fb, 5), np.percentile(fb, 95)))
mm = pd.DataFrame([s["monthly"] for s in S_r]); print("H1 acak PnL bulanan median:", mm.median().round(2).to_dict())
mb = pd.DataFrame([s["monthly"] for s in S_b]); mb.to_csv(res / "paper_monthly_baseline.csv", index=False); print("Baseline PnL bulanan median:", mb.median().round(2).to_dict())
s = summ(mf_cv, mf_tr); print("min_funding:", {k: (round(v, 3) if not isinstance(v, dict) else {a: round(b, 2) for a, b in v.items()}) for k, v in s.items()})
mm.to_csv(res / "paper_monthly_random.csv", index=False)
mf_tr.to_csv(res / "paper_trades_min_funding.csv", index=False)
# kontribusi ekor di skema acak: berapa seed yang menangkap pump >+100%
big = d[H1 & (d["net"] > 1.0)]
print("trade net>+100% tersedia:", len(big))
