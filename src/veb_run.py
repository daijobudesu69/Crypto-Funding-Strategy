"""Jalankan VEB di sekumpulan symbol, tulis trades ke CSV."""
from __future__ import annotations
import sys, time
from pathlib import Path
import pandas as pd
import veb_engine as E
import veb_data as V

# ROOT diturunkan dari lokasi file ini, bukan path absolut. Sebelum audit
# 2026-09-07 baris ini berbunyi Path(r"C:/Crypto data 2") - kode ini mati
# begitu repo di-clone orang lain atau foldernya dipindah/di-rename.
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "veb"
OUT.mkdir(parents=True, exist_ok=True)

SPEC8 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "HBARUSDT", "SUIUSDT", "SUSDT"]
START = int(pd.Timestamp("2024-01-01").value // 10**6)
END = int(pd.Timestamp("2026-07-30 20:00").value // 10**6)


def main(which: str):
    syms = SPEC8 if which == "spec8" else V.list_symbols()
    t0 = time.time()
    parts, bad = [], []
    for n, s in enumerate(syms, 1):
        try:
            tr = E.run_symbol(s, START, END)
        except Exception as exc:
            bad.append((s, type(exc).__name__, str(exc)[:120])); continue
        if len(tr):
            parts.append(tr)
        if n % 50 == 0:
            print(f"  {n}/{len(syms)}  {time.time()-t0:.0f}s  trades={sum(len(p) for p in parts)}", flush=True)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    df.to_csv(OUT / f"trades_{which}.csv", index=False)
    print(f"{which}: {len(df)} trades dari {df['symbol'].nunique() if len(df) else 0} symbol, "
          f"{time.time()-t0:.0f}s, error {len(bad)}")
    if bad:
        pd.DataFrame(bad, columns=["symbol", "err", "msg"]).to_csv(OUT / f"errors_{which}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "spec8")
