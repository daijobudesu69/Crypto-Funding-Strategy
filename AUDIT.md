# Audit infrastruktur — 2026-09-07

Lingkup: **infrastruktur saja.** Definisi strategi tidak disentuh sama sekali —
H1 tetap `funding_24h_sum <= 0 AND zrank <= 0.20`, entry open 00:00 UTC, exit 48
jam, tanpa stop, tanpa target. Tidak ada ambang yang digeser, tidak ada faktor
baru, tidak ada parameter yang di-tuning. Yang diperiksa: apakah pipeline-nya
benar-benar jalan seperti yang ditulis README, dan apakah angka yang keluar
dihitung dengan benar.

**Metode.** Seluruh `src/*.py` dibaca baris per baris, lalu pipeline dijalankan
end-to-end di universe 60 symbol (58 eligible + BTC/ETH benchmark, 730 hari,
29.524 baris eligible) pada Python 3.14.5 / pandas 3.0.3 / numpy 2.4.6. Setiap
temuan di bawah direproduksi, bukan dibaca dari kode saja.

**Vonis singkat.** Metode intinya sehat. Panel anti-lookahead-nya benar, SE
cluster per tanggal benar, penurunan `stepSize` dari volume klines terbukti
**100% tepat** saat diadu dengan `exchangeInfo` asli. Yang rusak: urutan
menjalankan yang didokumentasikan (pipeline mati di langkah 5), dependensi yang
tidak lengkap, satu koreksi yang diumumkan tapi tidak pernah masuk ke kode, dan
gate eksekutabilitas yang menandai 4 symbol bisa ditradingkan padahal tidak.

---

## 0. Verifikasi terhadap `exchangeInfo` asli — kabar baik

`fapi.binance.com` **ternyata reachable dari mesin ini** (HTTP 200 pada
`/fapi/v1/ping`). Ini pertama kalinya asumsi §4.4 bisa diuji, dan
`src/logger.py` sudah punya jalurnya (`binance_exchange_info()`) — jalur itu
memang berjalan dan menyimpan snapshot 658 perp USDT.

| Asumsi di `config.py` | Kenyataan (exchangeInfo 2026-09-07) | Vonis |
|---|---|---|
| `stepSize` diturunkan dari eksponen desimal volume | cocok **54/54** symbol yang diperiksa | ✅ metode VALID |
| `minQty == stepSize` | benar **657/658**; pengecualian ALLUSDT (step 1, minQty 10) | ✅ VALID |
| `MIN_NOTIONAL` default 5 | benar **652/658** | ✅ VALID |
| `MIN_NOTIONAL_OVERRIDE = {BTC: 100, ETH: 20}` | BTC sebenarnya **50**; dan **BCH/LTC/ETC/LINK = 20** tidak terdaftar | ❌ SALAH (lihat B4) |

Yang layak digarisbawahi: metode point-in-time yang dipakai repo ini (turunkan
`stepSize` dari arsip) **lebih baik** daripada memakai snapshot hari ini, dan
sekarang terbukti akurat. Snapshot hanya dipakai untuk memperbaiki `MIN_NOTIONAL`
— bukan untuk menggantikan `stepSize`.

---

## A. Reproduksibilitas — pipeline tidak jalan seperti yang ditulis

### A1 — Urutan jalan di README §8 mati di langkah ke-5 ❌ → ✅ diperbaiki

Urutan lama melompati `smc.py` dan `factors_ext.py`, padahal keduanya PRASYARAT
yang membangun `data/smc/` dan `data/ext/`. Direproduksi:

```
python src/ablation_smc.py  ->  ValueError: No objects to concatenate
python src/ablation_ext.py  ->  ValueError: No objects to concatenate
```

Pesan errornya datang dari dalam pandas dan tidak menyebut penyebabnya sama
sekali. `gate_table.py`, `exit_horizon.py`, `hour_sensitivity.py`, dan `chart.py`
juga tidak ada di daftar — padahal `chart.py` yang menghasilkan dua PNG di
`results/`.

**Perbaikan:** README §8 ditulis ulang lengkap dengan urutan dependensinya, dan
kedua skrip ablation kini berhenti lebih awal dengan pesan yang menyebut skrip
prasyaratnya.

