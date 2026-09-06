# Crypto-Trade-2 — Riset kuantitatif perp USDT Binance

> **Status: RISET. Belum ada strategi yang tervalidasi. Jangan pakai uang sungguhan.**
> Repo ini bukan sistem trading yang jalan. Isinya laboratorium backtest, catatan
> hipotesis yang dikunci sebelum diuji, dan satu logger data yang jalan otomatis
> tiap hari. Dari 24 keluarga uji yang sudah dijalankan, **nol** lolos kriteria
> KEEP dan **satu** (H1) masih menunggu uji di data yang belum pernah dilihat.

Repo ini **terpisah** dari [`daijobudesu69/Crypto-Trade`](https://github.com/daijobudesu69/Crypto-Trade),
yang berisi sistem sinyal harian v1.4 (spot, BTC/ETH/SOL, Telegram + Google Sheets).
Di sini tidak ada sinyal yang dikirim ke siapa pun, tidak ada notifikasi, dan tidak
ada kredensial apa pun.

---

## 1. Ringkasan dalam satu tabel

| | |
|---|---|
| Instrumen | Perp USDT Binance USDⓈ-M (futures) |
| Universe | 752 koin, termasuk yang sudah delisted |
| Periode panel | 2024-08-01 → 2026-07-31 (730 hari) |
| Observasi | 346.870 (tanggal × koin) |
| Modal acuan | $100, margin 3%, leverage 2× → notional **$6,00 fixed** |
| Keluarga uji dijalankan | **24** (R0–R21 + H1 + H2) + walk-forward + sensitivitas |
| Faktor lolos kriteria KEEP | **0** |
| Kandidat bertahan | **1** — H1 (funding carry), belum tervalidasi |
| Strategi yang sudah ditutup | Skema 2 (H1 + stop), H2/VEB |
| Uji berikutnya | ~1 November 2026, di data Ags–Okt 2026 |

---

## 2. Strategi trading

### 2.1 Kerangka awal — dan bagaimana data menolaknya

Titik berangkatnya `docs/dew-futures-screener-strategy.md`: screener tiga lapis
(likuiditas → funding cross-sectional → trigger BOS/CHoCH + EMA9), ditambah
matriks OI 4 kuadran dan Volume Profile sebagai pengganti liquidation heatmap.

Setelah diuji di 346.870 observasi, **seluruh lapisan arah harga ditolak**:

| Klaim dokumen awal | Hasil uji |
|---|---|
| "Sinyal funding ada di ekor, p90+ = kandidat short" | **Arah terbalik.** Funding tinggi diikuti return lebih tinggi; short D10 = −0,594% (t=−4,59) |
| "Momentum di koin likuid, reversal di koin tipis" | **Ditolak.** Tidak ada gradien likuiditas (L1 t=−0,46, L2 t=−2,50, L3 t=−0,38) |
| "BOS/CHoCH penentu arah utama" | **Ditolak.** Semua filter "arah bullish" memperburuk; R13 signifikan ke arah **salah** (t=−2,16) |
| "VPVR + swing pengganti liquidation heatmap" | **Ditolak.** Semua bucket nol |
| "Taker ratio tidak bisa dibacktest" | **Salah** — `taker_buy_quote_volume` ada di tiap baris klines, arsip 2 tahun penuh |

### 2.2 H1 — funding carry (satu-satunya yang bertahan)

Definisi dikunci di [`HYPOTHESIS_REGISTER.md`](HYPOTHESIS_REGISTER.md) pada
2026-08-23 dan **tidak boleh diubah** sebelum uji November.

```
Tiap hari 00:00 UTC, untuk tiap perp USDT dengan >=30 hari riwayat klines:

  funding_24h_sum = jumlah funding rate dalam (d-1 00:00, d 00:00]
  funding_ts_z30  = z-score funding_24h_sum vs 30 hari riwayat symbol sendiri
  zrank           = peringkat persentil funding_ts_z30 antar symbol eligible

  SINYAL LONG bila:  funding_24h_sum <= 0  DAN  zrank <= 0.20

  Entry  : open bar 1H 00:00 UTC
  Exit   : open bar 1H 48 jam kemudian - TANPA stop, TANPA target
  Sizing : notional $6,00 fixed (margin 3% x ekuitas x leverage 2x)
  Biaya  : maker 0,02% x 2 + funding aktual yang dibayar selama hold
  Filter : hanya symbol dengan executable_100usd == True
```

**Hasil dan uji ketahanan:**

| Uji | Hasil | Lolos |
|---|---|:-:|
| Net per trade | +0,536% CI [+0,079%, +0,993%], t=+2,30, n=30.796 | ✅ |
| Spread vs sisanya | +0,741% CI [+0,461%, +1,021%], t=+5,20 | ✅ |
| Market-neutral | +0,266%, t=+3,60 | ✅ |
| Bonferroni (264 uji) | p < 0,001 | ✅ |
| Walk-forward 9 fold | OOS positif **8/9**, degradasi 18,0%, OOS gabungan +0,634% (t=2,13) | ✅ |
| Regime BTC bull / bear | +0,666% (t=2,92) / +0,852% (t=4,80) | ✅ |
| 6 jam entry berbeda | positif **6/6**, +0,350% s/d +0,474% | ✅ |
| **Fold terakhir (Jun–Jul 2026)** | **+0,053% (t=0,08)** | ⚠️ |

**Ini carry, bukan capital gain.** Dekomposisi net +0,536%:

| Komponen | Kontribusi | t | % dari net |
|---|---:|---:|---:|
| Gerak harga | +0,197% | **+0,85** | 36,8% |
| **Funding diterima** | **+0,379%** | **+32,08** | **70,6%** |
| Fee | −0,040% | — | −7,5% |

Trade yang harganya naik hanya **46,9%**; median gerak harga **−0,4052%**.
Yang punya t=32 adalah funding-nya. Ini memungut carry sambil menanggung risiko
harga telanjang — bukan strategi arah.

**Kenapa tidak bisa di-hedge:** untuk menerima funding negatif harus long perp,
jadi hedge-nya wajib instrumen bebas funding. Short perp yang sama saling batal;
short spot butuh pinjam koin dan **47% symbol H1 tidak punya pasar spot**; hanya
**1 dari 681** symbol punya kontrak delivery. Dan sinyal terkuat justru ada di
koin yang tidak bisa di-hedge (tanpa spot: +1,033%, t=+2,99 vs punya spot:
+0,387%, t=+1,67) — konsisten secara ekonomi: funding negatif dalam justru karena
tidak ada instrumen untuk mengarbitrasenya.

**Status:** BELUM TERVALIDASI. Efeknya meluruh dari +0,901% (tahun 1) ke +0,053%
(2 bulan terakhir). Dua penjelasan sama masuk akalnya — edge nyata yang sudah
diarbitrase habis, atau tidak pernah ada. Data yang ada tidak bisa membedakannya.

### 2.3 Skema 2 (H1 + stop loss) — DIBATALKAN

Semua tingkat stop menghasilkan net negatif. Mekanismenya: stop memotong hold,
hold pendek memungut funding jauh lebih sedikit, sementara komponen harganya
negatif di semua tingkat.

| SL | TP | Median jam keluar | Harga | Funding | Net | t |
|---:|---:|---:|---:|---:|---:|---:|
| 1% | 2% | 2 | −0,125% | +0,020% | **−0,145%** | −4,77 |
| 3% | 6% | 13 | −0,096% | +0,048% | −0,088% | −0,95 |
| 5% | 10% | 30 | −0,181% | +0,093% | −0,129% | −0,91 |
| tanpa | — | 48 | +0,197% | **+0,379%** | **+0,536%** | +2,30 |

Angka portofolio Skema 2 yang pernah dilaporkan ($120,84 lalu $106,57) **keduanya
salah** — penyebabnya funding dikreditkan 48 jam penuh ke trade yang keluar di
jam ke-2.

### 2.4 H2 — VEB (Volatility-Expansion Breakout) — GAGAL, DITUTUP

Didaftarkan 2026-08-25 dari spec eksternal yang parameternya dibekukan **sebelum**
menyentuh panel ini (karena itu bebas dari penalti Bonferroni sesi sebelumnya).

```
Tiap bar 4H tertutup, perp USDT dengan >=700 bar riwayat:
  mom180 > 0  DAN  volratio > 1  DAN  atr_rank <= 0,50  DAN  high > hh20
  Entry: open bar 4H berikutnya | SL: -1,0 ATR | TP: +4,0 ATR | Time exit: 6 bar
```

| Universe | n | avgR bersih | t | Vonis |
|---|---:|---:|---:|---|
| 8 simbol yang spec setujui | 348 | +0,064 | +0,32 | nol |
| Universe layak spec | 2.057 | −0,027 | −0,17 | nol |
| **Seluruh panel** | **11.271** | **−0,106** | **−0,85** | **nol / minus** |

Prediksi spec avgR +0,410 hanya tereproduksi **di BTC saja** (+0,373); di 586 koin
lain jadi −0,012. Win rate 30,6% (klaim 43%), R:R efektif 1,9:1 (klaim 4:1), DD
30–32% (klaim 15–20%). **Jangan di-tuning** — uji bersihnya sudah terpakai;
menyetel parameter sekarang mengubah validasi jadi pencarian.

### 2.5 Portofolio (H1, $100, 3 slot)

| Skema | Ekuitas 2 thn | CAGR | Max DD | Rentang 30 seed |
|---|---:|---:|---:|---|
| Beli acak | $85,63 | −7,49% | −27,9% | $65–$158 |
| **H1 tanpa stop** | **$105,87** | **+2,90%** | −23,2% | $71–$176 |

Modal bekerja hanya **9%** (3 slot × 3% margin); 91% menganggur. Sinyal tersedia
~42/hari, dipakai 3 — **aturan pemilihan di antara 42 kandidat belum ditentukan**
dan akan menambah derajat bebas baru.

### 2.6 Gate eksekutabilitas $6 — LOLOS

| Ukuran | Nilai |
|---|---:|
| Executable (toleransi 10%) | **323.243 / 346.870 (93,2%)** |
| Symbol selalu executable | 553 / 752 (73,5%) |
| Symbol tidak pernah | 24 (3,2%) |
| Syarat paling mengikat | error kuantisasi (5,42%), bukan MIN_NOTIONAL |
| Aturan praktis | satu step harus ≤ **$0,60** |

Bias likuiditasnya **berlawanan dugaan**: `exec_rate` 88,1% di tercile paling
likuid vs 96,4% di paling tipis. Yang tersaring keluar justru koin likuid berharga
tinggi (AVAX 0,1% hari executable, SOL 33,8%, BNB 21,4%).

### 2.7 Aturan disiplin yang berlaku di repo ini

1. Setiap ambang yang diambil dari grid adalah derajat bebas. Pertahankan yang
   longgar kecuali walk-forward membuktikan yang ketat lebih baik di luar sampel.
2. Setiap aturan baru hasil pencarian **wajib didaftarkan** di
   `HYPOTHESIS_REGISTER.md` sebelum diuji pada data baru.
3. Hasil yang berlawanan dengan hasil sebelumnya = **ada bug** sampai terbukti
   sebaliknya. (Tiga kali terjadi, tiga-tiganya memang bug.)
4. Path scan mengalahkan MAE/MFE untuk apa pun yang bergantung urutan sentuhan.
   MAE/MFE hanya untuk skrining cepat, verifikasi dengan path scan.
5. Funding harus dihitung **sampai jam keluar sebenarnya**, bukan sampai batas
   horizon — kalau tidak, semua strategi ber-stop akan overstated.
6. Menambah faktor ke-25 dari data yang sama **menurunkan** kredibilitas apa pun
   yang ditemukan. Bonferroni kumulatif sudah menuntut |t| > 3,6.

---

## 3. Hasil 24 keluarga uji

Semua: LONG, horizon `fwd_48h`, universe penuh, standard error cluster per tanggal.

| Run | Faktor | Spread net | t | Vonis |
|---|---|---:|---:|:-:|
| R0 | Baseline (beli semua) | −0,330% | −1,67 | acuan |
| R1 | `funding_xs_pct` | +0,291% | +2,18 | KILL |
| R2 | `funding_ts_z30` | −0,437% | −5,82 | KILL |
| R3 | `vol_z30` | +0,008% | +0,09 | KILL |
| R4 | `ret_24h` × likuiditas | −0,190% | −1,52 | KILL |
| R5 | `atr14_norm` (kontrol) | +0,189% | +1,41 | KILL |
| R6 | funding × likuiditas | +0,448% (L3) | +2,15 | KILL |
| R7 | funding × momentum | — | — | KILL |
| R8 | Trigger EMA9/EMA21 | +0,023% | +0,08 | KILL |
| R9 | SMC bias swing (len 50) | −0,271% | −1,17 | KILL |
| R10 | SMC bias internal (len 5) | −0,191% | −0,81 | KILL |
| R11 | Jenis event BOS/CHoCH | −0,528% … +0,120% | \|t\| < 1,6 | KILL |
| R12 | Keselarasan swing × internal | −0,388% | −1,14 | KILL |
| R13 | CHoCH + EMA9 (alur §4 dok. strategi) | −0,135% | −2,16 | KILL (arah salah) |
| R14 | Fair Value Gap | +0,126% | +0,33 | KILL |
| R15 | Order Block | −0,651% | −1,80 | KILL |
| R16 | Volume Profile / POC / value area | +0,013% … +0,163% | < 1,3 | KILL |
| R17 | Jarak ke swing high/low | +0,204% | +1,65 | KILL |
| R18 | Split regime BTC | — | — | H1 bertahan di kedua rezim |
| R19 | CVD 24 jam | +0,029% | +0,45 | KILL |
| R20 | CVD 72 jam | +0,153% | +1,96 | KILL |
| R21 | Taker ratio z30 | −0,049% | −0,77 | KILL |
| R21b | Divergensi CVD akumulasi−distribusi | +0,363% | +1,27 | KILL |
| H1 | Funding negatif + z-rank terendah | +0,536% net | +2,30 | **bertahan** |
| H2 | VEB breakout 4H | −0,106 avgR | −0,85 | GAGAL |

Kriteria KEEP (ditetapkan **sebelum** melihat hasil, `src/config.py`):
spread net ≥ 0,5% **dan** |t| ≥ 2,5 **dan** ≥ 200 hari.

---

## 4. Data — apa saja yang ada dan dari mana

### 4.1 Sumber (semua publik, tanpa API key)

| Sumber | Endpoint | Dipakai untuk |
|---|---|---|
| **Arsip Binance** | `data.binance.vision/data/futures/um/{monthly,daily}/klines/...` | Klines 1H perp, 2024-06 → 2026-07 |
| **Arsip Binance** | `.../monthly/fundingRate/{SYM}/...` | Funding rate aktual (terbit bulanan, lag s/d 1 bulan) |
| **Gate.io** | `api.gateio.ws/api/v4/futures/usdt/contract_stats` | Positioning harian: OI, LSR, likuidasi |
| **Binance fapi** | `fapi.binance.com` | Hanya di-**probe** tiap run; selalu gagal (lihat §5) |

### 4.2 Yang ada di disk lokal (~900 MB, di-`gitignore`)

| Direktori | Isi | Ukuran |
|---|---|---:|
| `data/raw/` | 29.271 file ZIP: klines 1H + fundingRate mentah | 457 MB |
| `data/panel.parquet/` | Panel utama, partisi bulanan, 371.408 baris × 47 kolom | 88 MB |
| `data/interim/` | Fitur per symbol | 92 MB |
| `data/smc/`, `data/ext/` | Struktur SMC, Order Block / FVG / VPVR | 55 MB |
| `data/hours/`, `data/horizons/` | Panel jam entry & horizon exit | 186 MB |
| `data/orderflow/` | CVD / taker ratio | 24 MB |
| `data/daily_market.csv`, `data/universe_log.csv` | Agregat pasar & log universe | kecil |

Panel harian dibangun anti-lookahead: fitur hari `d` hanya memakai bar yang sudah
tertutup pada `d` 00:00 UTC, label `fwd_24h/48h/72h` diambil dari open bar 1H.

**Skema CSV di dalam ZIP** — klines: `open_time, open, high, low, close, volume,
close_time, quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore`
(`open_time` epoch **milidetik** UTC). Funding: `calc_time,
funding_interval_hours, last_funding_rate`, terbit tiap 8 jam (00/08/16 UTC).

### 4.3 Yang di-commit ke repo ini

| Path | Isi | Catatan |
|---|---|---|
| `oi_logs/date=YYYY-MM-DD/` | Positioning Gate.io harian (Parquet + `manifest.json`) | **Satu-satunya salinan** — Gate.io hanya menyimpan ~42 hari riwayat |
| `oi_logs/_state.json` | Timestamp terakhir per kontrak (mode inkremental) | |
| `results/` | 32+ file: `summary.csv`, `spreads.csv`, `R0`–`R13`, `ext_summary.csv`, `smc_summary.csv`, `GATE_executability.md`, `portfolio_sim.csv`, `hour_sensitivity.csv`, `skema2_sinyal.csv` (30.368 sinyal), 2 PNG | |
| `src/` | Pipeline lengkap (lihat §7) | |
| `pine/` | 2 script TradingView | |
| `docs/`, `*.md` | Spec, brief, temuan, register hipotesis | |

Kolom `oi_logs`: `open_interest`, `open_interest_usd`, `lsr_account`, `lsr_taker`,
`top_lsr_account`, `top_lsr_size`, `top_long_size`, `top_short_size`,
`long_taker_size`, `short_taker_size`, `long_liq_usd`, `short_liq_usd`,
`long_liq_size`, `short_liq_size`, `long_users`, `short_users`, `mark_price`,
`last_funding_rate`, `contract`, `symbol`, `time`.

> ⚠️ **Ini positioning Gate.io, bukan Binance.** Basis trader-nya berbeda. Overlap
> symbol dengan universe Binance 595 dari 769 (77%). Boleh dipakai sebagai proksi
> untuk menguji apakah positioning punya kandungan prediktif, **tidak boleh**
> diklaim sebagai OI Binance. Wajib ditandai di setiap analisis yang memakainya.

### 4.4 Jebakan data yang sudah ditemukan (jangan diulang)

- **Klines nol-volume untuk perp mati.** Arsip terus menerbitkan bar untuk perp
  yang sudah delisted. Mendeteksi dari "kapan file berhenti" hanya menemukan
  7 symbol; indikator sebenarnya `volume == 0` — **44 symbol** punya >50% hari nol
  volume, total **9,5% panel**. Tiga symbol (AGIXUSDT, OCEANUSDT, WAVESUSDT) nol
  volume 730 hari penuh.
- **`stepSize` diturunkan dari volume.** `exchangeInfo` tidak bisa diakses, jadi
  `stepSize` dihitung dari eksponen desimal kolom `volume` per (symbol, bulan) —
  tepat 5/5 pada symbol yang nilainya diketahui, dan lebih baik dari snapshot
  karena point-in-time serta tetap ada untuk symbol delisted. `minQty` dan
  `MIN_NOTIONAL` **tetap asumsi**, ditandai di semua output.
- **Bug grouping pandas 3.0.** `ts.astype("int64") // 10**9` salah karena pandas 3.0
  menyimpan timestamp sebagai `datetime64[ms]` — seluruh ranking cross-sectional
  rusak dan sempat memberi hasil berlawanan arah yang tampak signifikan. Diganti
  `pd.factorize`.
- **Parquet tidak terbaca di mesin lokal.** `pyarrow._parquet` diblokir Windows
  Application Control policy. Karena itu pipeline VEB dibangun membaca langsung
  dari ZIP (~0,2 dtk/symbol untuk 2 tahun klines 1H, 134 dtk untuk 810 symbol).

---

## 5. Koneksi — repo ini nyambung ke mana saja

| Tujuan | Arah | Kapan | Kredensial |
|---|---|---|---|
| `data.binance.vision` | tarik arsip ZIP | manual, saat `fetch.py` dijalankan | tidak ada |
| `api.gateio.ws` | tarik `contract_stats` | **otomatis, cron 01:20 UTC** | tidak ada |
| `fapi.binance.com` | probe + coba `exchangeInfo` | tiap run logger, selalu gagal | tidak ada |
| **GitHub Actions** | penjadwal + commit balik ke `main` | harian | `GITHUB_TOKEN` bawaan |
| **TradingView** | manual, tempel `pine/*.pine` ke chart | manual | tidak ada |

**Tidak tersambung ke:** API trading bursa mana pun, Telegram, Google Sheets,
database, broker, atau layanan berbayar. **Repository secrets: kosong.**
Tidak ada order yang pernah dikirim dari repo ini.

### Batasan akses jaringan (terverifikasi, bukan dugaan)

| Endpoint | Dari mesin lokal (Indonesia) | Dari GitHub Actions (US) |
|---|---|---|
| `fapi.binance.com` | ConnectTimeout (blokir ISP) | **HTTP 451** restricted location |
| `api.binance.com`, `www.binance.com` | ConnectTimeout | HTTP 451 |
| `api.bybit.com`, `www.okx.com` | ConnectTimeout | belum diuji |
| **`data.binance.vision`** | **200 OK** | 200 OK |
| `data-api.binance.vision` | 200 OK — **spot saja**, futures 404 | 200 OK |
| **`api.gateio.ws`** | **200 OK** | **200 OK** |

Konsekuensinya: data OI/LSR/taker Binance **mustahil** diambil dari lokasi mana
pun yang tersedia (arsip `futures/um/daily/metrics/` juga berhenti 2022-01-13),
sehingga diganti Gate.io. Funding rate yang terbit bulanan bisa direkonstruksi
dari `premiumIndexKlines` harian bila butuh lag 1 hari (korelasi +0,84 pada
agregat 24 jam, sepakat tanda 80,9%).

### Stage 0 logger — satu-satunya yang jalan otomatis

[`.github/workflows/stage0-logger.yml`](.github/workflows/stage0-logger.yml)

| | |
|---|---|
| Jadwal | cron **01:20 UTC** harian + `workflow_dispatch` |
| Sumber | Gate.io `/futures/usdt/contract_stats`, interval 1 jam, limit 1000 (~42 hari) |
| Mekanisme | Inkremental via `oi_logs/_state.json`; bootstrap ~42 hari, lalu ~24 baris/kontrak/hari |
| Run pertama | 2026-08-23 — 867.808 baris / 935 kontrak |
| Run terakhir tercatat | 2026-09-06 — 23.854 baris / 979 kontrak, 52 detik |
| Output | Di-commit balik ke `main` oleh workflow (`permissions: contents: write`) |

Kenapa di Actions dan bukan di mesin lokal: `fapi.binance.com` diblokir dari
Indonesia, dan retensi data ini hanya ~42 hari — kalau tidak dicatat harian,
datanya hilang selamanya.

---

## 6. Peta dokumen

| File | Isi |
|---|---|
| [`HYPOTHESIS_REGISTER.md`](HYPOTHESIS_REGISTER.md) | **Baca pertama.** Definisi H1 & H2 yang dikunci, prediksi yang bisa salah, status |
| [`SESSION_2026-08-23.md`](SESSION_2026-08-23.md) | Ringkasan sesi riset utama: 22 keluarga uji, batasan akses, tiga koreksi terhadap hasil sendiri |
| [`STAGE_1_1_FINDINGS.md`](STAGE_1_1_FINDINGS.md) | Temuan Stage 1.1 lengkap + addendum SMC |
| [`CLAUDE-CODE-HANDOFF.md`](CLAUDE-CODE-HANDOFF.md) | Handoff & parameter terkunci Stage 1.1 |
| [`docs/dew-futures-screener-strategy.md`](docs/dew-futures-screener-strategy.md) | Spec strategi awal — **sebagian besar sudah ditolak data**, disimpan sebagai catatan |
| [`docs/dew-action-plan.md`](docs/dew-action-plan.md) | Rencana Stage 0–6 |
| [`docs/stage-1.1-backtest-brief.md`](docs/stage-1.1-backtest-brief.md) | Brief eksekusi backtest, kriteria KEEP ditetapkan sebelum melihat hasil |
| [`results/GATE_executability.md`](results/GATE_executability.md) | Laporan gate eksekutabilitas $6 |

---

## 7. Struktur kode

| File | Fungsi | Waktu jalan |
|---|---|---|
| `src/config.py` | Konstanta terkunci: notional, periode, biaya, kriteria KEEP | — |
| `src/fetch.py` | Download + cache arsip `data.binance.vision` | 5,8 mnt / 29.145 file |
| `src/features.py` | Panel harian anti-lookahead, MAE/MFE, `stepSize` dari GCD volume | 0,7 mnt |
| `src/panel.py` | Fitur cross-sectional, gate eksekutabilitas, agregat pasar | 0,1 mnt |
| `src/gate_table.py` | Tabel gate `stepSize` × harga | — |
| `src/stats.py` | SE cluster per tanggal, cluster bootstrap, Bonferroni | — |
| `src/ablation.py` | R0–R8 | 1,3 mnt |
| `src/smc.py` + `src/ablation_smc.py` | Port SMC LuxAlgo (leg/pivot/BOS/CHoCH) → R9–R13 | 1,0 mnt |
| `src/factors_ext.py` + `src/ablation_ext.py` | Order Block, FVG, Volume Profile, swing → R14–R18 | 2,6 mnt |
| `src/orderflow.py` | CVD / taker ratio dari kolom klines → R19–R21 | 0,3 mnt |
| `src/hour_sensitivity.py` | Panel mini di 6 jam entry berbeda | 0,7 mnt |
| `src/exit_horizon.py` | Label forward 8/12/24/36/48/72/96 jam | 0,6 mnt |
| `src/walkforward.py` | 9 fold rolling 6/2 bulan | 0,2 mnt |
| `src/portfolio.py` | Simulasi portofolio sizing dinamis | 0,5 mnt |
| `src/chart.py` | `results/funding_bucket_curve.png` | — |
| `src/logger.py` | Stage 0 logger harian (dipanggil GitHub Actions) | 55 dtk/hari |

**Jalan ulang dari nol: ~15 menit** di luar download pertama.

### Script TradingView (`pine/`)

| File | Isi |
|---|---|
| `stage1_1_replica.pine` | Replika **mekanika** backtest Stage 1.1 di chart 1H — bukan strategi yang direkomendasikan |
| `skema2_execution.pine` | Manajer eksekusi Skema 2 (strateginya sendiri sudah dibatalkan) |

Keduanya membawa peringatan yang sama: **funding rate Binance tidak tersedia
sebagai deret data di TradingView**, dan faktor cross-sectional butuh meranking
~470 koin pada hari yang sama — mustahil di Pine yang hanya melihat satu symbol.
Basis perp−spot sudah diuji sebagai proksi funding dan **gagal**: korelasi +0,008,
sepakat tanda 50,7% (setara lempar koin), menangkap sinyal asli 18,8%.

---

## 8. Cara menjalankan ulang

Butuh Python 3.12+, `pandas`, `pyarrow`, `requests`, `matplotlib`.

```bash
cd "C:\Crypto data 2"
set PYTHONIOENCODING=utf-8

python src\fetch.py            # download arsip (5,8 mnt, 457 MB)
python src\features.py         # panel per symbol
python src\panel.py            # fitur cross-sectional + gate
python src\ablation.py         # R0-R8
python src\ablation_smc.py     # R9-R13
python src\ablation_ext.py     # R14-R18
python src\orderflow.py        # R19-R21
python src\walkforward.py      # 9 fold
python src\portfolio.py        # simulasi portofolio
```

Logger Stage 0 (biasanya dipanggil GitHub Actions, bisa juga lokal):

```bash
python src\logger.py --workers 8
```

---

## 9. Jadwal

| Kapan | Aksi |
|---|---|
| Sekarang – Oktober 2026 | Logger jalan otomatis. **Tidak ada backtest baru** dari data lama |
| ~1 November 2026 | Uji H1 di data Ags–Okt 2026 yang belum pernah dilihat. Kriteria lulus: net > 0 **dan** t > 2,0 |
| Kalau H1 lolos | Paper trading 60 hari — yang diukur **selisih fill vs sinyal**, bukan P&L |
| Kalau H1 gagal | Strategi funding ditutup. Lanjut ke positioning Gate.io |
| Kapan pun | Kirim `exchangeInfo` via VPN → validasi asumsi `minQty` / `MIN_NOTIONAL` |

### Arah yang belum tersentuh

| Arah | Kenapa layak | Status data |
|---|---|---|
| Positioning Gate.io (OI, LSR, likuidasi) | Satu-satunya lapisan yang belum pernah diuji sama sekali | Logger jalan, data terkumpul sejak 2026-08-23 |
| Horizon > 48 jam | Literatur menempatkan momentum kripto di 2–4 minggu; window sekarang di bawahnya | Klines sudah ada, tinggal hitung label |
| Cross-exchange funding spread | Funding Gate.io ≠ Binance; selisihnya bisa jadi sinyal maupun arbitrase | Kedua sumber sudah jalan |
| Order book / mikrostruktur | `bookTicker` & `bookDepth` ada di arsip, belum disentuh | `futures/um/daily/bookDepth` |
| Sisi kebalikan H1 (funding tinggi → short perp + long spot) | Bisa di-hedge murah, tidak perlu pinjam koin | Spot tersedia via `data-api.binance.vision` |

---

## 10. Peringatan penutup

Angka terbaik yang pernah dihasilkan repo ini — H1, +0,536% per trade, CAGR
+2,90% — berasal dari periode di mana efeknya meluruh dari **+0,901%** (tahun 1)
ke **+0,053%** (dua bulan terakhir).

Yang berhasil dicapai bukan menemukan strategi, melainkan **menutup 24
kemungkinan dengan biaya nol** — termasuk seluruh kerangka SMC yang jadi dasar
dokumen strategi awal. Itu hasil yang valid, dan jauh lebih murah daripada
menemukannya lewat setahun trading.

**Jangan pakai uang sungguhan sebelum uji November 2026.**
