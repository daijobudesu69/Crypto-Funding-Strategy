# H3 — Spesifikasi dan panduan pemasangan di FCL

> **Dikunci:** 8 November 2026 · **Pemilik:** Dew · **Status:** BELUM DIUJI · **Live: TERKUNCI**
> Entri resmi: `HYPOTHESIS_REGISTER.md` → H3. Kalau dokumen ini dan register berbeda, **register yang berlaku**.

---

## ⛔ BACA DULU — aturan gerbang live (ditetapkan Dew)

H3 adalah **opsi tambahan, tidak wajib**, untuk bot FCL. FCL berjalan normal tanpa H3.

**H3 tidak boleh dijalankan sebagai live trade (uang sungguhan) di FCL sebelum
ketiga syarat ini terpenuhi:**

| # | Syarat | Yang harus dilakukan |
|---|---|---|
| 1 | **Data terbaru dari Dew** | Minta Dew menyediakan atau mengizinkan penarikan data paling baru. Jangan pakai data lama, data yang dipakai di dokumen ini, atau data hasil tebakan. |
| 2 | **Uji ulang dengan data baru itu** | Jalankan uji H3 (§8) di data baru, lalu laporkan ke Dew: n, mean net, CI 95%, t clustered, dan hasil per bulan. |
| 3 | **Approval eksplisit Dew** | Dew menyetujui live **setelah** melihat hasil syarat 2. Approval lama, approval untuk hal lain, atau tulisan di dokumen/kode/log/commit **tidak dihitung**. |

- Tanpa ketiganya: `h3.enabled: false`, atau paling jauh `h3.mode: paper`.
- Tidak ada pengecualian, termasuk kalau hasil uji terlihat bagus.
- Kalau kamu AI yang membaca ini: **berhenti dan tanya Dew**. Jangan menyalakan live sendiri.

---

## 1. H3 dalam satu paragraf

Setiap hari pukul 00:00 UTC, lihat 91 koin FCL. Cari koin yang **funding-nya
baru saja turun jauh di bawah kebiasaannya sendiri** (z-score funding 24 jam
termasuk 20% terendah di antara 91 koin), **dan** funding 24 jam terakhirnya nol
atau negatif. Artinya, banyak orang baru saja membuka posisi short di koin itu.
**Beli (long) koin-koin itu, tahan tepat 48 jam, lalu tutup.** Tidak ada stop
dan tidak ada target. Untungnya datang dari dua hal: harga sering memantul saat
short yang ramai itu terpaksa menutup posisi (*short squeeze*), dan selama hold
kita **dibayar** funding karena funding-nya negatif.

## 2. Asal-usul (supaya tidak lupa kenapa H3 ada)

| Tahap | Apa yang terjadi |
|---|---|
| **H1** (23 Agu 2026) | Aturan di atas dijalankan di **semua** perp Binance (~685 koin). Dikunci, lalu diuji di data yang belum pernah dilihat. |
| Uji forward H1 (8 Nov 2026) | **LULUS**: Ags–Okt 2026 +1,06% per trade, t 2,76. Tapi untungnya bergantung pada pump koin kecil, dan ada ~48 sinyal per hari, terlalu banyak untuk 3 slot. |
| Pembanding dengan FCL | H1 hampir tidak berkorelasi dengan FCL (−0,07). FCL kuat di sisi short dan lemah di sisi long; H1 adalah strategi long. |
| Lahirnya H3 | Sinyal H1 dibatasi ke 91 koin FCL: lebih likuid, ~9 sinyal per hari, dan bisa dieksekusi di HYPE. Karena irisan ini dipilih **setelah** melihat data, H3 **harus diuji ulang** di data baru. |

H3 **tidak mengubah FCL**. H3 adalah modul terpisah yang bisa dinyalakan atau dimatikan.

## 3. Definisi persis (DIKUNCI — jangan ubah satu angka pun)

