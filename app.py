import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Sistem Data Perawatan GD & B", page_icon="🚆", layout="wide")

# ===== TAMPILAN BARU - LEBIH MENARIK =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
* {font-family: 'Plus Jakarta Sans', sans-serif !important;}
.stApp {background:#eef2f7;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#0f2a4d 0%,#123b68 60%,#176a9a 100%);}
[data-testid="stSidebar"] * {color:white !important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:10px;margin-bottom:6px;border:1px solid rgba(255,255,255,0.12);}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:rgba(255,255,255,0.18);}

.main-title {background:linear-gradient(110deg,#0f2a4d,#123b68 45%,#f28c28 130%);padding:24px 26px;border-radius:18px;color:white;margin-bottom:20px;box-shadow:0 10px 25px rgba(15,42,77,0.25);display:flex;align-items:center;gap:16px}
.main-title h1 {color:white;margin:0;font-size:30px;font-weight:800;letter-spacing:-0.5px;line-height:1.1}
.main-title p {color:#dbeafe;margin:8px 0 0 0;font-size:14px}
.main-title .icon {font-size:48px;background:rgba(255,255,255,0.15);width:72px;height:72px;border-radius:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0}

div[data-testid="stMetric"] {background:white;padding:16px;border-radius:16px;box-shadow:0 4px 14px rgba(0,0,0,0.06);border:1px solid #e5e9f0;}
div[data-testid="stMetric"] label {color:#64748b !important;font-weight:600;}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {color:#0f2a4d !important;font-weight:800;}

div.stButton>button[kind="primary"] {background:linear-gradient(90deg,#f28c28,#ff9d3c);border:none;color:white;font-weight:800;padding:14px;border-radius:12px;box-shadow:0 6px 18px rgba(242,140,40,0.35);font-size:16px;}
div.stButton>button[kind="primary"]:hover {transform:translateY(-1px);box-shadow:0 8px 22px rgba(242,140,40,0.45);}
div[data-testid="stForm"] {background:white;padding:24px;border-radius:18px;box-shadow:0 6px 20px rgba(0,0,0,0.06);border:1px solid #e8edf3;}
div[data-testid="stExpander"] {background:white;border-radius:14px !important;border:1px solid #e8edf3 !important;}
input, select, textarea {border-radius:10px !important;}
h3 {color:#0f2a4d !important;background:#fff7ed;padding:10px 14px;border-radius:10px;border-left:5px solid #f28c28;font-size:17px !important;}
</style>
""", unsafe_allow_html=True)

SHEET_HEADERS = [
    "ID", "Tanggal Perawatan", "Jenis Sarana", "Nomor Sarana", "Jenis Perawatan",
    "Depo/Lokasi", "Dipo Induk", "Nama Petugas", "NIPP",
    "Foto Sebelum", "Foto Sesudah", "Keterangan", "Waktu Input",
    "Mulai Dinas", "Siklus Perawatan", "Nomor Bogie 1", "Nomor Bogie 2",
    "Ukuran Roda", "Diameter B1 R1", "Diameter B1 R2", "Diameter B1 R3", "Diameter B1 R4",
    "Diameter B2 R1", "Diameter B2 R2", "Diameter B2 R3", "Diameter B2 R4",
    "Flens B1 R1", "Flens B1 R2", "Flens B1 R3", "Flens B1 R4",
    "Flens B2 R1", "Flens B2 R2", "Flens B2 R3", "Flens B2 R4",
    "Bidang Jalan B1 R1", "Bidang Jalan B1 R2", "Bidang Jalan B1 R3", "Bidang Jalan B1 R4",
    "Bidang Jalan B2 R1", "Bidang Jalan B2 R2", "Bidang Jalan B2 R3", "Bidang Jalan B2 R4",
    "Keausan Knuckle Bogie 1", "Keausan Knuckle Bogie 2", "Kelengkapan Emptyload",
    "Tinggi Boffer", "Brake", "Release", "Langkah Torak", "AC", "CD", "Tekanan BC",
    "Lain-lain", "Status SO/TSO"
]
SHEET_NAME = "Data Perawatan"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]

def get_config():
    if "gcp_service_account" not in st.secrets:
        st.error("Konfigurasi Google belum ditemukan.")
        st.stop()
    return st.secrets

@st.cache_resource
def connect_google():
    cfg = get_config()
    credentials = Credentials.from_service_account_info(dict(cfg["gcp_service_account"]), scopes=SCOPES)
    gc = gspread.authorize(credentials)
    spreadsheet_id = cfg.get("spreadsheet_id", "")
    if not spreadsheet_id:
        st.error("Isi spreadsheet_id pada secrets.toml.")
        st.stop()
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
    existing_headers = ws.row_values(1)
    if not existing_headers:
        ws.resize(cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
    else:
        missing_headers = [h for h in SHEET_HEADERS if h not in existing_headers]
        if missing_headers:
            updated_headers = existing_headers + missing_headers
            ws.resize(cols=max(len(updated_headers), ws.col_count))
            ws.update(range_name=f'A1:{gspread.utils.rowcol_to_a1(1, len(updated_headers))}', values=[updated_headers])
    drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
    return sh, ws, drive, cfg

def upload_photo(drive, uploaded_file, folder_id, filename, make_public=False):
    if uploaded_file is None: return ""
    metadata = {"name": filename}
    if folder_id: metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type or "application/octet-stream", resumable=True)
    result = drive.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    if make_public:
        drive.permissions().create(fileId=result["id"], body={"type":"anyone","role":"reader"}, fields="id").execute()
    return result.get("webViewLink", f"https://drive.google.com/file/d/{result['id']}/view")

@st.cache_data(ttl=60)
def load_records(_ws):
    values = _ws.get_all_records()
    if not values: return pd.DataFrame(columns=SHEET_HEADERS)
    df = pd.DataFrame(values)
    for col in SHEET_HEADERS:
        if col not in df.columns: df[col] = ""
    return df[SHEET_HEADERS]

def make_id(): return datetime.now().strftime("PRW%Y%m%d%H%M%S%f")
def add_record(ws, record):
    ws.append_row([record.get(h, "") for h in SHEET_HEADERS], value_input_option="USER_ENTERED")
    st.cache_data.clear()

st.markdown("""
<div class="main-title">
<div class="icon">🚆</div>
<div><h1>SISTEM DATA PERAWATAN SARANA</h1><p>GD &nbsp;•&nbsp; GB &nbsp;•&nbsp; B &nbsp;•&nbsp; Database Google Spreadsheet &nbsp;•&nbsp; Realtime</p></div>
</div>
""", unsafe_allow_html=True)

try:
    sh, ws, drive, cfg = connect_google()
except Exception as e:
    st.error(f"Gagal terhubung ke Google: {e}")
    st.stop()

folder_id = str(cfg.get("drive_folder_id", "")).strip()
make_public = bool(cfg.get("share_photos_publicly", False))
df = load_records(ws)

with st.sidebar:
    st.markdown("### 🚆 MENU APLIKASI")
    st.caption("Pencatatan pemeriksaan & pemeliharaan sarana")
    page = st.radio("Pilih menu", ["📊 Dashboard", "📝 Input Perawatan", "📚 Riwayat Perawatan", "📄 Laporan Otomatis"], label_visibility="collapsed")
    page = page.replace("📊 ","").replace("📝 ","").replace("📚 ","").replace("📄 ","")
    st.divider()
    st.caption("KAI • Dipo Induk • Versi Terbaru")
    st.success("✅ Terhubung ke Google Sheet")

if page == "Dashboard":
    st.subheader("📊 Dashboard Perawatan")
    total = len(df)
    gd_count = int((df["Jenis Sarana"].astype(str).isin(["GD","GB"])).sum()) if total else 0
    b_count = int((df["Jenis Sarana"].astype(str) == "B").sum()) if total else 0
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Data Perawatan", f"{total:,}")
    c2.metric("Gerbong (GD / GB)", f"{gd_count:,}")
    c3.metric("Bagasi (B)", f"{b_count:,}")
    st.divider()
    if total:
        recent = df.sort_values("Waktu Input", ascending=False).head(10)
        st.markdown("#### 🕒 10 Data Terakhir")
        st.dataframe(recent, use_container_width=True, hide_index=True)
        by_type = df["Jenis Perawatan"].replace("", "Tidak diisi").value_counts()
        st.markdown("#### 📈 Data berdasarkan jenis perawatan")
        st.bar_chart(by_type)
    else:
        st.info("Belum ada data perawatan. Silakan masukkan data melalui menu Input Perawatan.")

elif page == "Input Perawatan":
    st.subheader("📝 Form Input Pemeriksaan & Pemeliharaan Sarana")
    with st.form("form_perawatan", clear_on_submit=True):
        st.markdown("### 1. Identitas Sarana")
        a,b = st.columns(2)
        with a: jenis_sarana = st.selectbox("Jenis sarana", ["GD", "GB", "B", "Lainnya"])
        with b: nomor = st.text_input("Nomor sarana", placeholder="Contoh: 421005")
        c,d,e = st.columns(3)
        with c: mulai_dinas = st.date_input("Mulai dinas", value=date.today())
        with d: siklus = st.date_input("P24 / P48", value=date.today(), help="Diisi pake tanggal P24 / P48")
        with e: tanggal = st.date_input("Tanggal pemeriksaan / pemeliharaan", value=date.today())
        f,g = st.columns(2)
        with f: jenis_perawatan = st.selectbox("Program pemeliharaan", ["P1", "P3", "P6", "P12", "Perbaikan"])
        with g: dipo_induk = st.text_input("Dipo Induk", placeholder="Kosongkan / isi Dipo Induk...")

        st.markdown("### 2. Identitas Bogie")
        b1,b2 = st.columns(2)
        with b1: no_bogie1 = st.text_input("Nomor Bogie 1")
        with b2: no_bogie2 = st.text_input("Nomor Bogie 2")

        st.markdown("### 3. Pengukuran Roda")
        uk1, uk2 = st.columns([4,1])
        with uk1: ukuran_roda = st.text_input("Ukuran roda", placeholder="Contoh: 798")
        with uk2: st.markdown("<div style='padding-top:28px; font-weight:bold;'>mm</div>", unsafe_allow_html=True)
        diameter = {1: [], 2: []}
        flens = {1: [], 2: []}
        bidang = {1: [], 2: []}
        for bogie in [1, 2]:
            st.markdown(f"#### 🛞 BOGIE {bogie}")
            h0,h1,h2,h3 = st.columns([1,2,2,2])
            with h0: st.caption("RODA")
            with h1: st.caption("Keausan Flens")
            with h2: st.caption("Tinggi Flens")
            with h3: st.caption("Diameter")
            for roda in range(1,5):
                c0,c1,c2,c3 = st.columns([1,2,2,2])
                with c0: st.markdown(f"**Roda {roda}**")
                with c1:
                    v1 = st.text_input(f"Keausan B{bogie} R{roda}", key=f"keausan_b{bogie}_r{roda}_v4", label_visibility="collapsed", placeholder="0.0")
                    flens[bogie].append(v1)
                with c2:
                    v2 = st.text_input(f"Tinggi B{bogie} R{roda}", key=f"tinggi_b{bogie}_r{roda}_v4", label_visibility="collapsed", placeholder="0.0")
                    bidang[bogie].append(v2)
                with c3:
                    v3 = st.text_input(f"Diameter B{bogie} R{roda}", key=f"diam_b{bogie}_r{roda}_v4", label_visibility="collapsed", placeholder="0")
                    diameter[bogie].append(v3)

        st.markdown("### 4. Pemeriksaan Komponen dan Kelengkapan")
        k1,k2 = st.columns(2)
        with k1:
            knuckle1 = st.text_input("Keausan knuckle Bogie 1")
            emptyload = st.selectbox("Kelengkapan emptyload", ["Ada", "Tidak ada"])
            tinggi_boffer = st.text_input("Tinggi boffer")
        with k2:
            knuckle2 = st.text_input("Keausan knuckle Bogie 2")
            status = st.selectbox("Status sarana", ["SO", "TSO"])
        st.markdown("### 5. Pemeriksaan Pengereman")
        p1,p2,p3 = st.columns(3)
        with p1: brake = st.text_input("Brake")
        with p2: release = st.text_input("Release")
        with p3: langkah_torak = st.text_input("Langkah torak")
        p4,p5,p6 = st.columns(3)
        with p4: ac = st.text_input("AC")
        with p5: cd = st.text_input("CD")
        with p6: tekanan_bc = st.text_input("Tekanan BC")
        st.markdown("### 6. Catatan Lain-lain")
        lainnya = st.text_area("Lain-lain / temuan pemeriksaan", height=120, placeholder="Tulis temuan lainnya di sini...")
        st.markdown("### 7. Dokumentasi Foto")
        p1,p2 = st.columns(2)
        with p1: foto_sebelum = st.file_uploader("📷 Foto sebelum pemeriksaan", type=["jpg","jpeg","png","webp"], key="foto_sebelum")
        with p2: foto_sesudah = st.file_uploader("📸 Foto sesudah pemeriksaan", type=["jpg","jpeg","png","webp"], key="foto_sesudah")
        st.markdown("### 8. Petugas dan Informasi Tambahan")
        c,d = st.columns(2)
        with c:
            lokasi = st.text_input("Depo / lokasi")
            petugas = st.text_input("Nama petugas / teknisi")
        with d:
            nipp = st.text_input("NIPP")
            keterangan = st.text_area("Keterangan tambahan", height=75)
        submitted = st.form_submit_button("💾 SIMPAN DATA PEMERIKSAAN", type="primary", use_container_width=True)

    if submitted:
        if not nomor.strip():
            st.error("Nomor sarana wajib diisi.")
        else:
            try:
                record_id = make_id()
                with st.spinner("Mengunggah foto dan menyimpan data..."):
                    foto1 = upload_photo(drive, foto_sebelum, folder_id, f"{record_id}_sebelum_{foto_sebelum.name}" if foto_sebelum else "", make_public) if foto_sebelum else ""
                    foto2 = upload_photo(drive, foto_sesudah, folder_id, f"{record_id}_sesudah_{foto_sesudah.name}" if foto_sesudah else "", make_public) if foto_sesudah else ""
                    record = {
                        "ID": record_id, "Tanggal Perawatan": tanggal.strftime("%Y-%m-%d"),
                        "Jenis Sarana": jenis_sarana, "Nomor Sarana": nomor.strip().upper(),
                        "Jenis Perawatan": jenis_perawatan, "Depo/Lokasi": lokasi, "Dipo Induk": dipo_induk,
                        "Nama Petugas": petugas, "NIPP": nipp,
                        "Foto Sebelum": foto1, "Foto Sesudah": foto2,
                        "Keterangan": keterangan, "Waktu Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Mulai Dinas": mulai_dinas.strftime("%Y-%m-%d"), "Siklus Perawatan": siklus.strftime("%Y-%m-%d"),
                        "Nomor Bogie 1": no_bogie1, "Nomor Bogie 2": no_bogie2, "Ukuran Roda": ukuran_roda,
                        **{f"Diameter B{b} R{r+1}": diameter[b][r] for b in (1,2) for r in range(4)},
                        **{f"Flens B{b} R{r+1}": flens[b][r] for b in (1,2) for r in range(4)},
                        **{f"Bidang Jalan B{b} R{r+1}": bidang[b][r] for b in (1,2) for r in range(4)},
                        "Keausan Knuckle Bogie 1": knuckle1, "Keausan Knuckle Bogie 2": knuckle2,
                        "Kelengkapan Emptyload": emptyload, "Tinggi Boffer": tinggi_boffer,
                        "Brake": brake, "Release": release, "Langkah Torak": langkah_torak,
                        "AC": ac, "CD": cd, "Tekanan BC": tekanan_bc, "Lain-lain": lainnya,
                        "Status SO/TSO": status
                    }
                    add_record(ws, record)
                st.success(f"✅ Data perawatan berhasil disimpan. ID: {record_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan data: {e}")

elif page == "Riwayat Perawatan":
    st.subheader("📚 Riwayat Perawatan per Nomor Sarana")
    q1,q2 = st.columns([1,2])
    with q1: tipe_filter = st.selectbox("Jenis sarana", ["Semua", "GD", "GB", "B"])
    with q2: nomor_filter = st.text_input("Cari nomor GD / B", placeholder="Contoh: 421005 atau B 12345")
    filtered = df.copy()
    if tipe_filter != "Semua": filtered = filtered[filtered["Jenis Sarana"].astype(str) == tipe_filter]
    if nomor_filter.strip(): filtered = filtered[filtered["Nomor Sarana"].astype(str).str.contains(nomor_filter.strip(), case=False, na=False)]
    st.caption(f"Ditemukan {len(filtered)} catatan perawatan")
    if len(filtered):
        filtered = filtered.sort_values("Tanggal Perawatan", ascending=False)
        st.dataframe(filtered, use_container_width=True, hide_index=True, column_config={"Foto Sebelum": st.column_config.LinkColumn("Foto Sebelum"), "Foto Sesudah": st.column_config.LinkColumn("Foto Sesudah")})
        pilihan = st.selectbox("Lihat detail nomor sarana", ["-- Pilih --"] + sorted(filtered["Nomor Sarana"].astype(str).unique().tolist()))
        if pilihan != "-- Pilih --":
            detail = filtered[filtered["Nomor Sarana"].astype(str) == pilihan].sort_values("Tanggal Perawatan", ascending=False)
            st.markdown(f"#### Riwayat {pilihan}")
            for _, r in detail.iterrows():
                with st.expander(f"{r['Tanggal Perawatan']} · {r['Jenis Perawatan']}"):
                    st.write("**Dipo Induk:**", r.get("Dipo Induk",""))
                    st.write("**Lokasi:**", r["Depo/Lokasi"])
                    st.write("**Petugas:**", r["Nama Petugas"], "| **NIPP:**", r["NIPP"])
                    if r["Foto Sebelum"]: st.markdown(f"[Buka foto sebelum]({r['Foto Sebelum']})")
                    if r["Foto Sesudah"]: st.markdown(f"[Buka foto sesudah]({r['Foto Sesudah']})")
                    if r["Keterangan"]: st.write("**Keterangan:**", r["Keterangan"])
    else: st.info("Data tidak ditemukan.")

elif page == "Laporan Otomatis":
    st.subheader("📄 Laporan Data Perawatan")
    if df.empty: st.info("Belum ada data untuk dilaporkan.")
    else:
        l,r = st.columns(2)
        with l: start = st.date_input("Dari tanggal", value=date(date.today().year,1,1), key="start")
        with r: end = st.date_input("Sampai tanggal", value=date.today(), key="end")
        report = df.copy()
        dates = pd.to_datetime(report["Tanggal Perawatan"], errors="coerce")
        report = report[(dates.dt.date >= start) & (dates.dt.date <= end)]
        x,y = st.columns(2)
        with x: jenis = st.multiselect("Jenis sarana", ["GD","GB","B"], default=["GD","GB","B"])
        with y: perawatan = st.multiselect("Jenis perawatan", sorted(df["Jenis Perawatan"].dropna().astype(str).unique()))
        report = report[report["Jenis Sarana"].isin(jenis)]
        if perawatan: report = report[report["Jenis Perawatan"].isin(perawatan)]
        m1,m2,m3 = st.columns(3)
        m1.metric("Jumlah catatan", len(report))
        m2.metric("GD + GB", int(report["Jenis Sarana"].isin(["GD", "GB"]).sum()))
        m3.metric("B", int((report["Jenis Sarana"]=="B").sum()))
        st.markdown("#### Rekap per jenis perawatan")
        if len(report):
            st.bar_chart(report["Jenis Perawatan"].value_counts())
            st.dataframe(report, use_container_width=True, hide_index=True)
            csv = report.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Unduh laporan CSV", csv, file_name=f"laporan_perawatan_{start}_{end}.csv", mime="text/csv")
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer: report.to_excel(writer, index=False, sheet_name="Laporan")
            st.download_button("Unduh laporan Excel", excel_buffer.getvalue(), file_name=f"laporan_perawatan_{start}_{end}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.warning("Tidak ada data pada filter periode tersebut.")
