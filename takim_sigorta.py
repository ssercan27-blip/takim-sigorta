import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI VE YETKİ TANIMLARI ---
USER_CREDENTIALS = {
    "sercan": ["takim2026", "admin"],
    "admin": ["admin44", "admin"]
}

# --- KOMİSYON SÖZLÜĞÜ ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. OTURUM BAŞLATMA
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None

# 2. GİRİŞ KONTROLÜ
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
WORKSHEET_NAME = "Sayfa1" 

def load_data():
    try:
        raw_df = conn.read(worksheet=WORKSHEET_NAME, ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame()
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        for col in ['tanzim_tarihi', 'bitis_tarihi']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_datetime(raw_df[col], errors='coerce')
        return raw_df
    except:
        return pd.DataFrame()

df = load_data()

# SIDEBAR
st.sidebar.markdown(f"👤 Yetkili: **{st.session_state.username.upper()}**")
menu = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi / Düzenle": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}
choice = menu[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu.keys()))]

# --- SAYFALAR ---

if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_kayit", clear_on_submit=True):
        p_no = st.text_input("🔢 Poliçe Numarası")
        c1, c2 = st.columns(2)
        musteri = c1.text_input("👤 Müşteri Adı Soyadı")
        tel = c2.text_input("📱 Telefon")
        brans = st.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0)
        
        t1, t2 = st.columns(2)
        # TARİH FORMATI: GÜN AY YIL
        tanzim = t1.date_input("📅 Tanzim Tarihi", datetime.now(), format="DD/MM/YYYY")
        sure = t2.selectbox("⏳ Süre", ["1 Yıllık", "2 Aylık"])
        
        bitis_tarihi = tanzim + (relativedelta(years=1) if sure == "1 Yıllık" else relativedelta(months=2))
        st.info(f"💡 Hesaplanan Vade Sonu: {bitis_tarihi.strftime('%d.%m.%Y')}")
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            if all([p_no, musteri, tel, prim > 0]):
                kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
                new_row = pd.DataFrame([{
                    "kayit_yapan": st.session_state.username, "police_no": str(p_no), "musteri_adi": musteri,
                    "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc,
                    "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"), "bitis_tarihi": bitis_tarihi.strftime("%Y-%m-%d"), "telefon": tel
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet=WORKSHEET_NAME, data=updated_df)
                st.success("Kayıt Başarılı!")
                st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi ve Yönetimi")
    
    if not df.empty:
        # --- DÜZENLEME VE SİLME BÖLÜMÜ ---
        with st.expander("🛠️ Kayıt Düzenle veya Sil", expanded=False):
            st.info("Düzenlemek veya silmek istediğiniz poliçeyi seçin.")
            secilen_no = st.selectbox("Poliçe Seçin", ["Seçiniz..."] + sorted(df['police_no'].astype(str).unique().tolist()))
            
            if secilen_no != "Seçiniz...":
                # Seçilen poliçenin verilerini getir
                idx = df[df['police_no'].astype(str) == secilen_no].index[0]
                row = df.loc[idx]
                
                with st.form("duzenleme_formu"):
                    u_musteri = st.text_input("Müşteri Adı", value=str(row['musteri_adi']))
                    u_prim = st.number_input("Brüt Prim", value=float(row['brut_prim']))
                    u_tanzim = st.date_input("Tanzim Tarihi", value=row['tanzim_tarihi'], format="DD/MM/YYYY")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("💾 DEĞİŞİKLİKLERİ KAYDET"):
                            df.at[idx, 'musteri_adi'] = u_musteri
                            df.at[idx, 'brut_prim'] = u_prim
                            df.at[idx, 'tanzim_tarihi'] = u_tanzim
                            # Komisyonu yeniden hesapla
                            oran = KOMISY
