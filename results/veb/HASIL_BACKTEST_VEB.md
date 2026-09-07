# Hasil Backtest VEB v1.1 — di panel Binance perp, dengan path scan 1H

**Tanggal:** 2026-08-25 · **Spec yang diuji:** `VEB_STRATEGY_SPEC.md` v1.1 (final, parameter dibekukan)
**Data:** arsip `data.binance.vision`, klines 1H asli perp Binance USDⓈ-M + funding rate aktual
**Periode sinyal:** 2024-09-25 → 2026-07-30 (setelah warm-up 700 bar)
**Biaya:** 0,20% pulang-pergi (taker 0,05%×2 + slippage 0,05%×2)

---

## 1. Jawaban singkat, tanpa istilah teknis

Strategi ini **tidak menghasilkan keuntungan**. Bukan karena rugi besar — tapi karena
**keuntungan kotornya nol**, dan begitu biaya transaksi dimasukkan, hasilnya jadi minus.

Bayangkan begini: setiap trade mempertaruhkan 1 satuan risiko. Spec mengklaim rata-rata
tiap trade menghasilkan **+0,41 satuan**. Setelah diuji ke 586 koin dengan data harga
Binance yang sebenarnya, hasilnya:

| | Rata-rata untung per trade | Artinya |
|---|---:|---|
| Klaim spec (BTC saja, tanpa biaya) | **+0,410** | Untung bagus |
| Hasil saya, BTC saja, tanpa biaya | **+0,373** | ✅ **Klaim spec terbukti benar untuk BTC** |
| Hasil saya, 586 koin, tanpa biaya | **−0,012** | Persis nol. Tidak ada edge |
| Hasil saya, 586 koin, dengan biaya | **−0,106** | Rugi |

Baris kedua penting: **saya berhasil mereproduksi angka penulis spec.** Jadi ini bukan
soal kode saya salah. Masalahnya, apa yang bekerja di BTC **tidak ada di koin lain.**

---

## 2. Bukti bahwa implementasi saya benar

Sebelum percaya hasil apa pun, saya jalankan dulu semua tes yang spec sendiri wajibkan (§12):

| Tes | Isi | Hasil |
|---|---|:-:|
| §12.1 Unit test | 11 angka acuan di bar BTCUSDT 2026-08-23 16:00 UTC | ✅ **11/11 dalam toleransi** |
| §12.2 Lookahead | Indikator dihitung di potongan data vs data penuh harus identik | ✅ **42/42 identik** |
| §12.3 Forming bar | Tidak ada bar yang belum selesai ikut terpakai | ✅ Lolos |
| §12.4 Sanity | SL < entry < TP, atr_rank ≤ 0,50, hold ≤ 24 jam | ✅ Semua lolos |

Detail §12.1 (spec pakai harga CoinGecko, saya pakai perp Binance — makanya ada selisih kecil):

| Besaran | Spec | Binance (saya) | Selisih | Toleransi | |
|---|---:|---:|---:|---:|:-:|
| close | 77.150,00 | 77.305,10 | +0,20% | ±0,5% | ✅ |
| mom180 | +0,204246 | +0,204139 | −0,0001 | ±0,02 | ✅ |
| rv30 | 0,014781 | 0,014615 | −1,12% | ±5% | ✅ |
| rv90 | 0,009569 | 0,009482 | −0,91% | ±5% | ✅ |
| volratio | 1,5446 | 1,5414 | −0,003 | ±0,05 | ✅ |
| hh20 | 79.320 | 79.555,5 | +0,30% | ±0,5% | ✅ |
| ll60 | 62.525 | 62.484,2 | −0,07% | ±0,5% | ✅ |
| atr14 | 1.154,07 | 1.130,86 | −2,01% | ±5% | ✅ |
| atr_pct | 0,014959 | 0,014629 | −2,21% | ±5% | ✅ |
| close[−181] | 64.065 | 64.199,5 | +0,21% | ±1% | ✅ |
| Σ TR 14 bar | 16.157 | 15.832 | −2,01% | ±5% | ✅ |

---

## 3. Hasil utama

Semua angka pakai **standard error yang di-cluster per tanggal** (kalau tidak, semua altcoin
yang bergerak barengan dihitung sebagai bukti terpisah dan angka t jadi 3–5× terlalu besar).
Aturan main: **|t| di atas 2 baru boleh dianggap bukan kebetulan.**

