# Definisi Rasio (bahasa direksi)

Semua rasio dihitung `scripts/hitung_rasio.py` dengan saldo neraca **akhir periode**.
"Hari periode" = 365 untuk laporan tahunan. Untuk periode < 1 tahun, laba dan pendapatan disetahunkan untuk ROA,
ROE, dan perputaran aset.

| Rasio | Rumus | Arti sederhana | Arah yang lebih baik |
|---|---|---|---|
| Current ratio | Aset lancar / Liabilitas jangka pendek | Kemampuan membayar kewajiban < 1 tahun dengan aset lancar | Lebih tinggi (tetapi terlalu tinggi bisa berarti dana menganggur) |
| Quick ratio | (Aset lancar - Persediaan) / Liabilitas jangka pendek | Sama, tanpa mengandalkan stok terjual | Lebih tinggi |
| Margin laba kotor | Laba kotor / Pendapatan | Sisa dari tiap Rp100 penjualan setelah biaya produksi | Lebih tinggi |
| Margin laba usaha | Laba usaha / Pendapatan | Sisa setelah biaya produksi + biaya operasional | Lebih tinggi |
| Margin laba bersih | Laba bersih / Pendapatan | Sisa akhir untuk pemegang saham | Lebih tinggi |
| ROA | Laba bersih / Total aset | Seberapa produktif seluruh aset menghasilkan laba | Lebih tinggi |
| ROE | Laba bersih / Total ekuitas | Imbal hasil atas modal pemilik | Lebih tinggi |
| DER | Total liabilitas / Total ekuitas | Seberapa besar perusahaan dibiayai utang dibanding modal sendiri | Lebih rendah |
| Utang bank / ekuitas | (Utang bank pendek + panjang) / Ekuitas | Ketergantungan pada pinjaman berbunga | Lebih rendah |
| Interest coverage | Laba usaha / Beban bunga | Berapa kali laba usaha menutup bunga | Lebih tinggi |
| DIO | Persediaan / HPP × hari | Rata-rata hari barang (bahan, WIP, barang jadi) tersimpan sebelum terjual | Lebih rendah |
| DSO | Piutang usaha / Pendapatan × hari | Rata-rata hari pelanggan membayar | Lebih rendah |
| DPO | Utang usaha / HPP × hari | Rata-rata hari perusahaan membayar pemasok | Wajar & stabil (terlalu tinggi bisa merusak hubungan pemasok) |
| Cash conversion cycle | DIO + DSO - DPO | Berapa hari uang "tertahan" dari beli bahan sampai dibayar pelanggan | Lebih rendah |
| Perputaran aset | Pendapatan / Total aset | Penjualan yang dihasilkan tiap Rp1 aset | Lebih tinggi |
| Arus kas operasi / laba bersih | Arus kas operasi / Laba bersih | Berapa bagian laba yang benar-benar menjadi uang tunai | Sekitar ≥ 1 |
| Rasio kas | Kas / Liabilitas jangka pendek | Berapa kewajiban pendek yang bisa dibayar dengan kas saat ini | Lebih tinggi |
| Margin EBITDA | (Laba usaha + Penyusutan) / Pendapatan | Daya hasil kas operasi sebelum bunga, pajak, penyusutan | Lebih tinggi |
| Rasio beban usaha | Beban usaha / Pendapatan | Porsi penjualan yang habis untuk biaya penjualan & umum | Lebih rendah |
| Tarif pajak efektif | Beban pajak / Laba sebelum pajak | Pajak riil yang dibayar atas laba | Wajar (sekitar 22%) |
| Pengali ekuitas | Total aset / Ekuitas | Komponen DuPont: seberapa besar aset dibiayai utang | Wajar |
| Liabilitas / aset | Total liabilitas / Total aset | Porsi aset yang dibiayai utang | Lebih rendah |
| Utang bank bersih / EBITDA | (Utang bank − Kas) / EBITDA | Berapa tahun laba operasi untuk melunasi utang bank | Lebih rendah (umum < 2,5x) |
| Perputaran persediaan | HPP / Persediaan | Berapa kali stok berganti per tahun (= 365 ÷ DIO) | Lebih tinggi |
| Perputaran piutang | Pendapatan / Piutang | Berapa kali piutang tertagih per tahun (= 365 ÷ DSO) | Lebih tinggi |
| Margin arus kas bebas | (Arus kas operasi − Belanja modal) / Pendapatan | Uang tunai tersisa setelah investasi, per Rp100 penjualan | Lebih tinggi |
| Belanja modal / penyusutan | Belanja modal / Penyusutan | Di atas 1: aset diperbarui/ditambah; di bawah 1: aset menua | Wajar |
| Skor Altman Z'' | 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4 | Sinyal kesehatan perusahaan non-publik (X1 modal kerja/aset, X2 saldo laba/aset, X3 laba usaha/aset, X4 ekuitas/liabilitas) | > 2,60 aman; 1,10–2,60 abu-abu; < 1,10 rawan |

**DuPont:** ROE = margin laba bersih × perputaran aset × pengali ekuitas.

## Metode saldo: akhir vs rata-rata

| Metode | Kapan dipakai |
|---|---|
| Akhir periode (bawaan) | Memantau tren perusahaan sendiri; konsisten dengan laporan bulanan |
| Rata-rata awal & akhir (`--metode rata-rata`) | Membandingkan dengan angka yang dipublikasikan emiten/penyedia data |

Uji akurasi 7 emiten IDX (Nov 2026): rasio lancar, margin kotor, margin usaha, dan utang berbunga/ekuitas cocok
dengan angka publikasi; ROE, perputaran, dan rasio cepat berbeda karena definisi (rata-rata vs akhir, laba total vs
laba milik induk, komponen rasio cepat). Selalu sebut metode saat membandingkan.

Catatan: angka-angka ini bukan benchmark industri. Makna "tinggi" atau "rendah" tergantung industri, model bisnis,
dan musim. Bandingkan terutama dengan periode sebelumnya perusahaan itu sendiri.
