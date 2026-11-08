"""Uji forward H3 — SATU KALI PAKAI. Periode 2026-11-01..2027-01-31.

Definisi: HYPOTHESIS_REGISTER.md (H3) dan H3_SPEC_FCL.md §3. Tidak ada ambang yang
disetel di sini.

GERBANG (aturan Dew, 2026-11-08): sebelum menjalankan skrip ini, minta data
terbaru ke Dew. Hasilnya dilaporkan ke Dew; H3 tidak boleh live di FCL tanpa
approval eksplisit Dew. Skrip ini menolak jalan tanpa --dew-data-ok.

Jalankan (setelah arsip funding 2027-01 terbit, sekitar 2027-02-08):
    python src/h3_forward.py --dew-data-ok
    python src/h3_forward.py --dew-data-ok --step report    # pakai panel yang sudah dibangun

Opsi --start/--end hanya untuk parity check bot FCL di periode historis.
Hasil di luar periode resmi BUKAN uji H3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import h1_forward as H          # memakai ulang fetch/build + trim nol-volume
import stats as S

OFFICIAL = ("2026-11-01", "2027-01-31")
COST = 0.0013                   # 0,065% per sisi x 2 (HYPE)
COINS = C.ROOT / "results" / "h3" / "coins_h3_frozen.csv"
COINS_SHA = "fce7d7914dd184ea0a7236638ec7948283d31b49cff504cff3e013a34a150f23"


def frozen_coins() -> list[str]:
    # dinormalkan ke LF: git di Windows (autocrlf) bisa menulis ulang jadi CRLF saat checkout
    sha = hashlib.sha256(COINS.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if sha != COINS_SHA:
        raise SystemExit(f"coins_h3_frozen.csv berubah (sha {sha}) — H3 terkunci ke daftar beku.")
    return sorted(pd.read_csv(COINS)["binance"].astype(str))


def assemble(raw: pd.DataFrame, coins: list[str]) -> pd.DataFrame:
    d = raw[raw["symbol"].isin(coins)].copy()
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d = d[(d["n_hist_days"] >= C.MIN_HISTORY_DAYS) & (d["entry_open"] > 0)
          & (d["close_t"] > 0) & (d["dollar_vol_24h"] > 0)].copy()
    d["di"], _ = pd.factorize(d["date"], sort=True)      # BUKAN astype int64 (bug pandas 3.0)
    d["zrank"] = d.groupby("di")["funding_ts_z30"].rank(pct=True, method="first")
    d["net"] = d["fwd_48h"] - COST - d["funding_paid_48h"]
    d["H3"] = ((d["funding_24h_sum"] <= 0) & (d["zrank"] <= 0.20)).fillna(False)
    return d


def report(d: pd.DataFrame, res: Path, official: bool) -> dict:
    sig_all = d[d["H3"]]
    sig = sig_all.dropna(subset=["net"])
    r = S.cluster_mean(sig["net"].to_numpy(), sig["di"].to_numpy())
    lo, hi = S.cluster_bootstrap_ci(sig["net"].to_numpy(), sig["di"].to_numpy(),
                                    reps=C.BOOTSTRAP_REPS, seed=C.SEED)
    monthly = {}
    for m, g in sig.groupby(sig["date"].dt.strftime("%Y-%m")):
        x = S.cluster_mean(g["net"].to_numpy(), g["di"].to_numpy())
        monthly[m] = {"n": int(x["n_obs"]), "mean": x["mean"], "t": x["t"]}
    out = {
        "official_test": official, "period": [C.START_DATE, C.END_DATE],
        "n_obs": int(r["n_obs"]), "n_days": int(r["n_days"]),
        "mean_net": r["mean"], "t_clustered": r["t"], "p": r["p"],
        "ci95_t": [r["ci_lo"], r["ci_hi"]], "ci95_bootstrap": [lo, hi],
        "median": float(sig["net"].median()), "pos_frac": float((sig["net"] > 0).mean()),
        "price_component": float((sig["fwd_48h"] - COST).mean()),
        "funding_component": float((-sig["funding_paid_48h"]).mean()),
        "monthly": monthly, "signals_per_day": len(sig) / max(r["n_days"], 1),
        "n_dropped_nan_label": int(sig_all["net"].isna().sum()),
        "verdict": ("LULUS" if (r["mean"] > 0 and r["t"] > 2.0) else "GAGAL") if official else "BUKAN UJI RESMI",
        "live_gate": "Live di FCL tetap TERKUNCI sampai Dew memberi approval eksplisit.",
    }
    res.mkdir(parents=True, exist_ok=True)
    sig[["date", "symbol", "funding_24h_sum", "funding_ts_z30", "zrank", "entry_open",
         "fwd_48h", "funding_paid_48h", "net"]].to_csv(res / "signals.csv", index=False)
    (res / "result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dew-data-ok", action="store_true",
                    help="konfirmasi bahwa Dew sudah memberi/mengizinkan data terbaru")
    ap.add_argument("--step", choices=["all", "build", "report"], default="all")
    ap.add_argument("--start", default=OFFICIAL[0])
    ap.add_argument("--end", default=OFFICIAL[1])
    a = ap.parse_args()
    if not a.dew_data_ok:
        raise SystemExit("STOP: minta data terbaru ke Dew dulu (aturan gerbang H3). "
                         "Jalankan ulang dengan --dew-data-ok setelah Dew mengizinkan.")
    official = (a.start, a.end) == OFFICIAL
    C.START_DATE, C.END_DATE = a.start, a.end
    tag = "forward" if official else f"check_{a.start}_{a.end}"
    H.OUT = C.DATA / f"interim_h3_{tag}"
    res = C.RESULTS / "h3" / tag
    H.RES = res                     # fetch_log jangan menimpa hasil H1
    coins = frozen_coins()
    if a.step in ("all", "build"):
        if a.step == "all":
            H.do_fetch()
        raw = H.build(coins)
    else:
        raw = pd.read_pickle(H.OUT / "panel_raw.pkl")
    report(assemble(raw, coins), res, official)


if __name__ == "__main__":
    main()