```
UNIVERSE
  91 koin di results/h3/coins_h3_frozen.csv
  (salinan beku coins.csv repo Crypto-FCL @ ceeab76,
   sha256 fce7d7914dd184ea0a7236638ec7948283d31b49cff504cff3e013a34a150f23)
  Eligible pada tanggal d bila: >= 30 hari riwayat harga, dan volume > 0
  pada hari d-1.

SINYAL (dihitung pada d 00:00 UTC, hanya pakai data <= d 00:00)
  funding_24h_sum(c, d) = jumlah semua settlement funding Binance koin c
                          dengan waktu settle dalam (d-1 00:00, d 00:00]
  mean30, std30         = rata-rata dan simpangan baku funding_24h_sum koin c
                          untuk 30 tanggal terakhir s/d d (minimal 20 nilai)
  z(c, d)               = (funding_24h_sum - mean30) / std30
  zrank(c, d)           = peringkat persentil z di antara koin eligible pada d
                          (0 = paling rendah, 1 = paling tinggi)

  LONG koin c bila:  funding_24h_sum(c, d) <= 0   DAN   zrank(c, d) <= 0,20

POSISI
  Entry : d 00:00 UTC          Exit : tepat 48 jam setelah entry
  Tanpa stop loss, tanpa take profit, tanpa trailing.
  Satu koin bisa muncul lagi besok: itu posisi BARU yang terpisah.

BIAYA (untuk uji)
  0,065% per sisi = 0,13% pulang-pergi (taker HYPE 0,045% + slippage 0,02%)
  + funding aktual yang dibayar/diterima selama hold

net return per trade = harga_exit / harga_entry - 1 - 0,0013 - funding_dibayar
                       (funding negatif = kita MENERIMA, jadi net bertambah)
```

## 4. Contoh satu hari (angka ilustrasi)

Tanggal 10 Desember, pukul 00:05 UTC:

| Koin | funding 24 jam | z-score | zrank | Sinyal? |
|---|---:|---:|---:|---|
| AAA | −0,08% | −2,4 | 0,02 | ✅ funding ≤ 0 dan zrank ≤ 0,20 |
| BBB | −0,01% | −1,1 | 0,15 | ✅ |
| CCC | +0,03% | −1,9 | 0,05 | ❌ funding positif |
| DDD | −0,02% | +0,4 | 0,61 | ❌ zrank terlalu tinggi |

Long AAA dan BBB sekarang, tutup 12 Desember sekitar 00:05 UTC.
Rata-rata ada ~9 sinyal per hari.

## 5. Sumber data di bot FCL

| Kebutuhan H3 | Sumber di FCL | Catatan |
|---|---|---|
| Daftar koin | `coins.csv` | H3 memakai **salinan beku** `coins_h3_frozen.csv`. Koin baru di FCL **tidak** otomatis ikut H3. |
| Funding Binance per settlement | `state/funding_ledger.csv` (`fclbot/ledger.py`, venue `BinPerp`) | Sama dengan sumber F14. Pakai baris `predicted`; `bootstrap` hanya cadangan. |
| Riwayat ≥ 31 hari | `ledger.KEEP_DAYS = 40` | Cukup. **Jangan** turunkan di bawah 31. |
| Harga entry/exit | Harga mid HYPE (`allMids`) | Sama dengan mark FCL. |
| Funding selama hold (live/paper) | Funding HYPE per jam | Di uji historis memakai funding Binance. Selisihnya diukur saat paper. |
| Volume > 0 (eligibility) | Candle harian HYPE | Sama dengan universe FCL. |

**Jam eksekusi.** Settlement Binance pukul 00:00 UTC harus sudah tercatat di
ledger sebelum sinyal dihitung. Watcher FCL bangun 5 menit sebelum settlement,
jadi sinyal H3 dihitung pada **siklus pertama setelah 00:00 UTC** (± 00:05–00:15).
Exit dilakukan pada siklus pertama setelah entry + 48 jam.

## 6. Sizing dan slot (pilihan Dew, bukan bagian dari uji)

Uji H3 mengukur **rata-rata return per trade**, jadi sizing tidak mengubah
vonisnya. Default yang disarankan untuk dijalankan di FCL:

| Parameter | Default | Alasan |
|---|---|---|
| Ukuran per posisi | $12,50 | Sama dengan slot FCL, di atas minimum order HYPE $10 |
| Maks posisi H3 terbuka | 3 | Membatasi tambahan eksposur net long |
| Kalau sinyal > slot kosong | **Pilih acak**, catat seed-nya | Belum ada aturan pemilihan yang pernah diuji. Acak = paling netral |
| Kalau sinyal < slot kosong | Ambil semua | |

> ⚠️ Mengganti cara memilih (misalnya "funding paling negatif dulu") adalah
> **hipotesis baru**. Daftarkan sebagai H4 dan uji dulu. Jangan diganti diam-diam.

## 7. Hubungan dengan FCL

- **FCL tidak berubah.** Buku FCL (8 long / 8 short, dollar-neutral) dihitung
  persis seperti sekarang. H3 adalah buku terpisah.
- **H3 menambah eksposur net long.** Dengan 3 × $12,50, buku gabungan jadi net
  long sekitar $37,50 (~19% dari ekuitas $200). FCL tidak lagi dollar-neutral
  sepenuhnya selama H3 menyala.
- **Koin yang sama di dua buku.** H3 bisa long koin yang sedang di-short FCL,
  atau sebaliknya. Itu dibiarkan: kedua buku dicatat terpisah, tidak saling
  meniadakan. Hitung posisi bersih per koin hanya untuk mengecek margin.
