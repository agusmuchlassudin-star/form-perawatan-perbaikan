import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO
from uuid import uuid4
import re
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Sistem Data Perawatan Sarana", page_icon="🚆", layout="wide", initial_sidebar_state="expanded")

# --------------------------- KONFIGURASI ---------------------------
SHEET_NAME = "Data Perawatan"
LOG_SHEET_NAME = "Log Aktivitas"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
FLEET_TOTAL = 582  # Angka populasi referensi dari pengguna, bukan jumlah transaksi.
FLEET_GERBONG = 527
FLEET_BAGASI = 55
MAX_PHOTO_MB = 10

HEADERS = [
    "ID", "Tanggal Perawatan", "Jenis Sarana", "Nomor Sarana", "Mulai Dinas",
    "P24/P48 Terakhir", "Program Pemeliharaan", "Depo/Lokasi", "Nomor Bogie 1", "Nomor Bogie 2",
    "Diameter B1 R1", "Flens B1 R1", "Bidang Jalan B1 R1",
    "Diameter B1 R2", "Flens B1 R2", "Bidang Jalan B1 R2",
    "Diameter B1 R3", "Flens B1 R3", "Bidang Jalan B1 R3",
    "Diameter B1 R4", "Flens B1 R4", "Bidang Jalan B1 R4",
    "Diameter B2 R1", "Flens B2 R1", "Bidang Jalan B2 R1",
    "Diameter B2 R2", "Flens B2 R2", "Bidang Jalan B2 R2",
    "Diameter B2 R3", "Flens B2 R3", "Bidang Jalan B2 R3",
    "Diameter B2 R4", "Flens B2 R4", "Bidang Jalan B2 R4",
     "Keausan Knuckle Bogie 1", "Keausan Knuckle Bogie 2", "Kelengkapan Emptyload", "Tinggi Boffer",
    "Tebal Center Plate",
    "Tinggi Frame B1 R1", "Tinggi Frame B1 R2", "Tinggi Frame B1 R3", "Tinggi Frame B1 R4",
    "Tinggi Frame B2 R1", "Tinggi Frame B2 R2", "Tinggi Frame B2 R3", "Tinggi Frame B2 R4",
    "Axle Box B1 R1", "Axle Box B1 R2", "Axle Box B1 R3", "Axle Box B1 R4",
    "Axle Box B2 R1", "Axle Box B2 R2", "Axle Box B2 R3", "Axle Box B2 R4",
    "Spring Plank B1 N1", "Spring Plank B1 N2", "Spring Plank B2 N1", "Spring Plank B2 N2",
    "Brake", "Release", "Langkah Torak", "AC", "CD", "Tekanan BC",
    "Komponen", "Jenis Pekerjaan", "Kondisi Sebelum", "Tindakan Perawatan", "Kondisi Sesudah",
    "Lain-lain", "Status SO/TSO", "Nama Petugas", "NIPP", "Foto Sebelum", "Foto Sesudah",
    "Keterangan", "Waktu Input", "Dibuat Oleh",
    "Status Approval", "Disetujui Oleh", "Waktu Approval",
]
PROGRAMS = ["P1", "P3", "P6", "P12", "Perbaikan"]
TYPES = ["GD", "GB", "B", "Lainnya"]