| Universe | Trade | Koin | Untung/trade **tanpa** biaya | Untung/trade **dengan** biaya | t | Kesimpulan |
|---|---:|---:|---:|---:|---:|---|
| **8 simbol yang spec setujui** | 348 | 8 | +0,193 | **+0,064** | +0,32 | Tidak bisa dibedakan dari nol |
| Universe layak spec (volume ≥50 jt/hari, funding rendah) | 2.057 | 164 | +0,077 | **−0,027** | −0,17 | Nol |
| **Seluruh panel** | 11.271 | 586 | −0,012 | **−0,106** | −0,85 | Nol / sedikit minus |

Dalam bentuk persen return per trade (lebih gampang dibayangkan):

| Universe | Return bersih rata-rata per trade |
|---|---:|
| 8 simbol spec | +0,17% |
| Universe layak spec | −0,13% |
| Seluruh panel | −0,23% |

### 3.1 Rincian dari mana angkanya

Seluruh panel, per trade:

| Komponen | Kontribusi | t |
|---|---:|---:|
| Gerak harga (kotor) | **−0,014%** | −0,05 |
| Biaya fee + slippage | **−0,200%** | — |
| Funding yang dibayar | −0,011% | −6,47 |
| **NET** | **−0,226%** | −0,73 |

Yang membunuh strategi ini bukan funding (filter §1.3 kriteria 4 memang bekerja — cuma 0,011%).
Yang membunuh adalah **biaya transaksi bertemu edge yang nol.**

---

## 4. Klaim spec vs kenyataan

| Klaim spec | Sumber | Hasil di data ini | Vonis |
|---|---|---|:-:|
| avgR +0,410 | §5.3 | +0,373 di BTC (tanpa biaya) — cocok. **−0,012 di 586 koin** | ⚠️ Benar di BTC, tidak berlaku di tempat lain |
| "8/8 simbol positif" | §1.2 | **3 dari 8 positif** setelah biaya (DOGE, BTC, ETH). SUSDT 0 dari 6 menang | ❌ Ditolak |
| Win rate ~43% | §13 | **36,5%** di 8 simbol, **30,6%** di panel | ❌ Lebih rendah |
| Risk:Reward 4:1 | §5.1 | **1,9 : 1** sebenarnya. TP 4 ATR cuma kena **8–10%** trade | ❌ Kosmetik |
| 15–20 trade/simbol/tahun | §13 | **10,4** | ⚠️ Lebih jarang |
| Drawdown 15–20% | §13 | **30–32%** — menabrak kill switch di **semua** konfigurasi | ❌ Ditolak |
| Leverage dibatasi 2x | §6.1 + §12.4 | Terkonfirmasi bug: **leverage portofolio nyata sampai 5,1x** | ❌ Bug nyata |

### 4.1 Kenapa "R:R 4:1" itu menyesatkan

| Cara keluar | Porsi trade | Rata-rata hasil (R) | Median lama tahan |
|---|---:|---:|---:|
| Kena stop loss | **62,6%** | −1,23 | 7 jam |
| Habis waktu 24 jam | 29,0% | +0,73 | 24 jam |
| Kena target 4 ATR | **8,4%** | +3,13 | 12 jam |

Target 4 ATR hampir tidak pernah kena. Yang benar-benar menentukan hasil adalah
**batas waktu 24 jam**, bukan angka 4,0 ATR. Rata-rata trade yang menang cuma
menghasilkan +1,99R, bukan +4R — jadi rasio efektifnya **1,9:1**, bukan 4:1.

---

## 5. Simulasi portofolio — $100, 3 slot, risk 2%

| Universe | Cara hitung ukuran | Ekuitas akhir | CAGR | Max DD | Leverage portofolio tertinggi | Kill switch |
|---|---|---:|---:|---:|---:|---|
| 8 simbol spec | seperti tertulis di spec | $99,05 | −0,5% | −32,1% | **5,12x** | 🛑 kena 2026-04-08 |
| 8 simbol spec | leverage dibatasi portofolio | $94,71 | −2,9% | −30,8% | 2,09x | 🛑 kena 2026-04-18 |
| Universe layak spec | seperti tertulis di spec | $86,51 | −7,6% | −30,9% | **4,11x** | 🛑 kena 2025-03-24 |
| Universe layak spec | leverage dibatasi portofolio | $74,46 | −14,8% | −30,7% | 2,08x | 🛑 kena 2025-03-24 |

Kalau kill switch dimatikan supaya seluruh periode kelihatan: ekuitas turun ke
**$72,89** (8 simbol) dan **$30,82** (universe layak) — turun 27% dan 69%.

**Bug leverage terkonfirmasi.** Spec §6.1 membatasi leverage per posisi, tapi §7
mengizinkan 3 posisi sekaligus. Di simulasi, total taruhan menyentuh **5,12 kali**
modal di akun $100 — bukan 2x seperti yang tertulis di checklist §12.4.

