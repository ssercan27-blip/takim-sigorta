import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta - Komisyon Yönetimi", layout="centered")

# --- GÜNCEL KOMİSYON ORANLARI ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50,
    "Kasko": 9.50,
    "Konut": 20.00,
    "İşyeri": 12.00,
    "DASK": 9.75,
    "TSS": 16.25,
    "Yol yardım": 16.25,
    "Mali Sorumluluk": 6.50,
    "Diğer": 10.00  # Diğer seçeneği geri eklendi
}

# 1. LOGO ALANI
if os.path.exists("logo.jpg"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.jpg", use_container_width=True)
else:
    st.markdown("<h1 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h1>", unsafe_allow_html=True)

# 2. KULLANICI BİLGİLERİ
USER_CREDENTIALS = {"sercan": "takim2026", "admin": "admin44"}

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.divider()
        st.subheader("🔑 Personel Giriş Paneli")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    st.sidebar.title("📌 İşlem Merkezi")
    selected_page = st.sidebar.selectbox("Çalışılacak Sayfa", ["Sayfa1", "Sayfa2", "Sayfa3", "Sayfa4"])
    menu = ["Poliçe Kaydet", "Finansal Rapor"]
    choice = st.sidebar.radio("Menü", menu)
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

    # --- VERİ OKUMA ---
    try:
        df = conn.read(worksheet=selected_page, ttl=0)
    except:
        df = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'kaynak', 'brut_prim', 'oran', 'net_komisyon', 'vade_tarihi'])

    if choice == "Poliçe Kaydet":
        st.header(f"📝 {selected_page} - Yeni Kayıt")
        with st.form("kayit_formu", clear_on_submit=True):
            musteri_adi = st.text_input("Müşteri Adı Soyadı")
            police_turu = st.selectbox("Branş / Poliçe Türü", list(KOMISYON_SOZLUGU.keys()))
            kaynak = st.radio("Poliçe Kaynağı", ["Öz Portföy", "Dış Acente"])
            brut_prim = st.number_input("Brüt Prim (TL)", min_value=0.0, step=100.0)
            vade_tarihi = st.date_input("Vade Bitiş Tarihi")
            
            submit = st.form_submit_button("Hesapla ve Kaydet")
            
            if submit:
                if musteri_adi:
                    ana_oran = KOMISYON_SOZLUGU[police_turu]
                    uygulanan_oran = ana_oran / 2 if kaynak == "Dış Acente" else