# --------------------------- TEMA ---------------------------
st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: #071827; color: #edf4fb; }
[data-testid="stHeader"] { background: rgba(7,24,39,.92); }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#0b2945,#071827); border-right:1px solid #234461; }
[data-testid="stSidebar"] * { color:#edf4fb !important; }
.block-container { padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1500px; }
.hero { background:linear-gradient(115deg,#0d3152 0%,#14578a 62%,#e87518 100%); border:1px solid #376b91; padding:24px 28px; border-radius:18px; margin-bottom:18px; box-shadow:0 10px 30px rgba(0,0,0,.22); }
.hero h1 { color:white !important; font-size:clamp(24px,3vw,36px); margin:0; font-weight:850; }
.hero p { color:#e6f1fb !important; margin:7px 0 0 0; }
.section-card { background:#10283d; border:1px solid #294760; border-radius:14px; padding:15px 17px; }
.kpi { background:linear-gradient(145deg,#102b43,#0d2236); border:1px solid #2b4d68; border-top:4px solid #f28c28; border-radius:15px; padding:15px 17px; min-height:112px; }
.kpi .label { color:#a9c1d5; font-size:13px; font-weight:650; }
.kpi .value { color:#fff; font-size:30px; font-weight:850; margin-top:5px; }
.kpi .note { color:#91a9bd; font-size:11px; margin-top:2px; }
div[data-testid="stMetric"] { background:#10283d; border:1px solid #294760; border-radius:13px; padding:12px 14px; }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] { color:#f4f8fc !important; }
.stButton>button, .stDownloadButton>button { background:#ef8125; color:white; border:0; border-radius:9px; font-weight:700; }
.stButton>button:hover, .stDownloadButton>button:hover { background:#ff9b43; color:white; border:0; }
input, textarea, [data-baseweb="select"] > div { background-color:#f8fbff !important; color:#12283b !important; border-radius:7px !important; }
label, .stMarkdown, p, h1, h2, h3, h4 { color:#edf4fb; }
[data-testid="stDataFrame"] { border:1px solid #294760; border-radius:10px; }
/* Pastikan tulisan hasil pengukuran di tabel input bogie terbaca jelas */
[data-testid="stDataEditor"] [role="grid"],
[data-testid="stDataEditor"] [role="gridcell"],
[data-testid="stDataEditor"] [role="columnheader"],
[data-testid="stDataEditor"] input,
[data-testid="stDataEditor"] textarea {
    color:#172b3d !important;
    -webkit-text-fill-color:#172b3d !important;
}
[data-testid="stDataEditor"] [role="gridcell"] { background-color:#f4f8fc !important; }
[data-testid="stDataEditor"] [role="columnheader"] { background-color:#dce8f2 !important; color:#10283d !important; font-weight:700 !important; }
[data-testid="stDataEditor"] [data-testid="stMarkdownContainer"] { color:#172b3d !important; }
[data-testid="stExpander"] { background:#10283d; border:1px solid #294760; border-radius:10px; }
hr { border-color:#294760; }
.small-muted { color:#9bb2c5; font-size:12px; }
</style>
<div class="hero"><h1>🚆 SISTEM DATA PERAWATAN SARANA</h1><p>Pengelolaan pemeriksaan dan pemeliharaan GD · GB · B · Lainnya | Database Google Spreadsheet & dokumentasi Google Drive</p></div>
""", unsafe_allow_html=True)

# --------------------------- GOOGLE CONNECT ---------------------------
def get_config():
    if "gcp_service_account" not in st.secrets:
        st.error("Konfigurasi Google belum tersedia. Ikuti petunjuk pada README untuk mengisi .streamlit/secrets.toml.")
        st.stop()
    return st.secrets

@st.cache_resource(show_spinner="Menghubungkan ke Google...")
def connect_google():
    cfg = get_config()
    creds = Credentials.from_service_account_info(dict(cfg["gcp_service_account"]), scopes=SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet_id = str(cfg.get("spreadsheet_id", "")).strip()
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id belum diisi pada secrets.toml")
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=3000, cols=max(HEADERS.__len__(), 60))
    existing = ws.row_values(1)
    if not existing:
        ws.resize(rows=max(ws.row_count, 3000), cols=max(ws.col_count, len(HEADERS)))
        ws.update(range_name="A1", values=[HEADERS])
        existing = HEADERS.copy()
    else:
        # Ganti nama kolom lama tanpa menggeser atau menghapus data yang sudah tersimpan.
        if "Siklus Pemeriksaan" in existing and "P24/P48 Terakhir" not in existing:
            old_idx = existing.index("Siklus Pemeriksaan")
            existing[old_idx] = "P24/P48 Terakhir"
            ws.update_cell(1, old_idx + 1, "P24/P48 Terakhir")
        missing = [h for h in HEADERS if h not in existing]
        if missing:
            updated = existing + missing
            ws.resize(cols=max(ws.col_count, len(updated)))
            ws.update(range_name="A1", values=[updated])
            existing = updated
    # Sheet log untuk jejak input; dibuat terpisah agar data utama tetap utuh.
    log_headers = ["Waktu", "ID Data", "Aktivitas", "Pengguna", "Nomor Sarana", "Keterangan"]
    try:
        log_ws = sh.worksheet(LOG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        log_ws = sh.add_worksheet(title=LOG_SHEET_NAME, rows=3000, cols=len(log_headers))
    if not log_ws.row_values(1):
        log_ws.update(range_name="A1", values=[log_headers])
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    return sh, ws, log_ws, drive, cfg, existing

def upload_photo(drive, uploaded, folder_id, filename, make_public=False):
    if uploaded is None:
        return ""
    if uploaded.size > MAX_PHOTO_MB * 1024 * 1024:
        raise ValueError(f"Ukuran foto {uploaded.name} melebihi {MAX_PHOTO_MB} MB.")
    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(BytesIO(uploaded.getvalue()), mimetype=uploaded.type or "image/jpeg", resumable=True)
    result = drive.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    if make_public:
        drive.permissions().create(fileId=result["id"], body={"type":"anyone", "role":"reader"}, fields="id").execute()
    return result.get("webViewLink", f"https://drive.google.com/file/d/{result['id']}/view")

def load_records(ws):
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(rows).fillna("")
    for col in HEADERS:
        if col not in df.columns:
            df[col] = ""
    # Catatan lama otomatis masuk status belum disetujui.
    df["Status Approval"] = df["Status Approval"].replace("", "Belum Approve")
    return df

def append_record(ws, record, sheet_headers):
    # PENTING: gunakan urutan header aktual di Google Sheet agar data lama tidak bergeser.
    ws.append_row([record.get(h, "") for h in sheet_headers], value_input_option="RAW")

def log_activity(log_ws, record_id, activity, user, nomor, note=""):
    log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id, activity, user, nomor, note], value_input_option="RAW")

def update_record_by_id(ws, record_id, record, sheet_headers):
    """Perbarui satu baris berdasarkan ID tanpa menggeser kolom atau menghapus kolom tambahan."""
    values = ws.get_all_values()
    if not values:
        raise ValueError("Spreadsheet belum memiliki data.")
    headers = values[0]
    if "ID" not in headers:
        raise ValueError("Kolom ID tidak ditemukan pada Google Sheet.")
    id_col = headers.index("ID")
    row_number = None
    for idx, row in enumerate(values[1:], start=2):
        if len(row) > id_col and row[id_col] == record_id:
            row_number = idx
            break
    if row_number is None:
        raise ValueError("Data tidak ditemukan. Muat ulang halaman dan coba lagi.")
    old_row = values[row_number - 1]
    updated = [old_row[i] if i < len(old_row) else "" for i in range(len(headers))]
    for i, header in enumerate(headers):
        if header in record:
            updated[i] = record[header]
    from gspread.utils import rowcol_to_a1
    end_cell = rowcol_to_a1(row_number, len(headers))
    ws.update(range_name=f"A{row_number}:{end_cell}", values=[updated], value_input_option="RAW")
    return row_number

def clean_text(value):
    return str(value or "").strip()

def fmt_date(value):
    d = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(d) else d.strftime("%Y-%m-%d")

def make_excel(frame):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Data Perawatan")
        wsx = writer.sheets["Data Perawatan"]
        wsx.freeze_panes = "A2"
        wsx.auto_filter.ref = wsx.dimensions
        for col in wsx.columns:
            width = min(max(max(len(str(c.value or "")) for c in col) + 2, 12), 34)
            wsx.column_dimensions[col[0].column_letter].width = width
    return buf.getvalue()

# --------------------------- LOAD DATA ---------------------------
try:
    sh, ws, log_ws, drive, cfg, actual_headers = connect_google()
    df = load_records(ws)
except Exception as exc:
    st.error(f"Tidak berhasil terhubung atau membaca Google Spreadsheet: {exc}")
    st.info("Periksa Spreadsheet ID, izin berbagi kepada email service account, Google Sheets API, dan Google Drive API.")
    st.stop()

folder_id = clean_text(cfg.get("drive_folder_id", ""))
make_public = bool(cfg.get("share_photos_publicly", False))
user_label = clean_text(cfg.get("nama_pengguna", "Petugas aplikasi")) or "Petugas aplikasi"

with st.sidebar:
    st.markdown("## 🚆 MENU UTAMA")
    page = st.radio("Pilih halaman", ["Dashboard", "Input Perawatan", "Edit & Persetujuan", "Riwayat Perawatan", "Laporan Otomatis"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Depo Gerbong Jakarta Gudang**")
    st.caption("Sistem pencatatan pemeriksaan dan pemeliharaan sarana")
    st.caption(f"Pengguna: {user_label}")
    st.divider()
    st.caption("Tips: gunakan nomor sarana yang konsisten agar pencarian riwayat lebih akurat.")

# --------------------------- DASHBOARD ---------------------------
if page == "Dashboard":
    st.subheader("Dashboard Monitoring Perawatan")
    total_record = len(df)
    if total_record:
        dates = pd.to_datetime(df["Tanggal Perawatan"], errors="coerce")
        this_month = int(((dates.dt.year == date.today().year) & (dates.dt.month == date.today().month)).sum())
        so_count = int((df["Status SO/TSO"].astype(str).str.upper() == "SO").sum())
        tso_count = int((df["Status SO/TSO"].astype(str).str.upper() == "TSO").sum())
    else:
        this_month = so_count = tso_count = 0
    k1,k2,k3,k4 = st.columns(4)
    for col, label, value, note in [
        (k1,"Total Populasi Sarana",FLEET_TOTAL,"Angka referensi populasi"),
        (k2,"Gerbong",FLEET_GERBONG,"Angka referensi gerbong"),
        (k3,"Bagasi",FLEET_BAGASI,"Angka referensi bagasi"),
        (k4,"Catatan Perawatan",total_record,"Jumlah transaksi tersimpan"),
    ]:
        col.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value:,}</div><div class="note">{note}</div></div>', unsafe_allow_html=True)
    st.caption("Angka populasi 582 / 527 / 55 adalah angka referensi, bukan jumlah transaksi perawatan.")
    st.divider()
    a,b,c = st.columns(3)
    a.metric("Perawatan Bulan Ini", f"{this_month:,}")
    b.metric("Status SO", f"{so_count:,}")
    c.metric("Status TSO", f"{tso_count:,}")
    if total_record:
        left,right = st.columns([1,1])
        with left:
            st.markdown("#### Catatan berdasarkan program")
            prog = df["Program Pemeliharaan"].replace("", "Belum diisi").value_counts()
            st.bar_chart(prog)
        with right:
            st.markdown("#### Catatan berdasarkan jenis sarana")
            typ = df["Jenis Sarana"].replace("", "Belum diisi").value_counts()
            st.bar_chart(typ)
        st.markdown("#### 10 catatan terbaru")
        recent = df.copy()
        recent["_sort"] = pd.to_datetime(recent["Waktu Input"], errors="coerce")
        recent = recent.sort_values("_sort", ascending=False).drop(columns="_sort").head(10)
        show_cols = [c for c in ["Tanggal Perawatan","Jenis Sarana","Nomor Sarana","Program Pemeliharaan","Depo/Lokasi","Status SO/TSO","Nama Petugas"] if c in recent]
        st.dataframe(recent[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada catatan perawatan. Mulai dengan menu Input Perawatan.")

# --------------------------- INPUT ---------------------------
elif page == "Input Perawatan":
    st.subheader("Input Pemeriksaan & Pemeliharaan Sarana")
    st.caption("Isi sesuai hasil pemeriksaan aktual. Pengukuran roda dibuat ringkas dalam tabel per bogie.")
    st.markdown("### 1. Identitas sarana")
    jenis_sarana = st.selectbox("Jenis sarana *", TYPES, key="jenis_sarana_dynamic")
    with st.form("form_perawatan_v4", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            jenis_lain = st.text_input("Jenis sarana lainnya", placeholder="Isi jika memilih Lainnya")
            nomor = st.text_input("Nomor sarana *", placeholder="Contoh: GD 421005")
        with c2:
            mulai_dinas = st.date_input(
                "Mulai dinas",
                value=date.today(),
                min_value=date.today().replace(year=date.today().year - 30),
                max_value=date.today(),
                format="DD/MM/YYYY",
                help="Tanggal mulai dinas dapat dipilih hingga 30 tahun ke belakang."
            )
            p24p48_terakhir = st.date_input(
                "P24/P48 Terakhir",
                value=date.today(),
                format="DD/MM/YYYY",
                help="Masukkan tanggal terakhir pelaksanaan P24 atau P48."
            )
        with c3:
            tanggal = st.date_input(
                "Tanggal pemeriksaan / perawatan",
                value=date.today(),
                format="DD/MM/YYYY"
            )
            program = st.selectbox("Program pemeliharaan *", PROGRAMS)
        lokasi = st.text_input("Depo / lokasi pemeriksaan", placeholder="Contoh: Depo Gerbong Jakarta Gudang")
        st.markdown("### 2. Identitas bogie")
        b1,b2 = st.columns(2)
        with b1: no_bogie1 = st.text_input("Nomor Bogie 1")
        with b2: no_bogie2 = st.text_input("Nomor Bogie 2")
        st.markdown("### 3. Pengukuran roda")
        st.caption("Isi angka beserta satuan bila diperlukan. Kosongkan kolom jika tidak dilakukan pengukuran.")
        wheel_tables = {}
        for bogie_num in (1,2):
            st.markdown(f"**Bogie {bogie_num}**")
            initial = pd.DataFrame({"Roda": ["Roda 1","Roda 2","Roda 3","Roda 4"], "Diameter": ["","","",""], "Flens": ["","","",""], "Bidang Jalan": ["","","",""]})
            wheel_tables[bogie_num] = st.data_editor(
                initial, key=f"wheel_table_{bogie_num}", use_container_width=True, hide_index=True,
                disabled=["Roda"], num_rows="fixed", column_config={
                    "Roda": st.column_config.TextColumn("Posisi roda", width="small"),
                    "Diameter": st.column_config.TextColumn("Diameter", help="Isi hasil ukur diameter roda"),
                    "Flens": st.column_config.TextColumn("Flens", help="Isi hasil ukur flens"),
                    "Bidang Jalan": st.column_config.TextColumn("Bidang jalan", help="Isi hasil ukur bidang jalan"),
                })
        # Checklist tambahan khusus sarana B
        special_tables = {}
        if jenis_sarana == "B":
            st.markdown("### 4. Pengukuran khusus Sarana B")
            st.caption("Pengukuran disimpan terpisah untuk setiap bogie dan posisi roda/nomor komponen.")
            for component, label in [("Tinggi Frame", "Tinggi Frame"), ("Axle Box", "Axle Box")]:
                for bn in (1, 2):
                    st.markdown(f"**{label} — Bogie {bn}**")
                    initial_special = pd.DataFrame({
                        "Posisi": [f"Roda {i}" for i in range(1, 5)],
                        "Hasil Ukur": ["", "", "", ""]
                    })
                    special_tables[f"{component}_B{bn}"] = st.data_editor(
                        initial_special, key=f"{component.lower().replace(' ', '_')}_b{bn}",
                        use_container_width=True, hide_index=True, num_rows="fixed",
                        disabled=["Posisi"],
                        column_config={
                            "Posisi": st.column_config.TextColumn("Posisi", width="small"),
                            "Hasil Ukur": st.column_config.TextColumn("Hasil ukur")
                        })
            for bn in (1, 2):
                st.markdown(f"**Spring Plank — Bogie {bn}**")
                initial_spring = pd.DataFrame({"Nomor": ["Nomor 1", "Nomor 2"], "Hasil Ukur": ["", ""]})
                special_tables[f"Spring_Plank_B{bn}"] = st.data_editor(
                    initial_spring, key=f"spring_plank_b{bn}", use_container_width=True,
                    hide_index=True, num_rows="fixed", disabled=["Nomor"],
                    column_config={
                        "Nomor": st.column_config.TextColumn("Nomor", width="small"),
                        "Hasil Ukur": st.column_config.TextColumn("Hasil ukur")
                    })
        st.markdown("### 5. Pengukuran Center Plate")
        center_plate = st.text_input("Tebal Center Plate", placeholder="Isi hasil pengukuran (mis. mm)")
        st.markdown("### 6. Pemeriksaan komponen")
        c1,c2,c3 = st.columns(3)
        with c1:
            knuckle1 = st.text_input("Keausan knuckle Bogie 1")
            knuckle2 = st.text_input("Keausan knuckle Bogie 2")
        with c2:
            if jenis_sarana == "GD":
                emptyload = st.selectbox("Pemeriksaan Empty Load", ["Belum diperiksa", "Lengkap", "Tidak lengkap", "Tidak berlaku"])
            else:
                emptyload = ""
                if jenis_sarana == "B":
                    st.caption("Pemeriksaan Empty Load tidak berlaku untuk Sarana B.")
            boffer = st.text_input("Tinggi boffer")
        with c3:
            status = st.selectbox("Status sarana", ["SO", "TSO", "Belum ditentukan"])
            komponen = st.text_input("Komponen yang diperiksa")
        st.markdown("### 5. Pemeriksaan pengereman dan tekanan")
        p1,p2,p3 = st.columns(3)
        with p1: brake = st.text_input("Brake")
        with p2: release = st.text_input("Release")
        with p3: torak = st.text_input("Langkah torak")
        p4,p5,p6 = st.columns(3)
        with p4: ac = st.text_input("AC")
        with p5: cd = st.text_input("CD")
        with p6: bc = st.text_input("Tekanan BC")
        st.markdown("### 6. Temuan dan tindakan perawatan")
        pekerjaan = st.text_input("Jenis pekerjaan")
        d1,d2 = st.columns(2)
        with d1:
            sebelum = st.text_area("Kondisi sebelum", height=100)
            tindakan = st.text_area("Tindakan perawatan", height=130)
        with d2:
            sesudah = st.text_area("Kondisi sesudah", height=100)
            lainnya = st.text_area("Lain-lain / temuan pemeriksaan", height=130)
        keterangan = st.text_area("Keterangan tambahan", height=80)
        st.markdown("### 7. Dokumentasi foto")
        f1,f2 = st.columns(2)
        with f1: foto_sebelum = st.file_uploader("Foto sebelum", type=["jpg","jpeg","png","webp"], key="upload_before", help=f"Maksimal {MAX_PHOTO_MB} MB per foto")
        with f2: foto_sesudah = st.file_uploader("Foto sesudah", type=["jpg","jpeg","png","webp"], key="upload_after", help=f"Maksimal {MAX_PHOTO_MB} MB per foto")
        st.markdown("### 8. Petugas")
        t1,t2 = st.columns(2)
        with t1: petugas = st.text_input("Nama petugas / teknisi")
        with t2: nipp = st.text_input("NIPP")
        submitted = st.form_submit_button("💾 SIMPAN DATA PERAWATAN", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not clean_text(nomor): errors.append("Nomor sarana wajib diisi.")
        if jenis_sarana == "Lainnya" and not clean_text(jenis_lain): errors.append("Jenis sarana lainnya wajib diisi.")
        if foto_sebelum and foto_sebelum.size > MAX_PHOTO_MB*1024*1024: errors.append(f"Foto sebelum melebihi {MAX_PHOTO_MB} MB.")
        if foto_sesudah and foto_sesudah.size > MAX_PHOTO_MB*1024*1024: errors.append(f"Foto sesudah melebihi {MAX_PHOTO_MB} MB.")
        if errors:
            for e in errors: st.error(e)
        else:
            record_id = "PRW-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:6].upper()
            jenis_final = clean_text(jenis_lain) if jenis_sarana == "Lainnya" else jenis_sarana
            record = {h:"" for h in HEADERS}
            record.update({
                "ID":record_id, "Tanggal Perawatan":tanggal.isoformat(), "Jenis Sarana":jenis_final,
                "Nomor Sarana":clean_text(nomor).upper(), "Mulai Dinas":mulai_dinas.isoformat(),
                "P24/P48 Terakhir":p24p48_terakhir.isoformat(), "Program Pemeliharaan":program, "Depo/Lokasi":clean_text(lokasi),
                "Nomor Bogie 1":clean_text(no_bogie1), "Nomor Bogie 2":clean_text(no_bogie2),
                "Keausan Knuckle Bogie 1":clean_text(knuckle1), "Keausan Knuckle Bogie 2":clean_text(knuckle2),
                "Kelengkapan Emptyload":emptyload, "Tinggi Boffer":clean_text(boffer),
                "Tebal Center Plate":clean_text(center_plate),
                "Brake":clean_text(brake), "Release":clean_text(release), "Langkah Torak":clean_text(torak),
                "AC":clean_text(ac), "CD":clean_text(cd), "Tekanan BC":clean_text(bc),
                "Komponen":clean_text(komponen), "Jenis Pekerjaan":clean_text(pekerjaan),
                "Kondisi Sebelum":clean_text(sebelum), "Tindakan Perawatan":clean_text(tindakan),
                "Kondisi Sesudah":clean_text(sesudah), "Lain-lain":clean_text(lainnya),
                "Status SO/TSO":status, "Nama Petugas":clean_text(petugas), "NIPP":clean_text(nipp),
                "Keterangan":clean_text(keterangan), "Waktu Input":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Dibuat Oleh":user_label, "Status Approval":"Belum Approve",
                "Disetujui Oleh":"", "Waktu Approval":"",
            })
            for bn, table in wheel_tables.items():
                for _, row in table.iterrows():
                    match = re.search(r"(\d+)$", str(row["Roda"]))
                    if not match: continue
                    rn = int(match.group(1))
                    for field in ["Diameter", "Flens", "Bidang Jalan"]:
                        record[f"{field} B{bn} R{rn}"] = clean_text(row[field])
            try:
                with st.spinner("Mengunggah dokumentasi dan menyimpan data ke Google Spreadsheet..."):
                    if foto_sebelum:
                        record["Foto Sebelum"] = upload_photo(drive, foto_sebelum, folder_id, f"{record_id}_SEBELUM_{foto_sebelum.name}", make_public)
                    if foto_sesudah:
                        record["Foto Sesudah"] = upload_photo(drive, foto_sesudah, folder_id, f"{record_id}_SESUDAH_{foto_sesudah.name}", make_public)
                    append_record(ws, record, actual_headers)
                    log_activity(log_ws, record_id, "INPUT", user_label, record["Nomor Sarana"], f"Program {program} / {status}")
                st.success(f"Data berhasil disimpan. Nomor referensi: {record_id}")
                st.rerun()
            except Exception as exc:
                st.error(f"Penyimpanan belum berhasil: {exc}")
                st.warning("Jika foto sudah terunggah tetapi penyimpanan baris gagal, periksa folder Google Drive agar tidak ada file foto yatim.")

# --------------------------- EDIT & APPROVAL ---------------------------
elif page == "Edit & Persetujuan":
    st.subheader("Edit Data dan Persetujuan Perawatan")
    st.caption("Data dapat diedit selama berstatus Belum Approve. Setelah disetujui, data terkunci dan menu edit tidak tersedia untuk catatan tersebut.")
    if df.empty:
        st.info("Belum ada data perawatan.")
    else:
        pending = df.copy()
        pending["Status Approval"] = pending["Status Approval"].replace("", "Belum Approve")
        pending = pending.sort_values("Waktu Input", ascending=False)
        choices = pending.apply(lambda r: f"{r['Nomor Sarana']} | {r['Tanggal Perawatan']} | {r['Program Pemeliharaan']} | {r['ID']} [{r['Status Approval']}]", axis=1).tolist()
        selected_label = st.selectbox("Pilih catatan perawatan", ["-- Pilih data --"] + choices)
        if selected_label != "-- Pilih data --":
            selected_id = selected_label.split("|")[-1].split("[")[0].strip()
            selected_rows = df[df["ID"].astype(str) == selected_id]
            if not selected_rows.empty:
                selected_record = selected_rows.iloc[0].to_dict()
                approval_status = clean_text(selected_record.get("Status Approval")) or "Belum Approve"
                st.markdown(f"**Nomor Sarana:** {selected_record.get('Nomor Sarana','')}  ")
                st.markdown(f"**Status:** {approval_status}")
                if approval_status == "Disetujui":
                    st.success(f"Data telah disetujui oleh {selected_record.get('Disetujui Oleh','')} pada {selected_record.get('Waktu Approval','')}.")
                    st.info("Menu edit otomatis dinonaktifkan karena data sudah disetujui.")
                else:
                    st.warning("Data masih dapat diperbaiki. Pastikan seluruh hasil pemeriksaan sudah benar sebelum disetujui.")
                    edit_frame = pd.DataFrame([{h: selected_record.get(h, "") for h in actual_headers}])
                    protected = [c for c in ["ID", "Waktu Input", "Dibuat Oleh", "Status Approval", "Disetujui Oleh", "Waktu Approval"] if c in edit_frame.columns]
                    with st.form(f"edit_record_{selected_id}"):
                        edited_frame = st.data_editor(
                            edit_frame, key=f"editor_{selected_id}", use_container_width=True,
                            hide_index=True, num_rows="fixed", disabled=protected,
                            column_config={c: st.column_config.TextColumn(c, width="medium") for c in edit_frame.columns}
                        )
                        save_edit = st.form_submit_button("💾 SIMPAN PERUBAHAN", type="primary", use_container_width=True)
                    if save_edit:
                        # Pemeriksaan ulang status langsung dari Google Sheet agar tidak bisa mengedit data yang baru disetujui.
                        fresh = load_records(ws)
                        current = fresh[fresh["ID"].astype(str) == selected_id]
                        current_status = "" if current.empty else (clean_text(current.iloc[0].get("Status Approval")) or "Belum Approve")
                        if current_status == "Disetujui":
                            st.error("Perubahan ditolak: data sudah disetujui oleh pengguna lain.")
                        else:
                            updated_record = edited_frame.iloc[0].to_dict()
                            updated_record["Status Approval"] = "Belum Approve"
                            try:
                                update_record_by_id(ws, selected_id, updated_record, actual_headers)
                                log_activity(log_ws, selected_id, "EDIT", user_label, clean_text(updated_record.get("Nomor Sarana")), "Perubahan data sebelum persetujuan")
                                st.success("Perubahan berhasil disimpan.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Gagal menyimpan perubahan: {exc}")
                    st.divider()
                    confirm_approve = st.checkbox("Saya sudah memeriksa dan menyatakan data ini benar untuk disetujui.", key=f"confirm_approve_{selected_id}")
                    if st.button("✅ SETUJUI DATA", type="primary", disabled=not confirm_approve, key=f"approve_{selected_id}", use_container_width=True):
                        # Validasi status dilakukan kembali di sisi server sebelum mengunci baris.
                        fresh = load_records(ws)
                        current = fresh[fresh["ID"].astype(str) == selected_id]
                        current_status = "" if current.empty else (clean_text(current.iloc[0].get("Status Approval")) or "Belum Approve")
                        if current_status == "Disetujui":
                            st.error("Data ini sudah disetujui sebelumnya.")
                        else:
                            approved_record = current.iloc[0].to_dict()
                            approved_record.update({"Status Approval":"Disetujui", "Disetujui Oleh":user_label, "Waktu Approval":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                            try:
                                update_record_by_id(ws, selected_id, approved_record, actual_headers)
                                log_activity(log_ws, selected_id, "APPROVE", user_label, clean_text(approved_record.get("Nomor Sarana")), "Data disetujui dan dikunci")
                                st.success("Data berhasil disetujui. Menu edit untuk catatan ini telah dinonaktifkan.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Gagal menyetujui data: {exc}")

# --------------------------- HISTORY ---------------------------
elif page == "Riwayat Perawatan":
    st.subheader("Riwayat Perawatan per Nomor Sarana")
    f1,f2,f3 = st.columns([1,2,1])
    with f1: type_filter = st.selectbox("Jenis sarana", ["Semua"] + TYPES)
    with f2: number_filter = st.text_input("Cari nomor sarana", placeholder="Ketik nomor sarana...")
    with f3: status_filter = st.selectbox("Status", ["Semua", "SO", "TSO", "Belum ditentukan"])
    f4,f5 = st.columns(2)
    with f4: program_filter = st.multiselect("Program pemeliharaan", PROGRAMS)
    with f5: location_filter = st.text_input("Filter depo / lokasi")
    result = df.copy()
    if type_filter != "Semua": result = result[result["Jenis Sarana"].astype(str).str.upper() == type_filter.upper()]
    if number_filter.strip(): result = result[result["Nomor Sarana"].astype(str).str.contains(number_filter.strip(), case=False, na=False)]
    if status_filter != "Semua": result = result[result["Status SO/TSO"].astype(str) == status_filter]
    if program_filter: result = result[result["Program Pemeliharaan"].isin(program_filter)]
    if location_filter.strip(): result = result[result["Depo/Lokasi"].astype(str).str.contains(location_filter.strip(), case=False, na=False)]
    st.caption(f"Ditemukan {len(result):,} catatan")
    if len(result):
        result = result.copy()
        result["_date"] = pd.to_datetime(result["Tanggal Perawatan"], errors="coerce")
        result = result.sort_values("_date", ascending=False).drop(columns="_date")
        visible = [c for c in ["Tanggal Perawatan","Jenis Sarana","Nomor Sarana","Program Pemeliharaan","P24/P48 Terakhir","Depo/Lokasi","Status SO/TSO","Status Approval","Disetujui Oleh","Nama Petugas","Foto Sebelum","Foto Sesudah"] if c in result]
        st.dataframe(result[visible], use_container_width=True, hide_index=True, column_config={
            "Foto Sebelum":st.column_config.LinkColumn("Foto sebelum", display_text="Buka foto"),
            "Foto Sesudah":st.column_config.LinkColumn("Foto sesudah", display_text="Buka foto"),
        })
        options = sorted(result["Nomor Sarana"].astype(str).unique().tolist())
        selected = st.selectbox("Tampilkan detail riwayat sarana", ["-- Pilih nomor sarana --"] + options)
        if selected != "-- Pilih nomor sarana --":
            detail = result[result["Nomor Sarana"].astype(str) == selected]
            st.markdown(f"### Riwayat {selected}")
            for _, row in detail.iterrows():
                title = f"{row['Tanggal Perawatan']} · {row['Program Pemeliharaan']} · {row['Status SO/TSO']} · ID {row['ID']}"
                with st.expander(title):
                    x,y = st.columns(2)
                    with x:
                        st.write("**Identitas**")
                        st.write(f"Jenis: {row['Jenis Sarana']} | Lokasi: {row['Depo/Lokasi']}")
                        st.write(f"Mulai dinas: {row['Mulai Dinas']} | P24/P48 Terakhir: {row['P24/P48 Terakhir']}")
                        st.write(f"Bogie 1: {row['Nomor Bogie 1']} | Bogie 2: {row['Nomor Bogie 2']}")
                        st.write("**Kondisi dan tindakan**")
                        st.write("Sebelum:", row["Kondisi Sebelum"])
                        st.write("Tindakan:", row["Tindakan Perawatan"])
                        st.write("Sesudah:", row["Kondisi Sesudah"])
                    with y:
                        st.write("**Pemeriksaan komponen**")
                        st.write(f"Knuckle B1/B2: {row['Keausan Knuckle Bogie 1']} / {row['Keausan Knuckle Bogie 2']}")
                        if str(row["Jenis Sarana"]).upper() == "GD":
                            st.write(f"Empty Load: {row['Kelengkapan Emptyload']}")
                        st.write(f"Tebal Center Plate: {row.get('Tebal Center Plate', '')} | Boffer: {row['Tinggi Boffer']}")
                        st.write(f"Brake: {row['Brake']} | Release: {row['Release']} | Langkah torak: {row['Langkah Torak']}")
                        st.write(f"AC: {row['AC']} | CD: {row['CD']} | Tekanan BC: {row['Tekanan BC']}")
                        st.write(f"Petugas: {row['Nama Petugas']} | NIPP: {row['NIPP']}")
                    if str(row["Jenis Sarana"]).upper() == "B":
                        st.markdown("**Pengukuran khusus Sarana B**")
                        for component in ("Tinggi Frame", "Axle Box"):
                            for bn in (1, 2):
                                vals = [{"Posisi": f"Roda {rn}", "Hasil Ukur": row.get(f"{component} B{bn} R{rn}", "")} for rn in range(1, 5)]
                                st.write(f"{component} — Bogie {bn}")
                                st.dataframe(pd.DataFrame(vals), use_container_width=True, hide_index=True)
                        for bn in (1, 2):
                            vals = [{"Nomor": f"Nomor {n}", "Hasil Ukur": row.get(f"Spring Plank B{bn} N{n}", "")} for n in (1, 2)]
                            st.write(f"Spring Plank — Bogie {bn}")
                            st.dataframe(pd.DataFrame(vals), use_container_width=True, hide_index=True)
                    for bn in (1,2):
                        rows = []
                        for rn in range(1,5):
                            rows.append({"Roda":f"Roda {rn}","Diameter":row.get(f"Diameter B{bn} R{rn}",""),"Flens":row.get(f"Flens B{bn} R{rn}",""),"Bidang Jalan":row.get(f"Bidang Jalan B{bn} R{rn}","")})
                        st.markdown(f"**Hasil pengukuran Bogie {bn}**")
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    if row["Foto Sebelum"]: st.markdown(f"[📷 Buka foto sebelum]({row['Foto Sebelum']})")
                    if row["Foto Sesudah"]: st.markdown(f"[📷 Buka foto sesudah]({row['Foto Sesudah']})")
                    if row["Lain-lain"]: st.write("**Lain-lain:**", row["Lain-lain"])
                    if row["Keterangan"]: st.write("**Keterangan:**", row["Keterangan"])
                    st.caption(f"Dibuat: {row['Waktu Input']} | ID: {row['ID']}")
    else:
        st.info("Data tidak ditemukan. Periksa kembali filter pencarian.")

# --------------------------- REPORT ---------------------------
elif page == "Laporan Otomatis":
    st.subheader("Laporan dan Rekapitulasi Perawatan")
    if df.empty:
        st.info("Belum ada data untuk dilaporkan.")
    else:
        d1,d2 = st.columns(2)
        with d1: start = st.date_input("Dari tanggal", value=date(date.today().year,1,1), key="report_start")
        with d2: end = st.date_input("Sampai tanggal", value=date.today(), key="report_end")
        if start > end:
            st.error("Tanggal awal tidak boleh melewati tanggal akhir.")
            st.stop()
        r = df.copy()
        parsed = pd.to_datetime(r["Tanggal Perawatan"], errors="coerce")
        r = r[(parsed.dt.date >= start) & (parsed.dt.date <= end)]
        x,y,z = st.columns(3)
        with x: types = st.multiselect("Jenis sarana", sorted([v for v in r["Jenis Sarana"].dropna().astype(str).unique()]), default=sorted([v for v in r["Jenis Sarana"].dropna().astype(str).unique()]))
        with y: programs = st.multiselect("Program", PROGRAMS, default=PROGRAMS)
        with z: statuses = st.multiselect("Status", ["SO","TSO","Belum ditentukan"], default=["SO","TSO","Belum ditentukan"])
        r = r[r["Jenis Sarana"].isin(types) & r["Program Pemeliharaan"].isin(programs) & r["Status SO/TSO"].isin(statuses)]
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Jumlah catatan", f"{len(r):,}")
        m2.metric("GD / GB", f"{int(r['Jenis Sarana'].isin(['GD','GB']).sum()):,}")
        m3.metric("B", f"{int((r['Jenis Sarana']=='B').sum()):,}")
        m4.metric("TSO", f"{int((r['Status SO/TSO']=='TSO').sum()):,}")
        if len(r):
            left,right = st.columns(2)
            with left:
                st.markdown("#### Rekap program pemeliharaan")
                st.bar_chart(r["Program Pemeliharaan"].value_counts())
            with right:
                st.markdown("#### Rekap status sarana")
                st.bar_chart(r["Status SO/TSO"].value_counts())
            st.markdown("#### Data sesuai filter")
            st.dataframe(r, use_container_width=True, hide_index=True)
            safe_start, safe_end = start.isoformat(), end.isoformat()
            st.download_button("⬇️ Unduh CSV", r.to_csv(index=False).encode("utf-8-sig"), file_name=f"laporan_perawatan_{safe_start}_{safe_end}.csv", mime="text/csv")
            st.download_button("⬇️ Unduh Excel", make_excel(r), file_name=f"laporan_perawatan_{safe_start}_{safe_end}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("Tidak ada data sesuai filter yang dipilih.")

st.markdown("<hr><div class='small-muted'>Sistem Data Perawatan Sarana · Simpan data sesuai hasil pemeriksaan aktual · Periksa kembali catatan sebelum dikirim</div>", unsafe_allow_html=True)
