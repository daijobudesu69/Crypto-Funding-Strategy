# Hypothesis Register

Aturan yang **dikunci sebelum** diuji pada data yang belum ada. Tujuannya satu:
begitu sebuah aturan ditemukan lewat pencarian di data lama, satu-satunya uji
yang tidak bisa dicurangi adalah uji pada data yang belum pernah dilihat siapapun.

Setiap entri: definisi persis, tanggal dikunci, dan prediksi yang bisa salah.
Dilarang mengubah definisi setelah data baru masuk. Kalau ingin varian lain,
daftarkan sebagai entri baru.

---

## H1 — Funding negatif + z-score funding terendah, LONG

**Dikunci:** 2026-08-23
**Ditemukan lewat:** pencarian post-hoc di panel 2024-08-01..2026-07-31
(14 run ablation → dua kandidat nyaris lolos → irisan keduanya diuji).
Karena itu hasil in-sample-nya **tidak** bisa dianggap bukti.

### Definisi (final, tidak boleh diubah)

Pada tiap tanggal `d` pukul 00:00 UTC, untuk tiap symbol perp USDT Binance
USDⓈ-M yang punya ≥30 hari riwayat klines:

```
funding_24h_sum   = jumlah funding rate dalam (d-1 00:00, d 00:00]
funding_ts_z30    = (funding_24h_sum - mean30) / std30   (riwayat symbol sendiri)
zrank             = peringkat persentil funding_ts_z30 di antara symbol
                    eligible pada tanggal d

SINYAL LONG bila:  funding_24h_sum <= 0  DAN  zrank <= 0.20
```

- Entry: open bar 1H pukul `d` 00:00 UTC
- Exit: open bar 1H 48 jam kemudian (tanpa stop/target)
- Sizing: notional $6.00 fixed, equal-weight
- Biaya: fee maker 0.02%×2 + slippage 0 (limit order dianggap fill) = 0.04%
  round trip, ditambah funding aktual yang dibayar selama hold
- Hanya symbol dengan `executable_100usd == True`

### Prediksi yang bisa salah

Pada data 2026-08-01 dan sesudahnya, mean net return per observasi **> 0**
dengan t clustered per tanggal **> 2,0**.

### Yang sudah diketahui (in-sample + walk-forward, BUKAN bukti)

| Ukuran | Nilai |
|---|---|
| Full-sample net | +0,493% (t=2,17), n=33.708 |
| Spread vs sisanya | +0,741% CI [+0,461%, +1,021%] (t=5,20) |
| Walk-forward OOS gabungan | +0,634% CI [+0,049%, +1,219%] (t=2,13), n=22.045 |
| Fold OOS positif | 8 dari 9 |
| Degradasi IS→OOS | 18,0% |
| **Fold terakhir (Jun–Jul 2026)** | **+0,053% (t=0,08); aturan tetap −0,423%** |

### Kekhawatiran yang belum terjawab

1. Efeknya **meluruh**: paruh-1 +0,901%, paruh-2 +0,236%, fold terakhir ~0.
   Bisa berarti edge yang sudah diarbitrase habis, bukan edge yang stabil.
2. Aturan ini hasil pencarian. Bonferroni mengoreksi jumlah uji, bukan proses
   pemilihannya.
3. Frekuensi sinyal ~46/hari, jauh melebihi kapasitas 3 slot. Aturan pemilihan
   di antara 46 kandidat **belum ditentukan** dan akan menambah derajat bebas baru.

### Status

~~**BELUM TERVALIDASI.**~~ → lihat hasil uji forward di bawah.

### Uji forward 2026-08-01..2026-10-31 — dijalankan 2026-11-08 — **LULUS**

Uji sekali pakai. Definisi, ambang, horizon, biaya: persis seperti di atas, tidak
ada yang disetel. Skrip: `src/h1_forward.py` (pipeline fetch/features/panel/stats
yang sama, periode di-override di memori). Output: `results/h1_forward/`.

| Ukuran | Nilai |
|---|---|
| n observasi | **4.162** (87 hari, ~47,8 sinyal/hari) |
| Mean net / observasi | **+1,058%** |
| CI 95% (t, cluster tanggal) | [+0,296%, +1,821%] |
| CI 95% (bootstrap tanggal) | [+0,336%, +1,836%] |
| **t clustered per tanggal** | **+2,76** (p = 0,007) |
| Komponen harga setelah fee | +0,714% |
| Komponen funding diterima | +0,345% |
| Spread vs sisa universe executable | +0,535% (t = 1,94) |
| Rata-rata seluruh universe executable | +0,566% (pasar naik) |

**Kriteria (mean > 0 DAN t > 2,0): LULUS.**

Per bulan: Agustus +1,578% (t 2,70) · September +1,292% (t 1,67) ·
**Oktober +0,202% (t 0,32)**.