### A2 — `scipy` hilang dari daftar dependensi ❌ → ✅ diperbaiki

README §8 lama: "Butuh `pandas`, `pyarrow`, `requests`, `matplotlib`".
`src/stats.py` mengimpor `scipy`, dan **setiap** skrip ablation memakai
`src/stats.py`. Ikuti README apa adanya di mesin bersih → `ModuleNotFoundError`
pada skrip analisis pertama.

**Perbaikan:** `requirements.txt` (pipeline riset) + `requirements-logger.txt`
(cron harian) ditambahkan, dengan batas versi dan catatan kenapa. README §8
diperbarui.

### A3 — R19–R21 tidak ada kodenya ⚠️ ditandai, tidak ditambal

README §3 melaporkan spread untuk R19 / R20 / R21 / R21b dan README §7 menulis
"`src/orderflow.py` → R19-R21". Kenyataannya `orderflow.py` **hanya membangun
fitur** ke `data/orderflow/`. Tidak ada skrip ablation-nya, tidak ada
`results/R19*.csv`. Empat baris di tabel §3 itu tidak dapat direproduksi dari
repo ini.

**Keputusan:** sengaja **tidak** ditulis ulang. Menyusun analisis baru sampai
angkanya cocok dengan yang sudah dilaporkan mengubah verifikasi jadi pencarian —
persis yang dilarang README §2.7 no.2 dan no.6. Docstring `orderflow.py`, README
§7 dan §8 dikoreksi supaya jujur soal ini. Kalau R19–R21 mau dihidupkan lagi,
daftarkan dulu sebagai hipotesis di `HYPOTHESIS_REGISTER.md`.

### A4 — Referensi menggantung ⚠️ ditandai

`HYPOTHESIS_REGISTER.md` menunjuk `results/veb/HASIL_BACKTEST_VEB.md` dan
`PERBANDINGAN_H1_vs_VEB.md`. Keduanya **tidak ada di repo**, dan tidak ada kode
H2/VEB sama sekali di `src/`. Seluruh keluarga uji H2 — yang README §2.4 laporkan
dengan n=11.271 — tidak punya jejak yang bisa dieksekusi. H2 statusnya sudah
GAGAL/DITUTUP jadi ini tidak menghalangi apa pun, tapi kalau file-file itu ada di
disk lokal, sebaiknya di-commit.

---

## B. Bug perhitungan

### B1 — Koreksi funding yang diumumkan tapi tidak pernah masuk ke kode ❌ → ✅ diperbaiki

Commit `c1bb542` berjudul *"fix: stop loss membunuh H1 — koreksi akuntansi
funding"*. `git show --stat` pada commit itu:

```
 HYPOTHESIS_REGISTER.md | 45 +++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 45 insertions(+)
```

**Hanya markdown.** `src/portfolio.py` masih menghitung
`net_stop = ... - COST - funding_paid_48h`, yaitu mengkredit funding 48 jam PENUH
ke trade yang keluar di jam ke-2 karena kena stop. Karena ~71% edge H1 berasal
dari funding, semua baris ber-stop overstated. Dan `results/portfolio_sim.csv`
yang ter-commit masih menyimpan angkanya — $120,84 untuk Skema 2, yang README
§2.3 sendiri sebut **salah**, plus Skema 3b dengan CAGR +106%.

Ini melanggar aturan repo sendiri, README §2.7 no.5: *"Funding harus dihitung
sampai jam keluar sebenarnya, bukan sampai batas horizon."*

**Perbaikan:** Skema 2 dan 3b sudah DIBATALKAN, jadi barisnya **dibuang**, bukan
diperbaiki — menyusun ulang aproksimasinya sekarang = riset baru, bukan audit.
Kolom `net_stop` dihapus dari `portfolio.py`, kedua baris dihapus dari
`results/portfolio_sim.csv`. **Skema 1 dan 3 (H1 tanpa stop) memakai `net` dan
tidak tersentuh sama sekali.**

### B2 — Hit rate menghitung NaN sebagai kalah ❌ → ✅ diperbaiki

```python
"hit_rate_net": float(np.nanmean(net > 0))
```