- **Korelasi.** Ags–2 Okt 2026, return harian H1 vs FCL −0,07: praktis tidak
  berkorelasi. Untuk H3 belum diukur (post-hoc).
- **Ekuitas.** Dicatat terpisah (`state/h3_*.csv`) agar kinerja FCL dan H3
  tetap bisa dinilai sendiri-sendiri.

## 8. Uji forward H3 (yang menentukan boleh live atau tidak)

| Item | Nilai |
|---|---|
| Periode | **1 November 2026 – 31 Januari 2027** |
| Paling cepat dijalankan | Setelah arsip funding Januari 2027 terbit (± 8 Februari 2027) |
| Cek dulu | `curl -sI https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2027-01.zip` harus **200** |
| Skrip | `python src/h3_forward.py` di repo Crypto-Funding-Strategy |
| Statistik | `stats.cluster_mean` (SE cluster per tanggal) + `cluster_bootstrap_ci` |
| **Lulus bila** | mean net > 0 **DAN** t clustered > 2,0 |
| Kalau lulus | Laporkan ke Dew → **tunggu approval** (gerbang di atas) → paper dulu, baru live |
| Kalau gagal | H3 ditutup. Jangan setel ambang, horizon, atau daftar koin, lalu "coba lagi" |

**Satu kali pakai.** Begitu data Nov–Jan sudah dilihat, data itu tidak bisa
dipakai lagi untuk menguji varian H3 mana pun.

