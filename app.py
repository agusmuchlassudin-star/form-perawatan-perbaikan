import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO
from uuid import uuid4
import re
import hmac
import json
from urllib.parse import urlsplit
import gspread
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import Flow
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
# OAuth terpisah hanya untuk unggah foto ke Google Drive milik pengguna.
DRIVE_OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive"]
FLEET_TOTAL = 582  # Angka populasi referensi dari pengguna, bukan jumlah transaksi.
FLEET_GERBONG = 527
FLEET_BAGASI = 55
MAX_PHOTO_MB = 10
DATABASE_EDITOR_EMAIL = "spoorslosd@gmail.com"

HEADERS = [
    "ID", "Tanggal Perawatan", "Jenis Sarana", "Nomor Sarana",
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
    "Jenis Pekerjaan", "Kondisi Sebelum", "Tindakan Perawatan", "Kondisi Sesudah",
    "Lain-lain", "Status SO/TSO", "Nama Petugas", "NIPP", "Nama Petugas 2", "NIPP 2", "Nama Petugas 3", "NIPP 3", "Foto Sarana", "Foto Sebelum", "Foto Saat Perbaikan", "Foto Sesudah",
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
