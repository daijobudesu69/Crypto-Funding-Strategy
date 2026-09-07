"""VEB backtest - loader 1H dari arsip ZIP + resample ke grid 4H.

Tidak memakai parquet: pyarrow._parquet diblokir Application Control policy di
mesin ini (2026-08-25). Semua I/O lewat zipfile + CSV.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# ROOT diturunkan dari lokasi file ini, bukan path absolut. Sebelum audit
# 2026-09-07 baris ini berbunyi Path(r"C:/Crypto data 2") - kode ini mati
# begitu repo di-clone orang lain atau foldernya dipindah/di-rename.
ROOT = Path(__file__).resolve().parent.parent
RAW_KLINES = ROOT / "data" / "raw" / "klines"
RAW_FUNDING = ROOT / "data" / "raw" / "fundingRate"

H1_MS = 3_600_000
H4_MS = 4 * H1_MS

KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _read_zip_csv(path: Path, names: list[str]) -> pd.DataFrame | None:
    try:
        with zipfile.ZipFile(path) as z:
            inner = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not inner:
                return None
            raw = z.read(inner[0])
    except (zipfile.BadZipFile, OSError):
        return None
    if not raw:
        return None
    head = raw[:200].split(b"\n", 1)[0].decode("utf-8", "replace")
    skip = 1 if names[0] in head else 0
    df = pd.read_csv(io.BytesIO(raw), header=None, names=names, skiprows=skip)
    return df


def list_symbols() -> list[str]:
    return sorted(p.name for p in RAW_KLINES.iterdir() if p.is_dir())


def load_1h(symbol: str) -> pd.DataFrame:
    """1H klines gabungan seluruh arsip symbol. Kolom: ts(ms,int64), o,h,l,c,vol,qvol."""
    d = RAW_KLINES / symbol
    if not d.is_dir():
        return pd.DataFrame()
    parts = []
    for f in sorted(d.glob(f"{symbol}-1h-*.zip")):
        df = _read_zip_csv(f, KCOLS)
        if df is not None and len(df):
            parts.append(df[["open_time", "open", "high", "low", "close", "volume", "quote_volume"]])
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    # arsip lama kadang pakai open_time dalam mikrosekon
    if df["open_time"].max() > 10**14:
        df["open_time"] = df["open_time"] // 1000
    df = df.rename(columns={"open_time": "ts", "open": "o", "high": "h",
                            "low": "l", "close": "c", "volume": "vol",
                            "quote_volume": "qvol"})
    for col in ("o", "h", "l", "c", "vol", "qvol"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["ts"] = df["ts"].astype("int64")
    df = df.drop_duplicates("ts", keep="last").sort_values("ts").reset_index(drop=True)
    return df


def load_funding(symbol: str) -> pd.DataFrame:
    d = RAW_FUNDING / symbol
    if not d.is_dir():
        return pd.DataFrame(columns=["ts", "rate"])
    parts = []
    for f in sorted(d.glob(f"{symbol}-fundingRate-*.zip")):
        df = _read_zip_csv(f, ["calc_time", "funding_interval_hours", "last_funding_rate"])
        if df is not None and len(df):
            parts.append(df[["calc_time", "last_funding_rate"]])
    if not parts:
        return pd.DataFrame(columns=["ts", "rate"])
    df = pd.concat(parts, ignore_index=True)
    if df["calc_time"].max() > 10**14:
        df["calc_time"] = df["calc_time"] // 1000
    df = df.rename(columns={"calc_time": "ts", "last_funding_rate": "rate"})
    df["ts"] = df["ts"].astype("int64")
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    return df.dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def step_size(vol: pd.Series) -> float:
    """stepSize diturunkan dari eksponen desimal terkecil kolom volume.

    Metode yang sama dengan Stage 1.1 (tervalidasi 5/5). Volume bar = jumlah
    quantity trade, jadi selalu kelipatan stepSize.
    """
    v = vol[np.isfinite(vol) & (vol > 0)]
    if not len(v):
        return 1.0
    s = v.astype(str).str.rstrip("0")
    dec = s.str.split(".").str[1].fillna("").str.len()
    d = int(dec.max())
    return 10.0 ** (-min(d, 8))


def to_4h(h1: pd.DataFrame) -> pd.DataFrame:
    """Resample 1H -> grid 4H penuh (00,04,08,12,16,20 UTC).

    Bar 4H hanya valid bila keempat bar 1H-nya ada DAN volumenya tidak semua nol
    (klines nol-volume = perp yang sudah mati; jebakan arsip Stage 1.1 §2).
    Bar tidak valid diisi NaN, bukan dibuang -- supaya jarak 180/500 bar tetap
    berarti 30/83 hari kalender, bukan "180 bar terakhir yang ada".
    """
    if h1.empty:
        return pd.DataFrame()
    h1 = h1[np.isfinite(h1["c"]) & (h1["c"] > 0)]
    if h1.empty:
        return pd.DataFrame()
    g = h1["ts"] // H4_MS
    agg = h1.groupby(g).agg(
        ts=("ts", "min"), o=("o", "first"), h=("h", "max"), l=("l", "min"),
        c=("c", "last"), vol=("vol", "sum"), qvol=("qvol", "sum"), n=("c", "size"),
    )
    agg["gts"] = agg.index * H4_MS
    full = pd.DataFrame({"gts": np.arange(agg["gts"].min(), agg["gts"].max() + H4_MS, H4_MS)})
    out = full.merge(agg.reset_index(drop=True), on="gts", how="left")
    bad = (out["n"] != 4) | ~np.isfinite(out["c"]) | (out["vol"].fillna(0) <= 0) \
        | (out["h"] < out["l"]) | (out["c"] <= 0)
    out.loc[bad, ["o", "h", "l", "c", "vol", "qvol"]] = np.nan
    out["ts"] = out["gts"]
    return out[["ts", "o", "h", "l", "c", "vol", "qvol"]].reset_index(drop=True)


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Definisi persis VEB spec §3. Tidak ada indikator tambahan."""
    d = df.copy()
    d["mom180"] = d["c"] / d["c"].shift(180) - 1.0

    d["ret1"] = d["c"] / d["c"].shift(1) - 1.0
    d["rv30"] = d["ret1"].rolling(30).std(ddof=1)
    d["rv90"] = d["ret1"].rolling(90).std(ddof=1)
    d["volratio"] = d["rv30"] / d["rv90"]

    tr = pd.concat([
        d["h"] - d["l"],
        (d["h"] - d["c"].shift(1)).abs(),
        (d["l"] - d["c"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    d["atr14"] = tr.rolling(14).mean()          # rolling MEAN, bukan Wilder
    d["atr_pct"] = d["atr14"] / d["c"]
    d["atr_rank"] = d["atr_pct"].rolling(500).rank(pct=True)

    d["hh20"] = d["h"].rolling(20).max().shift(1)
    d["ll60"] = d["l"].rolling(60).min().shift(1)

    d["qvol_30d"] = d["qvol"].rolling(180).mean() * 6.0   # 180 bar 4H = 30 hari; x6 -> per hari
    return d