---

## 6. Dua kejutan

### 6.1 Kekhawatiran terbesar dokumen perbandingan ternyata TIDAK terbukti

`PERBANDINGAN_H1_vs_VEB.md` §4.2 menyebut "risiko terbesar VEB yang belum dihitung
siapa pun": tanpa menelusuri pergerakan harga di dalam bar, urutan sentuh SL vs TP
tidak bisa ditentukan, dan itu bisa membalik tanda hasil.

Saya sudah menelusurinya bar per bar dengan data 1H:

| Metode | avgR bersih, seluruh panel |
|---|---:|
| Telusur 1H, kalau ragu pilih yang merugikan | −0,297 |
| Telusur 1H, kalau ragu pilih yang menguntungkan | −0,294 |
| Cuma lihat bar 4H (metode lama yang dicurigai) | −0,307 |

Selisihnya **0,013R** — tidak berarti apa-apa. Alasannya: dengan stop 1 ATR dan
target 4 ATR, harga hampir mustahil menyentuh keduanya dalam satu jam yang sama.
Hanya **7 dari 11.312 trade (0,06%)** yang ambigu.

**Kekhawatiran itu boleh dicoret.** Bukan itu masalahnya.

### 6.2 Yang sebenarnya membunuh: biaya, bukan arah

| Biaya pulang-pergi | avgR seluruh panel | t |
|---:|---:|---:|
| 0,00% (mustahil) | −0,012 | −0,10 |
| 0,04% (limit order, optimis) | −0,069 | −0,55 |
| 0,10% (taker murni) | −0,155 | −1,19 |
| **0,20% (asumsi Dew)** | **−0,297** | −2,05 |
| 0,30% | −0,440 | −2,63 |

Bahkan kalau trading **gratis**, hasilnya tetap nol. Strategi ini tidak punya
apa pun untuk dibayar biayanya.

*(Catatan: kolom ini dihitung sebelum 41 trade perp emas/stablecoin dibuang —
stop-nya sangat kecil sehingga angka R-nya meledak. Setelah dibuang, avgR pada
biaya 0,20% jadi −0,106; polanya sama.)*

---

## 7. Konsistensi antar waktu

| Kuartal | Trade | avgR bersih | t |
|---|---:|---:|---:|
| 2024 Q3 | 210 | −0,01 | −0,04 |
| 2024 Q4 | 1.056 | −0,09 | −0,53 |
| 2025 Q1 | 262 | −0,62 | −3,79 |
| **2025 Q2** | 1.789 | **+0,44** | +0,94 |
| 2025 Q3 | 3.824 | −0,26 | −1,05 |
| 2025 Q4 | 462 | −0,51 | −3,01 |
| 2026 Q1 | 1.239 | −0,93 | −2,07 |
| 2026 Q2 | 1.976 | −0,69 | −2,39 |
| 2026 Q3 | 494 | −0,25 | −2,59 |

**1 kuartal positif dari 9.** Empat kuartal terakhir semuanya minus dengan |t| > 2.

Per koin (316 koin dengan ≥15 trade): hanya **33,4%** yang positif setelah biaya.
Kalau strategi ini benar-benar punya edge, angkanya harus jauh di atas 50%.

Di 8 simbol spec, seluruh hasil positif datang dari **satu koin**:

| Simbol | avgR bersih | Trade |
|---|---:|---:|
| DOGEUSDT | **+1,16** | 36 |
| BTCUSDT | +0,15 | 76 |
| ETHUSDT | +0,13 | 43 |
| ADAUSDT | −0,05 | 38 |
| SOLUSDT | −0,10 | 67 |
| SUIUSDT | −0,22 | 58 |
| HBARUSDT | −0,36 | 24 |
| SUSDT | −1,10 | 6 |
| **7 simbol tanpa DOGE** | **−0,06** | 312 |

---

## 8. Apa yang uji ini TIDAK buktikan

Supaya jujur:

1. **Periode lebih pendek dari riset asli.** Data Binance perp yang ada di disk mulai
   Juni 2024. Riset spec pakai BTC sejak 2020. Jadi ini menguji ~1,9 tahun, bukan 6 tahun.
   Mungkin saja VEB bekerja di rezim 2020–2023 dan berhenti bekerja setelahnya.
2. **`minQty` dan `MIN_NOTIONAL` masih asumsi** (BTC 100, ETH 20, sisanya 5 USDT).
   `exchangeInfo` tidak bisa diambil dari jaringan ini. `stepSize` bukan asumsi —
   diturunkan dari data volume, sudah tervalidasi 5/5.
