"""VEB backtest engine - sinyal 4H, exit lewat path scan 1H.

Perbedaan penting dari backtest asli VEB (spec §14): urutan sentuh SL vs TP di
dalam satu bar 4H TIDAK dapat ditentukan dari OHLC 4H. Di sini urutan itu
diselesaikan dengan menelusuri bar 1H di dalamnya. Kalau satu bar 1H pun masih
menyentuh SL dan TP sekaligus, trade ditandai ambigu dan dilaporkan dua kali
(pesimis = SL dulu, optimis = TP dulu).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import veb_data as V

H1_MS = V.H1_MS
H4_MS = V.H4_MS

MIN_HISTORY_BARS = 700      # spec §2.4
SL_ATR = 1.0                # spec §5.1 - FROZEN
TP_ATR = 4.0
HOLD_BARS = 6               # 24 jam
HOLD_MS = HOLD_BARS * H4_MS


def signals(ind: pd.DataFrame) -> pd.Series:
    """spec §4.1 LONG: keempat kondisi wajib benar. NaN -> tidak ada sinyal."""
    a = ind["mom180"] > 0.0
    b = ind["volratio"] > 1.0
    c = ind["atr_rank"] <= 0.50
    d = ind["h"] > ind["hh20"]
    need = ["mom180", "volratio", "atr_rank", "hh20", "atr14", "c", "h"]
    ok = ind[need].notna().all(axis=1)
    # spec §2.4: minimal 700 bar tertutup sebelum sinyal apa pun
    ok &= (np.arange(len(ind)) >= MIN_HISTORY_BARS)
    return (a & b & c & d & ok).fillna(False)


def _scan_path(hi, lo, sl, tp, n):
    """Kembalikan (kind, idx). kind: 'SL','TP','BOTH',None."""
    for k in range(n):
        h, l = hi[k], lo[k]
        if not (np.isfinite(h) and np.isfinite(l)):
            continue
        hit_sl = l <= sl
        hit_tp = h >= tp
        if hit_sl and hit_tp:
            return "BOTH", k
        if hit_sl:
            return "SL", k
        if hit_tp:
            return "TP", k
    return None, -1


def run_symbol(symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    """Semua trade VEB untuk satu symbol. Sinyal dievaluasi pada bar tertutup;
    entry di open bar 4H berikutnya."""
    h1 = V.load_1h(symbol)
    if h1.empty or len(h1) < 4 * MIN_HISTORY_BARS:
        return pd.DataFrame()
    step = V.step_size(h1["vol"])
    d4 = V.to_4h(h1)
    if len(d4) < MIN_HISTORY_BARS + 10:
        return pd.DataFrame()
    ind = V.indicators(d4)
    sig = signals(ind)

    fr = V.load_funding(symbol)
    f_ts = fr["ts"].to_numpy() if len(fr) else np.array([], dtype="int64")
    f_rt = fr["rate"].to_numpy() if len(fr) else np.array([])

    # index 1H untuk path scan
    h1i = h1.set_index("ts")
    hts = h1["ts"].to_numpy()
    hhi = h1["h"].to_numpy()
    hlo = h1["l"].to_numpy()
    hop = h1["o"].to_numpy()
    pos = {t: i for i, t in enumerate(hts)}

    ts = ind["ts"].to_numpy()
    o4 = ind["o"].to_numpy()
    h4 = ind["h"].to_numpy()
    l4 = ind["l"].to_numpy()
    atr = ind["atr14"].to_numpy()
    rows = []
    idxs = np.flatnonzero(sig.to_numpy())
    for i in idxs:
        if i + 1 >= len(ts):
            continue
        sig_ts = int(ts[i])
        ent_ts = int(ts[i + 1])
        if not (start_ms <= sig_ts <= end_ms):
            continue
        entry = o4[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        a = atr[i]
        sl = entry - SL_ATR * a
        tp = entry + TP_ATR * a
        if sl <= 0:
            continue
        stop_pct = (SL_ATR * a) / entry

        # ---- path scan 1H, 24 jam sejak entry
        j = pos.get(ent_ts)
        if j is None:
            continue
        n1 = 24
        if j + n1 >= len(hts):
            continue
        # pastikan jendela 1H benar-benar kontinu (kalau bolong, dilewati, dicatat)
        win_ts = hts[j:j + n1 + 1]
        expect = ent_ts + np.arange(n1 + 1) * H1_MS
        gaps = int((win_ts != expect).sum())
        if gaps:
            k = np.searchsorted(hts, ent_ts + (n1 + 1) * H1_MS)
            seg = np.full(n1 + 1, np.nan)
            segl = np.full(n1 + 1, np.nan)
            sego = np.full(n1 + 1, np.nan)
            sub = hts[j:k]
            off = ((sub - ent_ts) // H1_MS).astype(int)
            m = (off >= 0) & (off <= n1)
            seg[off[m]] = hhi[j:k][m]
            segl[off[m]] = hlo[j:k][m]
            sego[off[m]] = hop[j:k][m]
            hi_w, lo_w, op_w = seg, segl, sego
        else:
            hi_w = hhi[j:j + n1 + 1]
            lo_w = hlo[j:j + n1 + 1]
            op_w = hop[j:j + n1 + 1]

        kind, k1 = _scan_path(hi_w, lo_w, sl, tp, n1)
        if kind == "TP":
            px_p = px_o = tp
            ex_ts = ent_ts + (k1 + 1) * H1_MS
            exit_p = exit_o = "TP"
        elif kind == "SL":
            px_p = px_o = sl
            ex_ts = ent_ts + (k1 + 1) * H1_MS
            exit_p = exit_o = "SL"
        elif kind == "BOTH":
            px_p, px_o = sl, tp
            ex_ts = ent_ts + (k1 + 1) * H1_MS
            exit_p, exit_o = "SL", "TP"
        else:
            px_p = px_o = op_w[n1] if np.isfinite(op_w[n1]) else np.nan
            ex_ts = ent_ts + HOLD_MS
            exit_p = exit_o = "TIME"
        if not np.isfinite(px_p):
            continue

        # ---- pembanding: scan pada bar 4H saja (yang dilakukan backtest biasa)
        k4 = min(i + 1 + HOLD_BARS, len(ts))
        kind4, _ = _scan_path(h4[i + 1:k4], l4[i + 1:k4], sl, tp, k4 - (i + 1))
        if kind4 == "TP":
            px4, exit4 = tp, "TP"
        elif kind4 == "SL":
            px4, exit4 = sl, "SL"
        elif kind4 == "BOTH":
            px4, exit4 = sl, "SL"      # pesimis
        else:
            px4 = o4[i + 1 + HOLD_BARS] if i + 1 + HOLD_BARS < len(ts) else np.nan
            exit4 = "TIME"

        # ---- funding aktual yang dibayar long sampai jam keluar sebenarnya
        if len(f_ts):
            m = (f_ts > ent_ts) & (f_ts <= ex_ts)
            fsum = float(f_rt[m].sum())
            fn = int(m.sum())
            f_ok = bool(f_ts[-1] >= ex_ts)
        else:
            fsum, fn, f_ok = 0.0, 0, False

        rows.append((
            symbol, sig_ts, ent_ts, ex_ts, entry, a, stop_pct, sl, tp,
            px_p, exit_p, px_o, exit_o, px4, exit4,
            fsum, fn, f_ok, gaps, step,
            ind["atr_rank"].iat[i], ind["volratio"].iat[i], ind["mom180"].iat[i],
            ind["qvol_30d"].iat[i], (kind == "BOTH"),
        ))

    cols = ["symbol", "sig_ts", "ent_ts", "ex_ts", "entry", "atr", "stop_pct", "sl", "tp",
            "px_pess", "exit_pess", "px_opt", "exit_opt", "px_4h", "exit_4h",
            "fund_sum", "fund_n", "fund_ok", "gaps_1h", "step_size",
            "atr_rank", "volratio", "mom180", "qvol_30d", "ambiguous"]
    return pd.DataFrame(rows, columns=cols)


def enrich(tr: pd.DataFrame, cost_rt: float) -> pd.DataFrame:
    """Return kotor/bersih dalam % notional dan dalam R. Long bayar funding positif."""
    t = tr.copy()
    for tag in ("pess", "opt", "4h"):
        px = t[f"px_{tag}"]
        gross = px / t["entry"] - 1.0
        t[f"gross_{tag}"] = gross
        t[f"net_{tag}"] = gross - cost_rt - t["fund_sum"]
        t[f"R_{tag}"] = t[f"net_{tag}"] / t["stop_pct"]
        t[f"Rgross_{tag}"] = gross / t["stop_pct"]
    t["sig_date"] = pd.to_datetime(t["sig_ts"], unit="ms").dt.floor("D")
    t["hold_h"] = (t["ex_ts"] - t["ent_ts"]) / H1_MS
    return t
