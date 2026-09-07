"""Simulasi portofolio VEB: 3 slot, rotasi mingguan (spec §7.1), sizing spec §6.1.

Dua varian sizing:
  'spec' : cap leverage PER POSISI (persis seperti tertulis di spec §6.1)
  'fix'  : cap leverage TOTAL PORTOFOLIO (koreksi bug PERBANDINGAN §5.3)
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# Salinan kedua dari konstanta gate. Sebelum audit 2026-09-07 isinya
# {"BTCUSDT": 100.0, "ETHUSDT": 20.0} - salinan dari nilai config.py yang ternyata
# SALAH (lihat AUDIT.md B4): exchangeInfo asli menunjukkan BTC = 50, dan
# BCH/LTC/ETC/LINK = 20 tidak terdaftar sama sekali. Sekarang diambil langsung dari
# src/config.py supaya tidak ada dua sumber kebenaran yang bisa menyimpang lagi.
# CATATAN: file di results/veb/ dihasilkan dengan nilai LAMA dan sengaja TIDAK
# di-regenerate - H2 sudah GAGAL/DITUTUP, dan koreksi min-notional tidak akan
# membalik vonis itu.
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from config import MIN_NOTIONAL_OVERRIDE as MIN_NOTIONAL, DEFAULT_MIN_NOTIONAL  # noqa: E402


def simulate(tr: pd.DataFrame, *, equity0=100.0, risk_pct=0.02, max_lev=2.0,
             slots=3, mode="spec", kill_dd=0.30, symbols=None):
    tr = tr.sort_values(["sig_ts", "symbol"]).reset_index(drop=True)
    syms = sorted(symbols if symbols is not None else tr["symbol"].unique())
    ns = len(syms)
    rank = {s: i for i, s in enumerate(syms)}

    equity = equity0
    peak = equity0
    killed = False
    open_pos = []          # dict(symbol, ex_ts, notional, net)
    log, curve, skipped = [], [], []

    def close_due(until_ts):
        nonlocal equity, peak, killed, open_pos
        due = [p for p in open_pos if p["ex_ts"] <= until_ts]
        for p in sorted(due, key=lambda x: x["ex_ts"]):
            pnl = p["notional"] * p["net"]
            equity += pnl
            peak = max(peak, equity)
            log.append(dict(symbol=p["symbol"], ent_ts=p["ent_ts"], ex_ts=p["ex_ts"],
                            notional=p["notional"], net=p["net"], pnl=pnl,
                            equity=equity, lev=p["lev"], exit=p["exit"]))
            curve.append((p["ex_ts"], equity))
            if not killed and peak > 0 and (1.0 - equity / peak) >= kill_dd:
                killed = True
        open_pos = [p for p in open_pos if p["ex_ts"] > until_ts]

    for bar_ts, grp in tr.groupby("sig_ts", sort=True):
        ent_ts = int(grp["ent_ts"].iloc[0])
        close_due(ent_ts)
        if killed:
            continue
        free = slots - len(open_pos)
        if free <= 0:
            continue
        # rotasi mingguan spec §7.1
        wk = pd.Timestamp(bar_ts, unit="ms").isocalendar().week
        start = wk % ns if ns else 0
        held = {p["symbol"] for p in open_pos}
        cand = grp[~grp["symbol"].isin(held)].copy()
        cand["prio"] = [(rank[s] - start) % ns for s in cand["symbol"]]
        cand = cand.sort_values("prio")
        for _, r in cand.iterrows():
            if free <= 0:
                break
            risk_usd = equity * risk_pct
            notional = risk_usd / r["stop_pct"]
            if mode == "spec":
                notional = min(notional, equity * max_lev)
            else:
                room = equity * max_lev - sum(p["notional"] for p in open_pos)
                notional = min(notional, max(room, 0.0))
            step = r["step_size"] if np.isfinite(r["step_size"]) and r["step_size"] > 0 else 1.0
            qty = np.floor((notional / r["entry"]) / step) * step
            notional = qty * r["entry"]
            mn = MIN_NOTIONAL.get(r["symbol"], DEFAULT_MIN_NOTIONAL)
            if qty <= 0 or notional < mn:
                skipped.append(dict(symbol=r["symbol"], sig_ts=bar_ts, notional=notional,
                                    need=mn, reason="NOT_EXECUTABLE"))
                continue
            open_pos.append(dict(symbol=r["symbol"], ent_ts=int(r["ent_ts"]),
                                 ex_ts=int(r["ex_ts"]), notional=notional,
                                 net=float(r["net_pess"]), lev=notional / equity,
                                 exit=r["exit_pess"]))
            free -= 1
    close_due(10**15)

    lg = pd.DataFrame(log)
    cv = pd.DataFrame(curve, columns=["ts", "equity"]).sort_values("ts")
    if len(cv):
        pk = cv["equity"].cummax()
        maxdd = float((cv["equity"] / pk - 1.0).min())
    else:
        maxdd = np.nan
    days = (tr["ex_ts"].max() - tr["sig_ts"].min()) / 86_400_000 if len(tr) else np.nan
    cagr = (equity / equity0) ** (365.0 / days) - 1.0 if days and days > 0 else np.nan
    return dict(mode=mode, risk_pct=risk_pct, equity=equity, cagr=cagr, max_dd=maxdd,
                n_trades=len(lg), killed=killed,
                mean_lev=float(lg["lev"].mean()) if len(lg) else np.nan,
                max_lev_obs=float(lg["lev"].max()) if len(lg) else np.nan,
                not_exec=len(skipped),
                win=float((lg["net"] > 0).mean()) if len(lg) else np.nan), lg, cv, pd.DataFrame(skipped)


def peak_portfolio_leverage(lg: pd.DataFrame) -> float:
    """Leverage portofolio maksimum yang benar-benar terjadi (notional simultan / ekuitas)."""
    if not len(lg):
        return np.nan
    ev = []
    for _, r in lg.iterrows():
        ev.append((r["ent_ts"], r["notional"], r["equity"]))
        ev.append((r["ex_ts"], -r["notional"], r["equity"]))
    ev.sort()
    cur, best = 0.0, 0.0
    for ts, dn, eq in ev:
        cur += dn
        if eq > 0:
            best = max(best, cur / eq)
    return best
