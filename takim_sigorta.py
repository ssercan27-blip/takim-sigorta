import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- AYARLAR VE LİSTELER ---
USER_CREDENTIALS = {"sercan": ["takim2026", "admin"], "admin": ["admin44", "admin"]}
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# --- LOGO KONTROLÜ ---
def get_logo():
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("logo.png"): return "logo.png"
    return None

# --- GİRİŞ EKRANI (LOGOLU) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        logo_path = get_logo()
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🛡️ TAKİM SİGORTA</h1>", unsafe_allow_html=True)
        
        st.markdown("---")
        user = st.text_input("👤 Kullanıcı Adı").lower()
        pw = st.text_input("🔑 Şifre", type="password")
        if st.button("SİSTEMİ BAŞLAT", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user][0] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Giriş bilgileri hatalı!")
    st.stop()

# --- VERİ BAĞLANTISI VE TEMİZLİK ---
conn = st.connection("gsheets", type=GSheetsConnection)
def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        
        # Tarih ve Sayısal Dönüşüm
        for col in ['tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_datetime(raw_df[col], errors='coerce')
        for col in ['brut_prim', 'net_komisyon']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        return raw_df
    except:
        return pd.DataFrame()

df = load_data()

# --- SIDEBAR ---
logo_path = get_logo()
if logo_path: st.sidebar.image(logo_path, use_container_width=True)
st.sidebar.markdown(f"**Yetkili:** {st.session_state.username.upper()}")
menu = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}
choice = menu[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu.keys()))]

# --- SAYFALAR ---
if choice == "takip":
    st.markdown("## 🔎 Poliçe Takibi ve Durum Paneli")
    
    if not df.empty:
        # Excel'deki gibi "Durum" sütunu ekleyelim
        bugun = pd.Timestamp(datetime.now().date())
        
        def durum_belirle(bitis):
            if pd.isnull(bitis): return "⚪ Bilgi Yok"
            kalan = (bitis - bugun).days
            if kalan < 0: return "🔴 Vadesi Geçmiş"
            if kalan <= 15: return "🟡 Vade Yaklaştı"
            return "🟢 Güncel"

        df['durum'] = df['bitis_tarihi'].apply(durum_belirle)

        # Üst Metrikler (Canlı Tasarım)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Kayıt", len(df))
        c2.metric("🟢 Güncel", len(df[df['durum'] == "🟢 Güncel"]))
        c3.metric("🟡 Yaklaşan", len(df[df['durum'] == "🟡 Vade Yaklaştı"]))
        c4.metric("🔴 Geçmiş", len(df[df['durum'] == "🔴 Vadesi Geçmiş"]))

        st.markdown("---")
        
        # Filtreleme Alanı
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            search = st.text_input("🔍 Müşteri, Plaka veya Poliçe No ile Ara")
        with col_f2:
            filtre = st.selectbox("Durum Filtresi", ["Tümü", "🟢 Güncel", "🟡 Vade Yaklaştı", "🔴 Vadesi Geçmiş"])

        # Veriyi Süz
        d_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
        if filtre != "Tümü":
            d_df = d_df[d_df['durum'] == filtre]

        # Excel Benzeri Görsel Tablo
        st.dataframe(
            d_df.sort_values('bitis_tarihi', ascending=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "durum": st.column_config.TextColumn("Durum", help="Poliçenin vade durumu"),
                "musteri_adi": "👤 Müşteri Adı",
                "police_no": "🔢 Poliçe No",
                "police_turu": "📑 Branş",
                "brut_prim": st.column_config.NumberColumn("💰 Prim (TL)", format="%.2f"),
                "bitis_tarihi": st.column_config.DateColumn("🏁 Vade Sonu", format="DD.MM.YYYY"),
                "sigorta_sirketi": "🏢 Şirket",
                "telefon": "📱 Telefon"
            }
        )
    else:
        st.info("Henüz veri girişi yapılmamış.")

# Diğer sayfalar (kaydet, rapor vb.) mevcut yapıda devam eder...
