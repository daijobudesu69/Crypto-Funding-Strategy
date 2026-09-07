# Peta Data Backtest VEB — semua file & lokasinya

Untuk backtest ulang sendiri. Root proyek: **`C:\Crypto data 2`** (ada spasi — selalu kutip pathnya).

---

## 1. DATA SUMBER (input) — tidak saya ubah isinya

Satu-satunya sumber harga & funding. Semuanya ZIP berisi CSV, dari `data.binance.vision`.

| Lokasi | Isi | Jumlah | Ukuran |
|---|---|---:|---:|
| `data\raw\klines\<SYMBOL>\<SYMBOL>-1h-YYYY-MM.zip` | Klines 1H perp Binance USDⓈ-M, arsip **bulanan** | 810 folder simbol | 457 MB total |
| `data\raw\klines\<SYMBOL>\<SYMBOL>-1h-YYYY-MM-DD.zip` | Klines 1H, arsip **harian** (untuk tanggal terbaru yang bulanannya belum terbit) | — | (di dalam 457 MB) |
| `data\raw\fundingRate\<SYMBOL>\<SYMBOL>-fundingRate-YYYY-MM.zip` | Funding rate aktual, bulanan | 820 folder simbol | (di dalam 457 MB) |
| `data\raw\manifest.json` | Manifest unduhan | 1 | — |

Total **29.271 file ZIP**.

### Cakupan waktu

| | Mulai | Berakhir |
|---|---|---|
| Klines 1H (bulanan) | 2024-06-01 | 2026-07-31 |
| Klines 1H (harian) | 2026-08-01 | **2026-08-24** (hanya BTCUSDT) |
| Funding rate | 2024-06-01 | **2026-07-31** (arsip bulanan; Agustus belum terbit) |

Karena funding berhenti 2026-07-31, **periode sinyal backtest ditutup di 2026-07-30 20:00 UTC**
supaya setiap trade punya data funding penuh sampai jam keluarnya.

### Skema CSV di dalam ZIP

**Klines** (`<SYMBOL>-1h-*.csv`) — 12 kolom, ada baris header:
```
open_time, open, high, low, close, volume, close_time,
quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore
```
`open_time` / `close_time` = epoch **milidetik** UTC. Yang saya pakai: `open_time, open,
high, low, close, volume, quote_volume`. Kolom `volume` juga dipakai untuk menurunkan
`stepSize` (eksponen desimal terkecil).

**Funding** (`<SYMBOL>-fundingRate-*.csv`) — 3 kolom, ada baris header:
```
calc_time, funding_interval_hours, last_funding_rate
```
`calc_time` = epoch milidetik, terbit tiap 8 jam (00:00, 08:00, 16:00 UTC).
`last_funding_rate` desimal, mis. `0.00005532` = 0,0055%.

### Yang SAYA TAMBAHKAN ke data sumber sesi ini

19 file, semuanya unduhan baru dari `data.binance.vision`, tidak menimpa apa pun:

```
data\raw\klines\BTCUSDT\BTCUSDT-1h-2026-08-06.zip  ..  BTCUSDT-1h-2026-08-24.zip
```

Tujuannya satu: bar acuan unit test spec §12.1 adalah **BTCUSDT 4H 2026-08-23 16:00 UTC**,
yang berada di luar arsip yang sudah ada (berhenti 2026-08-05). Tanpa 19 file ini,
tes §12.1 tidak bisa dijalankan. **File-file ini tidak dipakai di backtest** — periode
sinyal berhenti 2026-07-30.

URL polanya:
```
https://data.binance.vision/data/futures/um/daily/klines/{SYM}/1h/{SYM}-1h-{YYYY-MM-DD}.zip
https://data.binance.vision/data/futures/um/monthly/klines/{SYM}/1h/{SYM}-1h-{YYYY-MM}.zip
https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYM}/{SYM}-fundingRate-{YYYY-MM}.zip
```

---

## 2. KODE YANG SAYA TULIS

