#!/usr/bin/env node
// Ambil data emiten IDX (perusahaan Tbk) dari TradingView lewat pustaka TradingView-API (Mathieu2301, tidak resmi).
//
// Persiapan (sekali):  cd scripts && npm install          (butuh Node.js >= 20 dan akses internet)
//
// Pemakaian:
//   node scripts/tv_emiten.mjs sektor                                  daftar sektor + jumlah emiten
//   node scripts/tv_emiten.mjs daftar --sektor "Consumer Non-Durables" --limit 20
//   node scripts/tv_emiten.mjs daftar --cari garmen                    cari nama/kode emiten
//   node scripts/tv_emiten.mjs ambil UNVR ICBP MYOR --out emiten.json  ambil data fundamental
//
// PERHATIAN: TradingView tidak menyediakan API data publik resmi. Pustaka ini memakai endpoint tidak resmi; data bisa
// tertunda, berbeda dengan laporan keuangan resmi, atau berhenti tersedia. Gunakan secara wajar dan verifikasi angka
// penting ke laporan keuangan resmi (idx.co.id / situs emiten) sebelum dipakai mengambil keputusan.
import { getScreener } from '@mathieuc/tradingview';
import { writeFileSync } from 'node:fs';

const KOLOM_PROFIL = ['name', 'description', 'sector', 'industry', 'currency', 'fundamental_currency_code', 'close', 'market_cap_basic'];
const KOLOM_RIWAYAT = ['total_revenue_fy_h', 'gross_profit_fy_h', 'net_income_fy_h', 'total_assets_fy_h', 'total_debt_fy_h',
  'ebitda_fy_h', 'free_cash_flow_fy_h'];
const KOLOM_TERAKHIR = ['total_current_assets_fy', 'total_current_liabilities_fy', 'total_liabilities_fy', 'total_equity_fy',
  'cash_n_short_term_invest_fy', 'oper_income_fy', 'cash_f_operating_activities_fy', 'capital_expenditures_fy', 'net_debt_fy',
  'long_term_debt_fy', 'short_term_debt_fy', 'current_ratio_fy', 'quick_ratio_fy', 'debt_to_equity_fy', 'return_on_equity_fy',
  'return_on_assets_fy', 'gross_margin_fy', 'operating_margin_fy', 'net_margin_fy', 'receivables_turnover_fy',
  'asset_turnover_fy', 'earnings_per_share_basic_fy'];

// kata kunci Indonesia -> istilah industri TradingView (Inggris)
const SINONIM = {
  tekstil: ['textile', 'apparel'], garmen: ['apparel', 'textile'], pakaian: ['apparel'], makanan: ['food'],
  minuman: ['beverages'], farmasi: ['pharmaceutical'], obat: ['pharmaceutical'], semen: ['construction materials'],
  otomotif: ['auto', 'motor vehicles'], komponen: ['auto parts'], logam: ['metal', 'steel'], baja: ['steel'],
  kimia: ['chemicals'], kertas: ['pulp', 'paper'], plastik: ['containers/packaging', 'plastic'], kemasan: ['packaging'],
  distribusi: ['wholesale', 'distributors'], distributor: ['wholesale', 'distributors'], ritel: ['retail'],
  rokok: ['tobacco'], kosmetik: ['household/personal care'], elektronik: ['electronic'], mesin: ['industrial machinery'],
};
const tidur = (ms) => new Promise((r) => setTimeout(r, ms));
async function screener(query, coba = 3) {
  let galat;
  for (let i = 0; i < coba; i++) {
    try { return await getScreener({ market: 'indonesia', ...query }); }
    catch (e) { galat = e; await tidur(2000 * (i + 1)); }
  }
  throw new Error(`Gagal menghubungi TradingView setelah ${coba} percobaan: ${galat?.message}. Periksa koneksi internet ` +
    `atau coba lagi nanti. (Lingkungan AI tanpa akses internet tidak bisa memakai skill ini.)`);
}

function argumen(argv) {
  const opsi = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) { opsi[argv[i].slice(2)] = argv[i + 1]; i++; } else opsi._.push(argv[i]);
  }
  return opsi;
}
const filterSaham = [{ left: 'type', operation: 'equal', right: 'stock' }];
const rupiah = (v) => v == null ? '-' : (Math.abs(v) >= 1e12 ? (v / 1e12).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + ' T'
  : (v / 1e9).toLocaleString('id-ID', { maximumFractionDigits: 0 }) + ' M');

