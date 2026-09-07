"""Stage 1.1 — konstanta terkunci & path.

Semua nilai di blok LOCKED berasal dari keputusan Dew (brief §2.4, action plan §0.1).
Jangan diubah, jangan dioptimasi, jangan diturunkan dari risk%/stop%.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent          # "C:/Crypto data 2"
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_KLINES = RAW / "klines"
RAW_FUNDING = RAW / "fundingRate"
PANEL = DATA / "panel.parquet"                          # direktori partisi bulanan
RESULTS = ROOT / "results"
for _p in (DATA, RAW, RAW_KLINES, RAW_FUNDING, PANEL, RESULTS):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- LOCKED (brief §2.4)
CAPITAL = 100.00
MARGIN_FRAC = 0.03
LEVERAGE = 2
NOTIONAL = 6.00            # = CAPITAL * MARGIN_FRAC * LEVERAGE — FIXED

# ---------------------------------------------------------------- periode (brief §2.2)
START_DATE = "2024-08-01"
END_DATE = "2026-07-31"
WARMUP_MONTHS = 2          # untuk fitur 30-hari sebelum START_DATE
FWD_TAIL_DAYS = 5          # hari kalender setelah END_DATE untuk label fwd_72h

# ---------------------------------------------------------------- universe (brief §2.3)
QUOTE = "USDT"
BENCHMARK_SYMBOLS = ("BTCUSDT", "ETHUSDT")   # keputusan Dew: benchmark saja, di luar pooled ablation
MIN_HISTORY_DAYS = 30

# ---------------------------------------------------------------- eksekutabilitas (brief §2.5)
# stepSize DITURUNKAN dari eksponen desimal volume klines per (symbol, bulan) — nilai
# point-in-time, tetap ada untuk symbol delisted. TETAP dipakai sebagai sumber utama.
#
# VERIFIKASI 2026-09-07 (audit infrastruktur): fapi.binance.com ternyata reachable dari
# mesin ini dan exchangeInfo berhasil ditarik (658 perp USDT). Hasil konfrontasi:
#   * stepSize turunan == LOT_SIZE asli pada 54/54 symbol yang diperiksa  -> metode VALID
#   * minQty == stepSize pada 657/658 symbol                              -> asumsi VALID
#     satu-satunya pengecualian: ALLUSDT (stepSize 1, minQty 10)
#   * MIN_NOTIONAL: 652 symbol = 5, lima symbol = 20, BTCUSDT = 50
# Override di bawah kini memakai nilai ASLI, bukan tebakan. Sebelumnya BTCUSDT ditulis
# 100 (salah) dan BCH/LTC/ETC/LINK tidak terdaftar sama sekali, sehingga keempatnya
# ditandai executable di $6 padahal MIN_NOTIONAL-nya 20.
# PERINGATAN: ini snapshot 2026-09-07, bukan point-in-time. stepSize sengaja TIDAK
# diambil dari sini justru karena alasan itu.
ASSUME_MINQTY_EQ_STEPSIZE = True               # terverifikasi 657/658; ALLUSDT pengecualian
DEFAULT_MIN_NOTIONAL = 5.0                     # terverifikasi: 652/658 symbol
MIN_NOTIONAL_OVERRIDE = {                      # exchangeInfo 2026-09-07, nilai asli
    "BTCUSDT": 50.0,
    "ETHUSDT": 20.0,
    "BCHUSDT": 20.0,
    "LTCUSDT": 20.0,
    "ETCUSDT": 20.0,
    "LINKUSDT": 20.0,
}
# minQty yang TIDAK sama dengan stepSize (exchangeInfo 2026-09-07).
# Kosongkan dict ini untuk kembali ke asumsi murni minQty == stepSize.
MIN_QTY_OVERRIDE = {"ALLUSDT": 10.0}
MIN_NOTIONAL_SENSITIVITY = (5.0, 10.0, 20.0)
QUANT_TOL = 0.10                              # brief §2.5 (c)
QUANT_TOL_SENSITIVITY = (0.05, 0.10, 0.20)

# ---------------------------------------------------------------- biaya (brief §5.1)
FEE_ROUNDTRIP = 0.0010                        # taker 0.05% x 2
SLIPPAGE_ROUNDTRIP = 0.0010                   # ASUMSI belum terverifikasi (konfirmasi Dew)
SLIPPAGE_SENSITIVITY = (0.0005, 0.0010, 0.0020)
COST_BASE = FEE_ROUNDTRIP + SLIPPAGE_ROUNDTRIP

# ---------------------------------------------------------------- label & window
HORIZONS_H = (24, 48, 72)
PRIMARY_H = 48

# ---------------------------------------------------------------- kriteria keputusan (brief §6)
KEEP_MIN_SPREAD_NET = 0.005
KEEP_MIN_TSTAT = 2.5
KEEP_MIN_NDAYS = 200
UNRELIABLE_NDAYS = 100

SEED = 20260823
BOOTSTRAP_REPS = 2000

BASE_URL = "https://data.binance.vision/data/futures/um"
S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