Semua di `src\`. Tidak ada file lama yang ditimpa.

| File | Baris | Fungsi |
|---|---:|---|
| `src\veb_data.py` | 159 | Baca ZIP → 1H → grid 4H; indikator spec §3; `step_size()` |
| `src\veb_engine.py` | 202 | Sinyal spec §4.1; exit lewat path scan 1H; funding aktual |
| `src\veb_run.py` | 40 | Runner: `spec8` atau `full` → tulis trades CSV |
| `src\veb_stats.py` | 91 | Ringkasan cluster SE, walk-forward, kurva biaya |
| `src\veb_portfolio.py` | 114 | Simulasi 3 slot, rotasi mingguan, 2 varian sizing |

Dipakai dari kode lama (tidak diubah): `src\stats.py` — `cluster_mean`,
`cluster_bootstrap_ci`, `cluster_ols`.

### Konstanta kunci (kalau mau diubah, di sini tempatnya)

| Nilai | Lokasi |
|---|---|
| `MIN_HISTORY_BARS = 700` | `veb_engine.py` |
| `SL_ATR = 1.0`, `TP_ATR = 4.0`, `HOLD_BARS = 6` | `veb_engine.py` |
| `COST = 0.0020` (biaya pulang-pergi) | `veb_stats.py` |
| `MIN_NOTIONAL = {BTC:100, ETH:20}`, default 5 | `veb_portfolio.py` |
| `risk_pct`, `max_lev`, `slots`, `kill_dd` | argumen `simulate()` |
| Periode `START` / `END` | `veb_run.py` |

---

## 3. HASIL YANG SAYA TULIS

Semua di `results\veb\`. Folder ini **baru**, sebelumnya tidak ada.

| File | Baris data | Ukuran | Isi |
|---|---:|---:|---|
| `trades_spec8.csv` | 348 | 96 KB | Trade di 8 simbol yang spec setujui. **25 kolom** |
| `trades_full.csv` | 11.312 | 3,2 MB | Trade di seluruh panel, 589 simbol. **25 kolom** |
| `trades_full_elig.csv` | 11.312 | 3,3 MB | = `trades_full` + kolom `fund_abs90`. **26 kolom** |
| `trades_full_clean.csv` | 11.271 | 6,2 MB | = `elig` minus 41 trade perp emas/stablecoin, + semua kolom return terhitung. **40 kolom** |
| `HASIL_BACKTEST_VEB.md` | — | 13 KB | Laporan lengkap |
| `DATA_MAP.md` | — | — | File ini |
| `veb_hasil.png` | — | 173 KB | Kurva ekuitas + avgR kumulatif |

### 3.1 Kolom `trades_*.csv` (25 kolom inti)

| # | Kolom | Arti |
|---:|---|---|
| 1 | `symbol` | Simbol perp |
| 2 | `sig_ts` | Epoch ms, **bar 4H tertutup** yang memicu sinyal |
| 3 | `ent_ts` | Epoch ms, open bar 4H berikutnya = waktu entry (`sig_ts` + 4 jam) |
| 4 | `ex_ts` | Epoch ms, waktu keluar sebenarnya (hasil path scan 1H) |
| 5 | `entry` | Harga entry = open bar 4H di `ent_ts` |
| 6 | `atr` | `atr14` di bar sinyal, **dikunci** seumur trade (spec §5) |
| 7 | `stop_pct` | `(1,0 × atr) / entry` — jarak stop dalam persen |
| 8 | `sl` | Harga stop loss = `entry − 1,0×atr` |
| 9 | `tp` | Harga target = `entry + 4,0×atr` |
| 10 | `px_pess` | Harga keluar, path scan 1H, **tie-break pesimis** (SL dulu) ← **yang saya pakai** |
| 11 | `exit_pess` | Cara keluar: `SL` / `TP` / `TIME` |
| 12 | `px_opt` | Harga keluar, tie-break optimis (TP dulu) |
| 13 | `exit_opt` | Cara keluar versi optimis |
| 14 | `px_4h` | Harga keluar kalau **hanya** melihat bar 4H (metode backtest biasa) |
| 15 | `exit_4h` | Cara keluar versi 4H-saja |
| 16 | `fund_sum` | **Jumlah funding rate** dalam (`ent_ts`, `ex_ts`]. Positif = long **bayar** |
| 17 | `fund_n` | Berapa kali funding kena (0, 1, 2, atau 3) |
| 18 | `fund_ok` | `True` kalau arsip funding memang mencakup sampai `ex_ts` |
| 19 | `gaps_1h` | Jumlah bar 1H yang hilang di jendela 24 jam. 0 = mulus |
| 20 | `step_size` | Kelipatan kuantitas, diturunkan dari desimal kolom volume |
| 21 | `atr_rank` | Nilai filter C di bar sinyal (≤ 0,50) |
| 22 | `volratio` | Nilai filter B di bar sinyal (> 1,0) |
| 23 | `mom180` | Nilai filter A di bar sinyal (> 0) |
| 24 | `qvol_30d` | Rata-rata quote volume 30 hari, **per hari** (untuk kriteria §1.3 no.3) |
| 25 | `ambiguous` | `True` kalau SL dan TP tersentuh di **bar 1H yang sama** (7 dari 11.312) |

### 3.2 Kolom tambahan

Hanya di `trades_full_elig.csv` dan `trades_full_clean.csv`:

| Kolom | Arti |
|---|---|
| `fund_abs90` | Rata-rata `\|funding\|` 90 hari terakhir per 8 jam, *point-in-time* (kriteria §1.3 no.4: harus ≤ 0,0005) |

Hanya di `trades_full_clean.csv` — hasil `veb_engine.enrich(tr, 0.0020)`:

| Kolom | Rumus |
|---|---|
| `gross_pess` | `px_pess / entry − 1` — gerak harga saja |
| `net_pess` | `gross_pess − 0,0020 − fund_sum` — setelah biaya & funding |
| `R_pess` | `net_pess / stop_pct` — **kolom utama laporan** |
| `Rgross_pess` | `gross_pess / stop_pct` |
| `*_opt`, `*_4h` | Sama, untuk varian tie-break optimis dan scan 4H-saja |
| `sig_date` | `sig_ts` dibulatkan ke hari — **kunci clustering standard error** |
| `hold_h` | `(ex_ts − ent_ts) / 3.600.000` — lama tahan dalam jam |

---

## 4. Cara menjalankan ulang

```bash
cd "C:\Crypto data 2"
set PYTHONIOENCODING=utf-8