Pembanding: in-sample +0,536% (t 2,30) · walk-forward OOS +0,634% (t 2,13) ·
fold terakhir Jun–Jul +0,053%. Peluruhan agregat **tidak** berlanjut, tetapi di
dalam periode forward sendiri polanya menurun lagi: Ags → Sep → Okt ≈ 0.

Pemeriksaan bug (aturan #4, karena hasil berlawanan arah dengan tren peluruhan):
- Rekonsiliasi manual 3 baris acak dari ZIP mentah (funding_24h_sum, fwd_48h,
  funding dibayar): cocok persis.
- Kode yang sama dijalankan ulang di panel in-sample: +0,527% (t 2,26) vs
  tercatat +0,536% (t 2,30) → pipeline konsisten.
- Grouping tanggal via `pd.factorize`; zrank dihitung di antara symbol eligible
  (teks definisi), baru disaring `executable_100usd`.
- 5 kontributor terbesar (LSK, SKR, ONG, ONE, RLC) = 37,6% total P&L. Dicek di
  data 1H: pump nyata dengan volume puluhan–ratusan juta USD/jam dan funding
  sangat negatif (short squeeze), bukan artefak arsip.

Fakta yang wajib dibawa ke tahap berikutnya (bukan alasan mengubah vonis):
- **Sangat bergantung ekor.** Median per observasi −0,03%; hanya 49,4% positif.
  Winsorize 1%: +0,663% (t 1,92). Tanpa 5 symbol teratas: +0,673% (t 1,93).
  Dengan 3 slot dari ~48 kandidat/hari, menangkap ekor itu bergantung pada aturan
  pemilihan yang belum ditentukan (kekhawatiran #3 di atas).
- **Celah data:** arsip Binance tidak memuat 2026-10-28 sama sekali (monthly 1H
  hanya 720/744 jam, checksum resmi cocok; daily 404). Akibatnya sinyal 26, 28,
  29 Okt tidak punya harga entry/exit. Sinyal 30–31 Okt tidak punya funding hold
  (arsip November belum terbit, fapi tidak tembus). Total 228 sinyal tanpa label
  dibuang. Sensitivitas: menambal 26 Okt dengan close 27 Okt 23:00 → +1,039%
  (t 2,76), tidak mengubah apa pun.
- 133 symbol dipangkas ekor klines nol-volume-nya (perp delisted).

### Status

**LULUS uji forward.** Langkah berikutnya sesuai rencana: paper trading 60 hari
yang mengukur **selisih fill vs sinyal**, bukan P&L. Tetap **jangan dipakai live**.
Uji forward ini sudah terpakai — tidak boleh diulang dengan ambang lain.

---

## Koreksi 2026-08-23 (sore) — stop loss membunuh H1

Ditemukan saat Dew menanyakan dasar angka stop 3%: **saya yang mengarang 3%**,
Dew hanya pernah menetapkan RR 2:1 dan SL maksimum 5%.

Saat diuji ulang dalam batasan itu, ditemukan kesalahan akuntansi yang lebih
serius: seluruh hitungan ber-stop sebelumnya mengkredit funding **48 jam penuh**
ke trade yang keluar di jam ke-2. Karena 71% keuntungan H1 berasal dari funding
yang diterima, itu melebih-lebihkan setiap baris ber-stop.

Setelah funding dihitung sampai jam keluar sebenarnya (path scan 1H):

| SL | TP | median jam keluar | komponen harga | funding diterima | net | t |
|---|---|---:|---:|---:|---:|---:|
| 1% | 2% | 2 | -0,125% | +0,0199% | **-0,145%** | -4,77 |
| 2% | 4% | 6 | -0,082% | +0,0305% | -0,091% | -1,46 |
| 3% | 6% | 13 | -0,096% | +0,0483% | -0,088% | -0,95 |
| 4% | 8% | 19 | -0,138% | +0,0705% | -0,107% | -0,90 |
| 5% | 10% | 30 | -0,181% | +0,0926% | -0,129% | -0,91 |
| tanpa SL/TP | — | 48 | +0,197% | +0,3788% | **+0,536%** | +2,30 |

**Setiap tingkat stop negatif.** Mekanismenya: stop memotong hold, hold pendek
mengumpulkan funding jauh lebih sedikit (0,02% vs 0,38%), sementara komponen
harganya negatif di semua tingkat.

Konsekuensi: **"Skema 2" (H1 + stop 3%/target 6%) DIBATALKAN.** Yang bertahan
hanya H1 tanpa stop, keluar di 48 jam. Angka portofolio Skema 2 yang pernah
dilaporkan ($120,84 lalu $106,57) keduanya salah.

### Ambang: kenapa tetap `<= 0` dan `rank <= 20%`, bukan yang lebih ketat

Grid in-sample memang lebih suka ambang ketat (funding <=-0,05% -> +0,749%;
z <=-1,50 -> +1,007%). Tapi walk-forward dengan grid diperluas ke ambang ketat:

| Grid | OOS gabungan | t | CI 95% | degradasi |
|---|---:|---:|---|---:|
| Longgar (f<=0, rank<=20%) | +0,634% | **+2,13** | [+0,049%, +1,219%] | 18,0% |
| Diperluas ke ketat | +0,658% | +1,70 | **[-0,102%, +1,419%]** | 28,6% |

Ambang ketat menaikkan mean tapi menurunkan t dan membuat CI melewati nol —
sinyalnya jadi terlalu sedikit. Ambang longgar dipertahankan karena lebih tahan
di luar sampel, bukan karena lebih bagus di dalam sampel.

---

## H2 — VEB (Volatility-Expansion Breakout), LONG — **GAGAL**

**Didaftarkan & diuji:** 2026-08-25
**Sumber definisi:** `VEB_STRATEGY_SPEC.md` v1.1, parameter dibekukan oleh pemilik
spec pada 2026-08-25 **sebelum** menyentuh panel ini. Karena itu H2 **tidak** kena
penalti Bonferroni dari 22 keluarga uji Sesi A — ambangnya |t| > 2 yang normal.

### Definisi (persis spec §3–§5, tidak diubah)

```
Pada tiap bar 4H tertutup (00,04,08,12,16,20 UTC), untuk tiap perp USDT
Binance USDS-M dengan >=700 bar 4H riwayat:

  mom180   = close/close.shift(180) - 1
  volratio = std(ret1,30,ddof=1) / std(ret1,90,ddof=1)
  atr14    = rolling MEAN True Range 14 bar   (BUKAN Wilder)
  atr_rank = atr_pct.rolling(500).rank(pct=True)
  hh20     = high.rolling(20).max().shift(1)

  SINYAL LONG bila: mom180>0 DAN volratio>1 DAN atr_rank<=0,50 DAN high>hh20

  Entry : open bar 4H berikutnya
  SL    : entry - 1,0 x atr14   TP: entry + 4,0 x atr14
  Time  : keluar di market setelah 6 bar (24 jam)
  Urutan sentuh SL vs TP: path scan bar 1H di dalam bar 4H
  Biaya : 0,20% pulang-pergi + funding aktual sampai jam keluar sebenarnya
```

### Prediksi yang bisa salah (dibuat sebelum uji)

Spec §5.3 / §14: avgR positif, sekitar **+0,410**; win rate ~43%; DD 15–20%.

### Hasil

| Universe | n | avgR kotor | avgR bersih | t | Vonis |
|---|---:|---:|---:|---:|---|
| 8 simbol yang spec setujui | 348 | +0,193 | +0,064 | +0,32 | tidak beda dari nol |
| Universe layak spec (kri. §1.3 no.3+4) | 2.057 | +0,077 | −0,027 | −0,17 | nol |
| **Seluruh panel** | **11.271** | **−0,012** | **−0,106** | **−0,85** | **nol / minus** |

| Klaim | Hasil |
|---|---|
| avgR +0,410 | +0,373 di **BTC saja** (reproduksi berhasil) → −0,012 di 586 koin |
| 8/8 simbol positif | 3/8 positif setelah biaya; seluruh surplus dari DOGEUSDT (+1,16) |
| win rate 43% | 30,6% |
| R:R 4:1 | efektif 1,9:1 — TP 4 ATR kena hanya 8,4% trade |
| DD 15–20% | 30–32%, kill switch kena di **semua** konfigurasi portofolio |
| leverage <= 2x | leverage portofolio nyata **5,12x** (bug: cap per posisi, 3 posisi paralel) |

Konsistensi: **1 dari 9 kuartal positif**; 4 kuartal terakhir minus dengan |t|>2.
Per koin: hanya 33,4% dari 316 koin (>=15 trade) positif setelah biaya.

### Temuan sampingan yang menutup pertanyaan terbuka

**Bias path scan yang dikhawatirkan `PERBANDINGAN_H1_vs_VEB.md` §4.2 tidak nyata.**
Hanya 7/11.312 trade (0,06%) menyentuh SL dan TP di bar 1H yang sama. Selisih
avgR antara scan 1H dan scan 4H saja = **0,013R**. Dengan SL 1 ATR / TP 4 ATR,
jarak keduanya terlalu jauh untuk tersentuh dalam satu jam. Pertanyaan ini
**selesai** — jangan diinvestigasi lagi.

### Status

**GAGAL. Ditutup.** Jangan di-tuning berdasarkan hasil ini — uji bersihnya sudah
terpakai; menyetel parameter sekarang mengubah validasi menjadi pencarian.
Laporan lengkap: `results/veb/HASIL_BACKTEST_VEB.md`.