`net > 0` menghasilkan array boolean — boolean tidak punya NaN. Baris yang
`net`-nya NaN (funding belum terbit di arsip; ~7,8% panel) menjadi `False`, jadi
terhitung KALAH, bukan dibuang. `np.nanmean` tidak menolong apa pun di sini.

Terukur pada panel uji: **0,4049 dilaporkan vs 0,4392 yang benar** — understated
3,4 poin persen. Ada di `ablation.py` (dua kali), `ablation_smc.py`,
`ablation_ext.py`.

**Perbaikan:** helper `_hit()` yang membuang NaN dulu. Rata-rata dan t-stat
**tidak terpengaruh** (`cluster_mean` memang sudah membuang NaN dengan benar) —
yang salah hanya kolom hit rate.

### B3 — `n_obs` / `n_days` melaporkan sampel yang salah ❌ → ✅ diperbaiki

`n_obs` dan `n_days` dihitung dari deret **gross**, sementara angka utama
(`mean_ret_net`, `t_stat_clustered`, CI) dihitung dari deret **net** yang lebih
pendek. Pada panel uji: 29.522 vs 27.216 — selisih 7,8%. `n_days` juga dipakai
sebagai penyaring di R8 (`n_days >= KEEP_MIN_NDAYS`), jadi ini bukan sekadar
kosmetik.

**Perbaikan:** kolom `n_obs_net` dan `n_days_net` ditambahkan berdampingan.
Kolom lama dibiarkan supaya file hasil lama tetap bisa dibandingkan.

### B4 — Gate menandai 4 symbol bisa ditradingkan padahal tidak ❌ → ✅ diperbaiki

`MIN_NOTIONAL_OVERRIDE` lama hanya berisi BTC dan ETH, dan nilai BTC-nya salah.
Menurut `exchangeInfo` asli, ada enam symbol dengan MIN_NOTIONAL > $5:

| symbol | MIN_NOTIONAL asli | di config lama | akibat |
|---|---:|---:|---|
| BTCUSDT | 50 | 100 | benchmark, di luar `eligible` — tidak berdampak |
| ETHUSDT | 20 | 20 | benar |
| BCHUSDT | 20 | *(tidak ada)* → 5 | **ditandai executable @ $6, padahal tidak bisa** |
| LTCUSDT | 20 | *(tidak ada)* → 5 | idem |
| ETCUSDT | 20 | *(tidak ada)* → 5 | idem |
| LINKUSDT | 20 | *(tidak ada)* → 5 | idem |

Keempat symbol terakhir bukan benchmark — mereka masuk universe H1 dan lolos
filter `executable_100usd == True` padahal notional $6 di bawah MIN_NOTIONAL
$20-nya. Order sebesar itu **ditolak bursa**, bukan sekadar tidak efisien.
Ditambah ALLUSDT yang `minQty`-nya 10 sementara `stepSize`-nya 1 — satu-satunya
pelanggaran `ASSUME_MINQTY_EQ_STEPSIZE` dari 658 symbol.

**Perbaikan:** `config.py` memakai nilai asli, plus `MIN_QTY_OVERRIDE` baru untuk
ALLUSDT; `panel.py` memakai keduanya. Diverifikasi: keenam symbol kini gagal
`exec_cond_a_min_notional`, ALLUSDT memakai `minQty = 10`.

> **`results/` SENGAJA TIDAK di-regenerate** (keputusan Anda). Angka H1 yang
> terkunci sebelum uji November tetap seperti apa adanya — H1 tidak di-refit dan
> tidak ada yang di-tuning. Koreksi gate ini baru berlaku saat pipeline
> dijalankan ulang. Sebelum uji ~1 November 2026, jalankan `features.py` →
> `panel.py` → seterusnya sekali supaya panelnya memakai gate yang benar. Efeknya
> kecil (4 dari ~752 symbol) tapi arahnya jelas: baris yang selama ini terhitung
> executable akan hilang.

### B5 — Logger bisa kehilangan data secara permanen ❌ → ✅ diperbaiki

`src/logger.py` menulis `_state.json` **sebelum** menulis parquet-nya. Kalau
`to_parquet` gagal (disk penuh, runner mati, pyarrow error) sementara state sudah
maju, baris jam-jam itu tidak akan pernah ditarik lagi — dan hilang permanen
begitu retensi Gate.io ~42 hari lewat. `oi_logs/` adalah satu-satunya salinan
data itu di dunia.