python src\veb_run.py spec8    # 3 detik   -> results\veb\trades_spec8.csv
python src\veb_run.py full     # 134 detik -> results\veb\trades_full.csv
```

`veb_run.py` otomatis menambahkan `src\` ke path lewat lokasinya sendiri; kalau
dipanggil dari skrip lain, awali dengan `sys.path.insert(0, 'src')`.

Untuk ringkasan statistiknya:

```python
import sys; sys.path.insert(0, 'src')
import veb_stats as S
t = S.load('spec8')          # atau 'full'
print(S.summarize(t, 'spec8'))
print(S.exit_mix(t))
print(S.per_symbol(t))
print(S.walkforward(t))
```

Untuk simulasi portofolio:

```python
import veb_portfolio as P
ringkasan, log, kurva, ditolak = P.simulate(t, mode='spec', risk_pct=0.02)
# mode='spec' = cap leverage per posisi (seperti spec, ada bug)
# mode='fix'  = cap leverage total portofolio (koreksi)
```

---

## 5. ⚠️ Data lama yang TIDAK BISA DIBACA di mesin ini

Ini yang paling penting kalau Anda mau kerja sendiri. Semua direktori Parquet dari
Stage 1.1 **tidak terbaca** karena `pyarrow._parquet` diblokir Windows Application
Control policy (terverifikasi 2026-08-25, dari Bash maupun PowerShell):

| Direktori | Ukuran | Status |
|---|---:|---|
| `data\panel.parquet` | 88 MB | ❌ tidak terbaca |
| `data\interim` | 92 MB | ❌ tidak terbaca |
| `data\hours` | 91 MB | ❌ tidak terbaca |
| `data\horizons` | 95 MB | ❌ tidak terbaca |
| `data\ext` | 37 MB | ❌ tidak terbaca |
| `data\smc` | 18 MB | ❌ tidak terbaca |
| `data\orderflow` | 24 MB | ❌ tidak terbaca |
| `data\skema2_pathscan.parquet` | — | ❌ tidak terbaca |

Pesan errornya: `DLL load failed while importing _parquet: An Application Control
policy has blocked this file.` `fastparquet`, `duckdb`, dan `polars` tidak terpasang.

**Karena itu seluruh pipeline VEB dibangun untuk membaca langsung dari ZIP.**
Kecepatannya ternyata tidak jadi masalah: ~0,2 detik per simbol untuk 2 tahun
klines 1H, atau 134 detik untuk 810 simbol.

Kalau Anda mau memakai panel Parquet lama, tiga pilihan:
1. `pip install fastparquet` — belum diuji, mungkin ikut diblokir (butuh `cramjam`)
2. `pip install duckdb` lalu `duckdb.read_parquet(...)` — belum diuji
3. Abaikan saja dan pakai ZIP seperti pipeline VEB — **paling aman**

Yang masih terbaca normal (CSV, bukan Parquet): semua di `results\`,
`data\daily_market.csv`, `data\universe_log.csv`, `oi_logs\`.

---

## 6. Dokumen rujukan di proyek ini

| File | Isi |
|---|---|
| `HYPOTHESIS_REGISTER.md` | H1 (funding carry) + **H2 = VEB, GAGAL** ← saya tambahkan |
| `SESSION_2026-08-23.md` | Riset Sesi A: 22 keluarga uji, batasan akses jaringan |
| `STAGE_1_1_FINDINGS.md` | Temuan Stage 1.1 |
| `CLAUDE-CODE-HANDOFF.md` | Handoff & parameter terkunci Stage 1.1 |
| `results\veb\HASIL_BACKTEST_VEB.md` | Laporan hasil VEB |
| `C:\Users\sedan\Downloads\VEB_STRATEGY_SPEC.md` | Spec yang diuji (v1.1) |
