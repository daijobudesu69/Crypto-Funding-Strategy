"""Uji forward H1 — SATU KALI PAKAI. Periode 2026-08-01..2026-10-31.

Definisi disalin persis dari HYPOTHESIS_REGISTER.md (H1, dikunci 2026-08-23).
Tidak ada ambang yang disetel di file ini.

Memakai ulang pipeline yang sama (fetch.py / features.py / panel.py / stats.py)
dengan konstanta periode di-override DI MEMORI saja; config.py tidak diubah dan
panel in-sample (data/interim, data/panel.parquet, data/raw/manifest.json) tidak
disentuh. Output fitur -> data/interim_h1fwd/.

Penyesuaian data (bukan penyetelan aturan):
  * Klines nol-volume di ekor seri (perp delisted yang arsipnya tetap terbit)
    dibuang -> harga NaN -> symbol itu tidak eligible / label NaN.
  * Baris dengan dollar_vol_24h == 0 tidak eligible.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

# ---------------------------------------------------------------- periode uji (DIKUNCI)
C.START_DATE = "2026-08-01"
C.END_DATE = "2026-10-31"
C.WARMUP_MONTHS = 2
C.FWD_TAIL_DAYS = 5

import fetch as F          # noqa: E402
import features as FE      # noqa: E402
import panel as P          # noqa: E402
import stats as S          # noqa: E402

COST = 0.0004              # maker 0.02% x 2
OUT = C.DATA / "interim_h1fwd"
RES = C.RESULTS / "h1_forward"

_orig_load_klines = FE.load_klines
TRIM_LOG: dict[str, int] = {}


def load_klines_trimmed(sym: str):
    k, steps = _orig_load_klines(sym)
    if k.empty:
        return k, steps
    v = k["volume"].to_numpy(dtype=float)
    live = np.flatnonzero(np.isfinite(v) & (v > 0))
    if len(live) == 0:
        return k.iloc[0:0], steps
    last = live[-1]
    if last < len(k) - 1:
        TRIM_LOG[sym] = int(len(k) - 1 - last)
        k = k.iloc[: last + 1]
    return k, steps


FE.load_klines = load_klines_trimmed


def do_fetch(workers: int = 24) -> list[str]:
    t0 = time.time()
    symbols = F.discover_symbols()
    months, tails = F.target_months(), F.tail_days()
    print(f"symbols={len(symbols)} months={months} tails={tails[0]}..{tails[-1]}", flush=True)
    jobs = [(s, u, p) for s in symbols for (u, p) in F.jobs_for_symbol(s, months, tails)]
    st = {"ok": 0, "cached": 0, "absent": 0, "fail": 0}
    fails = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(F._save_zip, u, p): (s, u) for s, u, p in jobs}
        for f in as_completed(futs):
            r = f.result()
            st[r] += 1
            if r == "fail":
                fails.append(futs[f][1])
    print(f"fetch {len(jobs)} files in {(time.time()-t0)/60:.1f} min: {st}", flush=True)
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "fetch_log.json").write_text(json.dumps({"stats": st, "fails": fails}, indent=1))
    return symbols


def build(symbols: list[str]) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    parts, errs = [], []

    def one(sym):
        try:
            return sym, FE.build_symbol(sym)
        except Exception as e:
            return sym, e

    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, f in enumerate(as_completed([ex.submit(one, s) for s in symbols]), 1):
            sym, df = f.result()
            if isinstance(df, Exception):
                errs.append((sym, repr(df)))
            elif df is not None and not df.empty:
                parts.append(df)
            if i % 200 == 0:
                print(f"  features {i}/{len(symbols)} {(time.time()-t0)/60:.1f}m", flush=True)
    print(f"features: {len(parts)} symbols, {len(errs)} errors, {(time.time()-t0)/60:.1f} min")
    for e in errs[:10]:
        print("  ERR", e)
    d = pd.concat(parts, ignore_index=True)
    d.to_pickle(OUT / "panel_raw.pkl")
    return d


def assemble(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d["eligible"] = (
        (d["n_hist_days"] >= C.MIN_HISTORY_DAYS)
        & d["close_t"].notna() & (d["close_t"] > 0)
        & d["entry_open"].notna() & (d["entry_open"] > 0)
        & d["step_size"].notna()
        & ~d["is_benchmark"].astype(bool)
        & (d["dollar_vol_24h"] > 0)
    )
    d = P.add_executability(d)
    e = d[d["eligible"]].copy()
    # grouping tanggal via factorize (BUKAN astype int64 // 10**9 — bug pandas 3.0)
    e["di"], _ = pd.factorize(e["date"], sort=True)
    e["zrank"] = e.groupby("di")["funding_ts_z30"].rank(pct=True, method="first")
    e["net"] = e["fwd_48h"] - COST - e["funding_paid_48h"]
    e["H1"] = ((e["funding_24h_sum"] <= 0) & (e["zrank"] <= 0.20)).fillna(False)
    return e


def report(e: pd.DataFrame) -> dict:
    sig_all = e[e["H1"] & e["executable_100usd"]]
    sig = sig_all.dropna(subset=["net"])
    dropped = sig_all[sig_all["net"].isna()]
    r = S.cluster_mean(sig["net"].to_numpy(), sig["di"].to_numpy())
    lo, hi = S.cluster_bootstrap_ci(sig["net"].to_numpy(), sig["di"].to_numpy(),
                                    reps=C.BOOTSTRAP_REPS, seed=C.SEED)
    price = S.cluster_mean((sig["fwd_48h"] - COST).to_numpy(), sig["di"].to_numpy())
    fund = S.cluster_mean((-sig["funding_paid_48h"]).to_numpy(), sig["di"].to_numpy())
    # pembanding: semua eligible+executable yang BUKAN sinyal (deskriptif saja)
    rest = e[~e["H1"] & e["executable_100usd"]].dropna(subset=["net"])
    sp = S.cluster_diff(sig["net"].to_numpy(), sig["di"].to_numpy(),
                        rest["net"].to_numpy(), rest["di"].to_numpy())
    monthly = {}
    for m, g in sig.groupby(sig["date"].dt.strftime("%Y-%m")):
        x = S.cluster_mean(g["net"].to_numpy(), g["di"].to_numpy())
        monthly[m] = {"n": int(x["n_obs"]), "days": int(x["n_days"]),
                      "mean": x["mean"], "t": x["t"]}
    passed = bool(r["mean"] > 0 and r["t"] > 2.0)
    out = {
        "period": [C.START_DATE, C.END_DATE],
        "n_obs": int(r["n_obs"]), "n_days": int(r["n_days"]),
        "mean_net": r["mean"], "se": r["se"], "t_clustered": r["t"], "p": r["p"],
        "ci95_t": [r["ci_lo"], r["ci_hi"]], "ci95_bootstrap": [lo, hi],
        "price_component_after_fee": price["mean"], "funding_component": fund["mean"],
        "spread_vs_rest": sp["diff"], "spread_t": sp["t"],
        "monthly": monthly,
        "signals_per_day": len(sig) / max(r["n_days"], 1),
        "n_signals_dropped_nan_label": int(len(dropped)),
        "dropped_dates": sorted({str(x.date()) for x in dropped["date"]}),
        "date_min": str(sig["date"].min().date()), "date_max": str(sig["date"].max().date()),
        "n_symbols_eligible_avg": float(e.groupby("di").size().mean()),
        "n_symbols_trimmed_zero_vol": len(TRIM_LOG),
        "verdict": "LULUS" if passed else "GAGAL",
    }
    RES.mkdir(parents=True, exist_ok=True)
    sig[["date", "symbol", "funding_24h_sum", "funding_ts_z30", "zrank", "entry_open",
         "fwd_48h", "funding_paid_48h", "net"]].to_csv(RES / "signals.csv", index=False)
    (RES / "result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("all", "fetch"):
        syms = do_fetch()
    else:
        syms = F.discover_symbols()
    if step in ("all", "fetch", "build"):
        raw = build(syms)
    else:
        raw = pd.read_pickle(OUT / "panel_raw.pkl")
    report(assemble(raw))