3. **Slippage 0,05% per sisi adalah asumsi**, bukan pengukuran. Tapi lihat §6.2:
   bahkan pada biaya nol pun hasilnya nol.
4. **Sisi SHORT tidak diuji** — spec mematikannya secara default, jadi saya ikuti.
5. **Bar 4H yang datanya tidak lengkap dijadikan kosong (NaN), bukan membatalkan
   seluruh simbol** seperti perintah §2.5. Kalau dijalankan persis seperti spec,
   satu jam data hilang akan membuang seluruh riwayat simbol itu. Untuk 589 simbol
   itu tidak masuk akal. Di 8 simbol spec, jumlah bar bermasalah = **0**, jadi
   tidak ada bedanya di sana.

Yang uji ini **memang** buktikan: pada perp Binance 2024-09 s/d 2026-07, dengan harga
asli, funding asli, dan penelusuran intrabar — **VEB versi LONG tidak punya edge arah.**

---

## 9. Status uji pra-registrasi

VEB v1.1 memenuhi syarat uji bersih: parameternya dibekukan dan didokumentasikan
(spec §11.1, tanggal 2026-08-25) **sebelum** menyentuh panel ini. Jadi tidak kena
penalti Bonferroni dari 22 keluarga uji Sesi A. Ambangnya |t| > 2 yang normal.

**Prediksi spec:** avgR positif, sekitar +0,410.
**Hasil:** −0,012 kotor / −0,106 bersih, t = −0,85, n = 11.271.

> **VEB GAGAL uji pra-registrasi.** Ini uji tunggal dan bersih —
> tidak ada parameter yang di-tuning, tidak ada varian yang dicoba lalu dibuang.

---

## 10. Rekomendasi

| | Aksi | Alasan |
|---|---|---|
| ✅ | **Batalkan deployment VEB.** Coret checklist §15 | Gagal uji pra-registrasi di 586 aset. Tidak perlu 8 minggu paper trading untuk mengetahui ini |
| ✅ | Catat hasil ini di `HYPOTHESIS_REGISTER.md` sebagai H2 GAGAL | Menjaga rekam jejak. Hasil negatif juga hasil |
| ✅ | Coret kekhawatiran path-scan dari daftar risiko | Sudah diukur: 0,06% trade ambigu, dampak 0,013R |
| ❌ | **JANGAN** tuning VEB berdasarkan hasil ini | Itu mengubah uji validasi jadi pencarian. Uji bersihnya sudah terpakai |
| ❌ | **JANGAN** kejar "versi VEB yang lebih baik" | DSR spec sudah 0,03–0,14 setelah ~500 konfigurasi dicari. Menambah pencarian membuatnya makin pas ke masa lalu |
| ⚠️ | Kalau tetap mau lanjut riset breakout: uji di rezim 2020–2023 | Satu-satunya celah yang belum tertutup. Butuh arsip Binance yang lebih lama — bisa diunduh, `data.binance.vision` terjangkau |

### Yang tetap berlaku dari dokumen perbandingan

Temuan **§6.4 — berhenti mencari filter kualitas sinyal** justru makin kuat.
Sesi A: 22 keluarga faktor → 0 lolos. VEB §7.1: 12 metrik → 0 lolos. Sekarang
ditambah: aturan masuk VEB sendiri, diuji di 586 aset → edge nol.

Temuan **§6.1 (overlap universe H1 ∩ VEB ≈ nol)** tetap benar tapi jadi tidak relevan:
tidak ada gunanya menggabungkan dua sumber edge kalau salah satunya nol.

---

## 11. File yang dihasilkan

| File | Isi |
|---|---|
| `src/veb_data.py` | Loader arsip ZIP → grid 4H + indikator spec §3 |
| `src/veb_engine.py` | Mesin sinyal + exit lewat path scan 1H |
| `src/veb_run.py` | Runner per universe |
| `src/veb_stats.py` | Ringkasan dengan cluster SE |
| `src/veb_portfolio.py` | Simulasi 3 slot, rotasi mingguan, dua varian sizing |
| `results/veb/trades_spec8.csv` | 348 trade, 8 simbol |
| `results/veb/trades_full.csv` | 11.312 trade, 589 simbol |
| `results/veb/trades_full_clean.csv` | + kolom funding 90 hari, tanpa perp emas/stablecoin |
| `results/veb/veb_hasil.png` | Kurva ekuitas + avgR kumulatif |

Catatan teknis: `pyarrow._parquet` diblokir Application Control policy di mesin ini
per 2026-08-25, jadi seluruh pipeline VEB baca langsung dari ZIP arsip, tidak lewat
`data/panel.parquet`. Hasilnya tidak terpengaruh — sumber datanya sama.
