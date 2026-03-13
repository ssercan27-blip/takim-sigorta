import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI VE YETKİ TANIMLARI ---
# İstediğin kadar kullanıcı ekleyebilirsin: "kullanici_adi": ["şifre", "rol"]
USER_CREDENTIALS = {
    "sercan": ["takim2026", "admin"],
    "admin": ["admin44", "admin"],
    "personel1": ["12345", "user"] # Bu kullanıcı silemez
}

# --- KOMİSYON VE AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. LOGO VE GİRİŞ KONTROLÜ
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.header("🔑 Yetkili Girişi")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sistemi Başlat", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user][0] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.session_state.role = USER_CREDENTIALS[user][1]
                st.rerun()
            else:
                st.error("Giriş başarısız!")
    st.stop()

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)
page_map = {"Ana Portföy": "Sayfa1", "Ek Kayıtlar": "Sayfa2", "Arşiv": "Sayfa3"}
selected_page = page_map[st.sidebar.selectbox("📂 Veri Tabanı", list(page_map.keys()))]

# VERİ OKUMA
try:
    df = conn.read(worksheet=selected_page, ttl=0)
    # Tarihleri düzelt
    df['tanzim_tarihi'] = pd.to_datetime(df['tanzim_tarihi'], errors='coerce')
    df['bitis_tarihi'] = pd.to_datetime(df['bitis_tarihi'], errors='coerce')
except:
    df = pd.DataFrame()

# MENÜ
menu = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Finansal Analiz": "rapor", "🔔 Vade Takip": "vade"}
choice = menu[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu.keys()))]

if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_kayit", clear_on_submit=True):
        p_no = st.text_input("🔢 Poliçe Numarası")
        c1, c2 = st.columns(2)
        musteri = c1.text_input("👤 Müşteri Adı Soyadı")
        tel = c2.text_input("📱 Telefon")
        brans = st.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0)
        
        st.divider()
        t1, t2 = st.columns(2)
        tanzim = t1.date_input("📅 Tanzim", datetime.now())
        sure = t2.selectbox("⏳ Süre", ["1 Yıllık", "2 Aylık"])
        
        bitis_tarihi = tanzim + (relativedelta(years=1) if sure == "1 Yıllık" else relativedelta(months=2))
        
        if st.form_submit_button("✅ KAYDET"):
            if all([p_no, musteri, tel, prim > 0]):
                oran = KOMISYON_SOZLUGU[brans]
                kazanc = prim * (oran / 100)
                new_row = pd.DataFrame([{
                    "kayit_yapan": st.session_state.username, "police_no": str(p_no), "musteri_adi": musteri,
                    "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc,
                    "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"), "bitis_tarihi": bitis_tarihi.strftime("%Y-%m-%d"), "telefon": tel
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet=selected_page, data=updated_df)
                st.success("Kaydedildi!")
                st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    
    # SİLME PANELİ (SADECE ADMİN GÖRÜR)
    if st.session_state.role == "admin":
        with st.expander("🗑️ Kayıt Silme Paneli (Yalnızca Admin)", expanded=False):
            st.warning("Dikkat! Buradan silinen kayıtlar geri getirilemez.")
            delete_no = st.selectbox("Silinecek Poliçe Numarasını Seçin", ["Seçiniz..."] + df['police_no'].astype(str).tolist())
            if st.button("Seçili Poliçeyi Tamamen Sil", type="primary"):
                if delete_no != "Seçiniz...":
                    # Kaydı bul ve sil
                    new_df = df[df['police_no'].astype(str) != delete_no]
                    conn.update(worksheet=selected_page, data=new_df)
                    st.success(f"{delete_no} nolu poliçe silindi.")
                    st.rerun()
    
    # Arama ve Liste
    search = st.text_input("🔍 İsim veya Poliçe No ile Ara")
    if not df.empty:
        f_df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)] if search else df
        st.dataframe(f_df.sort_values('tanzim_tarihi', ascending=False), use_container_width=True, hide_index=True)

# ... (Vade takip ve Analiz kısımları aynı mantıkla devam eder)
