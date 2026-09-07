"""Analisa hasil VEB dengan standar Sesi A: SE cluster per tanggal, walk-forward."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import veb_engine as E
from stats import cluster_mean, cluster_bootstrap_ci

# ROOT diturunkan dari lokasi file ini, bukan path absolut. Sebelum audit
# 2026-09-07 baris ini berbunyi Path(r"C:/Crypto data 2") - kode ini mati
# begitu repo di-clone orang lain atau foldernya dipindah/di-rename.
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "veb"
COST = 0.0020          # taker 0,05% x2 + slippage 0,05% x2 (keputusan Dew 2026-08-25)


def load(which: str) -> pd.DataFrame:
    tr = pd.read_csv(OUT / f"trades_{which}.csv")
    return E.enrich(tr, COST)


def blk(t: pd.DataFrame, col: str, label: str) -> dict:
    r = cluster_mean(t[col], t["sig_date"])
    lo, hi = cluster_bootstrap_ci(t[col], t["sig_date"], reps=2000, seed=20260825)
    return dict(label=label, n=r["n_obs"], n_days=r["n_days"], mean=r["mean"],
                t=r["t"], p=r["p"], ci_lo=r["ci_lo"], ci_hi=r["ci_hi"],
                bs_lo=lo, bs_hi=hi)


def summarize(t: pd.DataFrame, tag: str) -> pd.DataFrame:
    rows = [
        blk(t, "Rgross_pess", "R kotor (tanpa biaya & funding)"),
        blk(t, "R_pess", f"R bersih (biaya {COST*100:.2f}% + funding)"),
        blk(t, "R_opt", "R bersih - tie-break optimis"),
        blk(t, "R_4h", "R bersih - scan bar 4H saja (metode lama)"),
        blk(t, "net_pess", "return bersih % notional"),
        blk(t, "gross_pess", "return kotor % notional"),
    ]
    df = pd.DataFrame(rows)
    df.insert(0, "universe", tag)
    return df


def walkforward(t: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    t = t.sort_values("sig_date")
    per = t["sig_date"].dt.to_period("M")
    ms = sorted(per.unique())
    rows = []
    for i in range(0, len(ms), months):
        grp = ms[i:i + months]
        s = t[per.isin(grp)]
        if len(s) < 10:
            continue
        r = cluster_mean(s["R_pess"], s["sig_date"])
        rows.append(dict(period=f"{grp[0]}..{grp[-1]}", n=len(s), avgR=r["mean"],
                         t=r["t"], win=float((s["net_pess"] > 0).mean())))
    return pd.DataFrame(rows)


def per_symbol(t: pd.DataFrame) -> pd.DataFrame:
    g = t.groupby("symbol")
    d = pd.DataFrame({
        "n": g.size(),
        "avgR_gross": g["Rgross_pess"].mean(),
        "avgR_net": g["R_pess"].mean(),
        "win": g.apply(lambda x: (x["net_pess"] > 0).mean(), include_groups=False),
        "med_stop_pct": g["stop_pct"].median(),
        "tp_rate": g.apply(lambda x: (x["exit_pess"] == "TP").mean(), include_groups=False),
        "sl_rate": g.apply(lambda x: (x["exit_pess"] == "SL").mean(), include_groups=False),
        "time_rate": g.apply(lambda x: (x["exit_pess"] == "TIME").mean(), include_groups=False),
    })
    return d.sort_values("avgR_net", ascending=False)


def cost_curve(tr_raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in (0.0, 0.0004, 0.0010, 0.0020, 0.0030):
        t = E.enrich(tr_raw, c)
        r = cluster_mean(t["R_pess"], t["sig_date"])
        rows.append(dict(cost_rt=c, avgR=r["mean"], t=r["t"],
                         win=float((t["net_pess"] > 0).mean()),
                         exp_pct=float(t["net_pess"].mean())))
    return pd.DataFrame(rows)


def exit_mix(t: pd.DataFrame) -> pd.DataFrame:
    m = t["exit_pess"].value_counts(normalize=True).rename("share").to_frame()
    m["n"] = t["exit_pess"].value_counts()
    m["avgR_net"] = t.groupby("exit_pess")["R_pess"].mean()
    m["median_hold_h"] = t.groupby("exit_pess")["hold_h"].median()
    return m