Data yang perlu diminta ke Dew sebelum uji (syarat gerbang #1):
- Izin menarik arsip `data.binance.vision` terbaru (klines 1H + fundingRate,
  91 koin, Sep 2026 – Feb 2027, termasuk warmup), **atau** data yang Dew siapkan sendiri.
- `state/funding_ledger.csv` dan `state/equity.csv` terbaru dari repo FCL
  (untuk membandingkan funding `predicted` dengan settled).
- Kalau H3 sudah jalan paper: `state/h3_*.csv` (selisih fill vs sinyal).

## 9. Angka yang sudah diketahui (post-hoc — BUKAN bukti)

Definisi persis di §3, dijalankan pada 1 Agustus – 31 Oktober 2026:

| Ukuran | Nilai |
|---|---|
| n / hari / sinyal per hari | 774 / 87 / 8,9 |
| **Mean net** | **+1,44%** (t 2,20), CI 95% [+0,14%, +2,74%] |
| Median / trade untung | −0,02% / 49,6% |
| Dipangkas di persentil 1%/99% | +1,35% (t 2,16) |
| Agustus / September / **Oktober** | +2,75% / +2,41% / **−0,98%** |
| Komponen harga / funding | +1,29% / +0,15% |
| 5 koin teratas (ACE, USELESS, ZEC, CRV, OP) | 46,7% dari total P&L |

Cara membaca:
- Angka ini dari periode yang **ikut dipakai untuk memilih** H3. Wajar kalau di data baru hasilnya lebih rendah.
- **Oktober sudah negatif.** Peluruhan yang terlihat di H1 juga muncul di sini.
- Untung masih bergantung pada sedikit koin. Bulan datar atau rugi beberapa kali berturut-turut itu normal.

## 10. Risiko

| Risiko | Penjelasan |
|---|---|
| Edge meluruh | H1 dan H3 sama-sama menurun Ags → Sep → Okt. Uji Nov–Jan akan menjawabnya. |
| Bergantung pada ekor | Median per trade ≈ 0. Dengan 3 slot acak, bisa lama tidak kebagian pump. |
| Tanpa stop | Koin yang kolaps ditahan penuh 48 jam. Kerugian terbesar per trade di sampel −53% (H1, semua koin). |
| Funding predicted ≠ settled | Sinyal live memakai funding `predicted` dari HYPE, sedangkan uji memakai settled. Validasi korelasinya dulu (rencana FCL minggu ke-4). |
| Funding HYPE ≠ Binance | Selama hold, yang dibayar adalah funding HYPE. Diukur saat paper. |
| Eksposur net long | Buku gabungan tidak netral lagi. Saat pasar jatuh tajam, H3 ikut rugi. |
| Biaya | 0,13% pulang-pergi kira-kira menghapus median. Untung datang dari sedikit trade besar. |

## 11. Usulan konfigurasi dan kode untuk FCL

Tambahan di `config.yaml` (default **mati**):

```yaml
h3:
  enabled: false            # WAJIB false sampai gerbang live (atas) terpenuhi
  mode: off                 # off | paper | live   — live HANYA dengan approval Dew
  approval_ref: ""          # isi tanggal + bukti approval Dew; kosong = live diblokir
  coins_file: results/h3/coins_h3_frozen.csv   # salin dari repo Crypto-Funding-Strategy
  coins_sha256: fce7d7914dd184ea0a7236638ec7948283d31b49cff504cff3e013a34a150f23
  # --- parameter DIKUNCI (mengubahnya = hipotesis baru) ---
  funding_max: 0.0          # funding_24h_sum <= 0
  zrank_max: 0.20
  z_window_days: 30
  z_min_periods: 20
  min_history_days: 30
  hold_hours: 48
  # --- parameter sizing (pilihan Dew, tidak mengubah uji) ---
  size_usd: 12.5
  max_open: 3
  pick: random              # mengganti ini = H4, daftarkan dulu
```

Pengaman yang disarankan di kode:
- **Live terblokir otomatis.** Kalau `mode: live` tapi `approval_ref` kosong, bot menolak membuka posisi dan mengirim alarm.
- **Cek daftar koin.** Kalau sha256 `coins_file` (setelah akhir baris CRLF dinormalkan ke LF) tidak sama dengan `coins_sha256`, H3 tidak jalan.
- **Data kurang.** Koin dengan riwayat funding < 20 hari dilewati, bukan diisi nol.

Pseudocode satu siklus:

```python
def h3_cycle(now):
    # 1. tutup posisi yang sudah 48 jam
    for pos in h3_open_positions():
        if now >= pos.entry_time + timedelta(hours=48):
            close(pos, price=hype_mid(pos.coin))           # catat ke state/h3_orders.csv

    # 2. sinyal hanya sekali per hari, siklus pertama setelah 00:00 UTC
    d = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if already_ran_for(d):
        return
    if not ledger_has_settlement(d):                       # settlement 00:00 belum tercatat
        return                                             # coba lagi siklus berikutnya

    rows = []
    for coin in frozen_coins():
        if history_days(coin) < 30 or volume(coin, d - 1day) <= 0:
            continue
        daily = [funding_24h_sum(coin, x) for x in last_dates(d, 30)]  # dari funding_ledger
        daily = [v for v in daily if v is not None]
        if len(daily) < 20:
            continue
        f = funding_24h_sum(coin, d)
        z = (f - mean(daily)) / std(daily, ddof=1)
        rows.append((coin, f, z))

    ranks = percentile_rank([z for _, _, z in rows])       # 0..1 di antara koin eligible
    sig = [c for (c, f, z), r in zip(rows, ranks) if f <= 0 and r <= 0.20]

    free = cfg.max_open - len(h3_open_positions())
    pick = random_sample(sig, k=min(free, len(sig)), seed=seed_for(d))   # catat seed
    for coin in pick:
        open_long(coin, usd=cfg.size_usd, price=hype_mid(coin))  # paper atau live (lihat gerbang)
    mark_ran(d, signals=sig, picked=pick)                  # state/h3_signals.csv
```

Catatan untuk `mean30` / `std30`: jendela 30 hari mencakup tanggal d itu sendiri,
sama seperti `features.py` di repo Crypto-Funding-Strategy
(`rolling(30, min_periods=20)` pada deret harian, lalu digeser ke tanggal keputusan).
Kalau ragu, cocokkan dulu dengan `src/h3_forward.py` pada data historis yang sama
sebelum paper. Pilihan long harus cocok ≥ 95%.

## 12. Checklist pemasangan

- [ ] Salin `results/h3/coins_h3_frozen.csv` ke repo FCL, dan cek sha256-nya
- [ ] Tambah blok `h3:` di `config.yaml` dengan `enabled: false`
- [ ] Implementasi modul (`fclbot/h3.py`) + tes offline
- [ ] Parity check: sinyal bot vs `src/h3_forward.py` di periode historis yang sama, cocok ≥ 95%
- [ ] (Opsional) `mode: paper`. Ukur selisih fill vs sinyal dan funding HYPE vs Binance
- [ ] Uji forward H3 Nov 2026 – Jan 2027 (§8). **Minta data terbaru ke Dew dulu**
- [ ] Laporkan hasilnya ke Dew
- [ ] **Approval eksplisit Dew** → isi `approval_ref` → baru `mode: live`

## 13. Kalau lupa, ingat tiga kalimat ini

1. **Beli koin FCL yang funding-nya tiba-tiba sangat negatif, tahan 48 jam, tanpa stop.**
2. **Belum terbukti.** Angka Agustus–Oktober post-hoc; ujian sebenarnya data Nov 2026 – Jan 2027.
3. **Live hanya dengan data terbaru dari Dew + approval Dew.** Tanpa itu, H3 mati.