**Perbaikan:** urutannya dibalik — parquet dulu, state belakangan.

### B6 — Sensitivitas MIN_NOTIONAL mengabaikan override ❌ → ✅ diperbaiki

```python
df[f"executable_mn{int(mn)}"] = (mn <= C.NOTIONAL) & cond_b & ...
```

`(mn <= C.NOTIONAL)` adalah perbandingan **skalar**, jadi override per-symbol
diabaikan total dan BTC/ETH ikut lolos di `mn=5`. Kolomnya tidak dipakai di hilir
mana pun, tapi tetap output yang menyesatkan.

**Perbaikan:** `mn` kini menggantikan DEFAULT saja; symbol yang nilai aslinya
diketahui tetap memakai nilai aslinya.

### B7 — P&L trade terakhir dibuang diam-diam ❌ → ✅ diperbaiki

`portfolio.simulate()` menutup posisi hanya saat hari jatuh temponya muncul di
loop. Posisi yang dibuka di 1–2 hari terakhir tidak pernah ditutup, jadi P&L-nya
hilang dari ekuitas akhir **dan** dari daftar `trades`. Kecil (≈3 dari ~1.090
trade) tapi tetap salah.

**Perbaikan:** sisa posisi ditutup setelah loop selesai.

### B8 — `walkforward.py` bisa crash ❌ → ✅ diperbaiki

`pd.concat(allo)` melempar `ValueError` kalau tidak ada satu pun fold yang
menghasilkan baris OOS (mudah terjadi di universe kecil atau grid ketat). Sekarang
dijaga: laporan per-fold tetap ditulis, gabungan OOS dilewati dengan pesan jelas.

### B9 — Kode mati ❌ → ✅ dibersihkan

`gate_table.py` punya `... if False else ...` yang menyembunyikan satu ekspresi
yang tidak pernah dieksekusi, dan agregasi `lambda s: np.nan` yang seluruh
kolomnya langsung ditimpa beberapa baris kemudian.

---

## C. Operasional (GitHub Actions)

### C1 — Dependensi tanpa batas versi ❌ → ✅ diperbaiki

`pip install --quiet requests pandas pyarrow` — tanpa batas versi apa pun, di cron
yang menjaga data yang tidak bisa diambil ulang. Repo ini **sudah pernah** kena
rilis breaking sekali (README §4.4: bug grouping pandas 3.0 yang merusak seluruh
ranking cross-sectional dan sempat memberi hasil signifikan ke arah yang salah).

**Perbaikan:** install dari `requirements-logger.txt` yang berversi.

### C2 — Kegagalan ditelan diam-diam ❌ → ✅ diperbaiki

```bash
git pull --rebase --autostash origin main || true
git push origin HEAD:main
```

`|| true` membuang kegagalan rebase, dan push yang kalah balapan langsung
membuang data hari itu tanpa percobaan ulang.

**Perbaikan:** `set -euo pipefail`, push dengan 5 kali percobaan + rebase di
antaranya, dan `::error::` eksplisit kalau semuanya gagal. Ditambah step
**Verify output** yang membaca ulang parquet yang baru ditulis dan mencocokkan
jumlah barisnya dengan manifest sebelum di-commit — file korup yang ter-commit
lebih buruk daripada run yang gagal.

### C3 — Tidak ada notifikasi kegagalan ⚠️ rekomendasi, tidak diimplementasikan

Kalau cron mati, satu-satunya tanda adalah tab Actions yang tidak dilihat siapa
pun. 42 hari gagal berturut-turut = data hilang permanen. Sengaja **tidak** saya
tambahkan (butuh `permissions: issues: write` dan menambah permukaan kegagalan
baru) — tapi layak dipasang: step `if: failure()` yang membuka issue, atau
notifikasi bawaan GitHub untuk scheduled workflow yang gagal.

---

## D. Yang diperiksa dan ternyata BENAR

Supaya jelas apa yang tidak perlu dikhawatirkan:

