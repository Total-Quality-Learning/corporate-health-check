# Struktur Laporan

| Tab | Isi | Butuh data operasional? |
|---|---|---|
| Ringkasan | 3 angka besar + tren 12 bulan, lampu status 15 indikator & skor, 3 hal yang perlu diketahui (cerita atau checklist), usulan keputusan, catatan direksi (opsional `--narasi`) | Penyebab: ya (jika tidak ada → Perlu data) |
| Kesehatan | 15 indikator berbahasa awam, dikelompokkan (untung, tumbuh, kas & modal kerja, kemampuan bayar, utang), "Apa artinya?" | - |
| Arus kas | Jembatan laba → uang tunai + penjelasan, perkiraan kas 13 minggu, skenario "bagaimana jika", risiko | - |
| Tren | 4 grafik 22 bulan, pos utama per bulan, DuPont per bulan | - |
| Laporan keuangan | Perubahan terbesar, laba rugi, posisi keuangan, arus kas vs pembanding | Target: sheet Target |
| Operasional | Piutang per pelanggan, produk & margin, umur stok, pemasok, kinerja pabrik/gudang, per lini | **Ya** |
| Rumus & data | sekitar 35 rasio dengan rumus & perhitungan, pemeriksaan data G1-G8, kelengkapan, kamus, metode | - |

Prinsip desain: `prinsip-desain-laporan.md`.

## Cerita utama (aturan pemilihan)

Kandidat dihitung dari YTD vs YTD tahun lalu, lalu diurutkan kritis → waspada → kabar baik:

| Cerita | Pemicu |
|---|---|
| Laba belum menjadi kas | Laba positif dan konversi kas < 75% |
| Piutang semakin lama tertagih | DSO naik ≥ 10 hari YoY |
| Persediaan menumpuk | DIO naik ≥ 10 hari YoY |
| Margin kotor tergerus | Margin kotor turun ≥ 1 poin YoY |
| Beban usaha tumbuh lebih cepat | Pertumbuhan beban usaha - pertumbuhan pendapatan ≥ 5 poin |
| Beban utang membatasi ruang gerak | ICR < 3x, utang bersih/EBITDA > 2,5x, atau utang bank naik ≥ 25% |
| Ketergantungan pada sedikit pelanggan | 3 pelanggan terbesar ≥ 40% omzet (butuh data pelanggan) |
| Penjualan tumbuh | Pendapatan naik ≥ 3% YoY |

## Gerbang validasi

G1 neraca seimbang (gagal → laporan tidak disusun) | G2 bulan lengkap | G3 kas arus kas = kas neraca , 
G4 rekonsiliasi kas | G5 laba bersih dihitung ulang | G6 saldo laba konsisten | G7 target tersedia , 
G8 data operasional tersedia.