async function semuaEmiten() {
  const r = await screener({ columns: ['name', 'description', 'sector', 'industry', 'market_cap_basic'], filter: filterSaham,
    sort: { sortBy: 'market_cap_basic', sortOrder: 'desc' }, range: [0, 3000] });
  return r.rows.map((x) => ({ kode: x.values.name, nama: x.values.description, sektor: x.values.sector,
    industri: x.values.industry, kapitalisasi: x.values.market_cap_basic }));
}

async function main() {
  const [perintah, ...sisa] = process.argv.slice(2);
  const o = argumen(sisa);
  if (perintah === 'sektor') {
    const semua = await semuaEmiten();
    const hit = {};
    semua.forEach((e) => { hit[e.sektor] = (hit[e.sektor] || 0) + 1; });
    console.log(`Total ${semua.length} saham IDX (sumber: TradingView, tidak resmi)\n`);
    Object.entries(hit).sort((a, b) => b[1] - a[1]).forEach(([s, n]) => console.log(`${String(n).padStart(4)}  ${s}`));
    return;
  }
  if (perintah === 'daftar') {
    let semua = await semuaEmiten();
    if (o.sektor) semua = semua.filter((e) => (e.sektor || '').toLowerCase() === o.sektor.toLowerCase());
    if (o.industri) semua = semua.filter((e) => (e.industri || '').toLowerCase().includes(o.industri.toLowerCase()));
    if (o.cari) {
      const k = o.cari.toLowerCase();
      const padanan = (SINONIM[k] || []).concat([k]);
      semua = semua.filter((e) => padanan.some((w) => [e.kode, e.nama, e.industri, e.sektor]
        .some((f) => (f || '').toLowerCase().includes(w))));
    }
    const n = Number(o.limit || 25);
    console.log(`| No | Kode | Nama | Industri | Kapitalisasi pasar |\n|---:|---|---|---|---:|`);
    semua.slice(0, n).forEach((e, i) => console.log(`| ${i + 1} | ${e.kode} | ${e.nama} | ${e.industri || '-'} | Rp${rupiah(e.kapitalisasi)} |`));
    console.log(`\n${Math.min(n, semua.length)} dari ${semua.length} emiten ditampilkan (urut kapitalisasi pasar). Sumber: TradingView (tidak resmi).`);
    if (o.json) writeFileSync(o.json, JSON.stringify(semua, null, 1));
    return;
  }
  if (perintah === 'ambil') {
    const kode = o._.map((k) => k.toUpperCase().replace(/^IDX:/, ''));
    if (!kode.length) throw new Error('Sebutkan kode emiten, mis. ambil UNVR ICBP');
    if (kode.length > 15) throw new Error('Maksimal 15 emiten per permintaan.');
    const kolom = [...new Set([...KOLOM_PROFIL, ...KOLOM_RIWAYAT, ...KOLOM_TERAKHIR])];
    const r = await screener({ columns: kolom, symbols: kode.map((k) => 'IDX:' + k), range: [0, kode.length] });
    const emiten = {};
    r.rows.forEach((x) => { emiten[x.values.name] = { simbol: x.symbol, ...x.values }; });
    const hilang = kode.filter((k) => !emiten[k]);
    const hasil = {
      sumber: 'TradingView melalui TradingView-API (github.com/Mathieu2301/TradingView-API) — sumber TIDAK RESMI',
      catatan: 'Nilai uang dalam Rupiah penuh. *_fy = tahun buku terakhir yang tersedia; *_fy_h = riwayat tahunan, indeks 0 = terbaru.',
      diambil: new Date().toISOString(),
      emiten,
      tidak_ditemukan: hilang,
    };
    const out = o.out || 'emiten.json';
    writeFileSync(out, JSON.stringify(hasil, null, 1));
    console.log(`Data ${Object.keys(emiten).length} emiten ditulis ke ${out}.` + (hilang.length ? ` Tidak ditemukan: ${hilang.join(', ')}` : ''));
    console.log('Ringkas dengan: python scripts/ringkas_emiten.py ' + out);
    return;
  }
  console.log('Perintah: sektor | daftar [--sektor S] [--industri I] [--cari kata] [--limit N] | ambil KODE... [--out f.json]');
  process.exitCode = 1;
}

main().catch((e) => { console.error('GAGAL:', e.message); process.exitCode = 1; });
