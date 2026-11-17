# Sumber Data: TradingView via TradingView-API

- Pustaka: `@mathieuc/tradingview` 4.1.2 (github.com/Mathieu2301/TradingView-API, lisensi ISC). Proyek komunitas,
  **tidak berafiliasi** dengan TradingView.
- Fungsi yang dipakai: `getScreener({ market: 'indonesia', columns, symbols | filter, sort, range })` — satu permintaan
  HTTP ke layanan screener TradingView, tanpa login.
- TradingView tidak menyediakan API data publik resmi; ketentuan layanannya membatasi pengambilan data otomatis.
  Pemakaian skill ini adalah keputusan pengguna. Gunakan secukupnya (bukan pengambilan massal berulang).

## Kolom yang dipakai

| Kelompok | Kolom TradingView |
|---|---|
| Profil | `name`, `description`, `sector`, `industry`, `currency`, `close`, `market_cap_basic` |
| Riwayat tahunan (indeks 0 = terbaru) | `total_revenue_fy_h`, `gross_profit_fy_h`, `net_income_fy_h`, `total_assets_fy_h`, `total_debt_fy_h`, `ebitda_fy_h`, `free_cash_flow_fy_h` |
| Tahun buku terakhir | `total_current_assets_fy`, `total_current_liabilities_fy`, `total_liabilities_fy`, `total_equity_fy`, `cash_n_short_term_invest_fy`, `oper_income_fy`, `cash_f_operating_activities_fy`, `capital_expenditures_fy`, `net_debt_fy`, `long_term_debt_fy`, `short_term_debt_fy` |
| Rasio jadi | `current_ratio_fy`, `quick_ratio_fy`, `debt_to_equity_fy`, `return_on_equity_fy`, `return_on_assets_fy`, `gross_margin_fy`, `operating_margin_fy`, `net_margin_fy`, `receivables_turnover_fy`, `asset_turnover_fy` |

Diuji 17 Nov 2026: kolom persediaan, piutang, utang usaha, HPP, beban bunga, laba sebelum pajak, dan pajak
**tidak tersedia** untuk saham IDX (bernilai kosong). Kolom dapat berubah sewaktu-waktu karena dikendalikan TradingView.

## Hasil uji akurasi (FY2024, 7 emiten: UNVR, ICBP, MYOR, SIDO, KLBF, AUTO, INTP)

Dibandingkan dengan data LK yang dipublikasikan ulang oleh penyedia data lain:

| Pos | Hasil |
|---|---|
| Pendapatan, laba bersih, total aset, total utang | Sama persis (selisih 0,00%) |
| Laba kotor | Lebih rendah 0,3%–4,3% (perbedaan klasifikasi biaya) |

Konsekuensi: margin laba kotor dari TradingView bisa sedikit lebih rendah daripada angka di LK resmi emiten.