* **Panel anti-lookahead.** Konvensi fitur dari bar closed pada `d` 00:00 UTC,
  entry di open bar `d` 00:00, label dari open bar 1H — konsisten di
  `features.py`, `smc.py`, `factors_ext.py`, `orderflow.py`, dan
  `hour_sensitivity.py`. Tidak ada satu pun bar setelah instan keputusan yang
  bocor ke sisi fitur.
* **Window funding tidak dobel-hitung.** Geser 1 mikrodetik di `features.py`
  membuat window fitur `(d-1 00:00, d 00:00]` dan window biaya hold
  `(d 00:00, d+H]` bersambung tanpa tumpang tindih maupun celah. Diverifikasi
  juga bahwa pandas 3.0 meng-upcast resolusi ms→us dengan benar untuk operasi ini
  (kalau ter-truncate jadi nol, window-nya akan bergeser diam-diam — tidak
  terjadi).
* **Funding tidak diam-diam dianggap nol.** Saat arsip funding berhenti sebelum
  akhir hold, `funding_paid_*h` diisi NaN, bukan 0. Ini benar dan penting.
* **SE cluster per tanggal.** `cluster_ols` mengimplementasikan koreksi
  finite-sample `G/(G-1) × (N-1)/(N-k)` dengan benar; bootstrap me-resample
  TANGGAL, bukan observasi, sehingga korelasi cross-section di dalam hari
  terjaga.
* **Perlakuan pandas 3.0.** `pd.factorize` dan `.values.astype("datetime64[D]")`
  dipakai di mana-mana; pola `astype("int64") // 10**9` yang berbahaya itu tidak
  tersisa satu pun.
* **Konvensi arah short.** `sign * fwd - cost - sign * fund` benar untuk kedua
  arah.
* **MAE/MFE.** Window `[entry, entry+H-1]` — tepat, sesuai entry di open dan exit
  di open bar ke-H.
* **`pine/stage1_1_replica.pine`.** Diperiksa terhadap kode Python: definisi state
  EMA identik, timing exit (`barsHeld >= holdBars - 1` → terisi di open bar ke-48)
  benar, `commission.percent` 0,10 per sisi = 0,20% pulang-pergi sesuai header.
  Tanda `fundingDrag` benar untuk long maupun short.
* **Integritas `oi_logs/`.** 1.203.033 baris, 991 kontrak, **nol duplikat**
  `(contract, time)`, deret per jam bersambung penuh sejak 2026-07-12. Hanya 4
  dari 991 kontrak punya jam bolong (5–15 jam, celah dari sumbernya). Mode
  inkremental via `_state.json` bekerja persis seperti yang dimaksud. Ini bagian
  paling sehat dari repo.
* **Tidak ada kredensial, tidak ada koneksi trading.** Dikonfirmasi ulang: tidak
  ada API key, tidak ada endpoint order, repository secrets kosong.

---

## E. Yang harus Anda lakukan

1. **Sebelum uji ~1 November 2026**, jalankan ulang pipeline sekali dengan gate
   yang sudah diperbaiki (B4). Urutannya ada di README §8 yang sudah dikoreksi.
   `results/` sengaja belum di-regenerate, jadi saat ini isinya masih keluaran
   kode lama.
2. **Pertimbangkan notifikasi kegagalan cron** (C3). Ini satu-satunya risiko
   kehilangan data permanen yang tersisa.
3. **Commit file H2/VEB kalau ada di disk lokal** (A4), atau hapus referensinya
   dari `HYPOTHESIS_REGISTER.md`.
4. **`fapi.binance.com` sekarang jalan dari mesin ini.** Kalau itu bertahan,
   `bookTicker` / `bookDepth` / metrics jadi terjangkau — tapi catat bahwa
   README §5 masih menyatakan sebaliknya, dan sifatnya bisa berubah kapan saja
   (blokir ISP / geo-restriction). Jangan tulis ulang §5 sebelum terbukti stabil
   beberapa hari.

## F. Yang TIDAK saya sentuh

Definisi H1, ambang mana pun, biaya, horizon, universe, kriteria KEEP, isi
`HYPOTHESIS_REGISTER.md`, seluruh angka hasil di `results/` selain dua baris
Skema 2/3b yang repo sendiri sudah nyatakan salah, dan seluruh klaim hasil di
README §1–§6 dan §9–§10.
