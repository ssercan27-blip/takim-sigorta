import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. AYARLAR ---
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- 2. LOGO GETİRME FONKSİYONU ---
def get_main_logo():
    # Klasördeki logoyu arar
    for ext in ["jpg", "png", "jpeg"]:
        if os.path.exists(f"logo.{ext}"):
            return f"logo.{ext}"
    return None

# --- 3. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_secure():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty:
            cols = ['müşteri_adı', 'poliçe_türü', 'araç_plakası/tc', 'başlangıç_tarihi', 'bitiş_tarihi', 'telefon', 'referans', 'arsiv']
            return pd.DataFrame(columns=cols)
        # Sütunları küçük harf ve alt çizgiye çevirerek hata payını yok et
        raw_df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in raw_df.columns]
        return raw_df
    except:
        return pd.DataFrame()

# --- 4. GİRİŞ EKRANI (LOGO BURAYA GERİ GELDİ) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # Sayfayı ortalamak için boş sütunlar kullanıyoruz
    left_co, cent_co, last_co = st.columns([1, 1.2, 1])
    with cent_co:
        logo_path = get_main_logo()
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center;'>🛡️</h1>", unsafe_allow_html=True)
            
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Giriş bilgileri hatalı!")
    st.stop()

# --- 5. ANA SİSTEM ---
df = load_data_secure()

# Sidebar (Yan Menü)
logo_path = get_main_logo()
if logo_path:
    st.sidebar.image(logo_path, use_container_width=True)

menu = st.sidebar.radio("İŞLEM MERKEZİ", ["📝 Yeni Poliçe", "🔎 Poliçe Takibi"])

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

# --- SAYFA İÇERİKLERİ ---
if menu == "📝 Yeni Poliçe":
    st.markdown("### 📝 Yeni Poliçe Kaydı")
    # Form içeriği Excel'indeki alanlara (Plaka, Referans vb.) göre hazır
    with st.form("yeni_kayit"):
        c1, c2 = st.columns(2)
        m_adi = c1.text_input("Müşteri Ad Soyad")
        p_turu = c2.selectbox("Poliçe Türü", ["TRAFİK", "KASKO", "DASK", "KONUT", "TSS", "DİĞER"])
        
        c3, c4 = st.columns(2)
        plaka = c3.text_input("Araç Plakası / TC")
        tel = c4.text_input("Telefon Numarası")
        
        c5, c6 = st.columns(2)
        basla = c5.date_input("Başlangıç Tarihi", datetime.now())
        ref = c6.text_input("Referans")
        
        if st.form_submit_button("✅ KAYDET", use_container_width=True):
            if m_adi and tel:
                bitis = basla + relativedelta(years=1)
                new_row = pd.DataFrame([{
                    "müşteri_adı": m_adi.upper(),
                    "poliçe_türü": p_turu,
                    "araç_plakası_tc": plaka.upper(),
                    "başlangıç_tarihi": basla.strftime("%d.%m.%Y"),
                    "bitiş_tarihi": bitis.strftime("%d.%m.%Y"),
                    "telefon": tel,
                    "referans": ref,
                    "arsiv": False
                }])
                conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("Kayıt başarıyla Google Sheets'e eklendi!")
            else:
                st.warning("Eksik bilgi bırakmayın!")

elif menu == "🔎 Poliçe Takibi":
    st.subheader("🔎 Aktif Kayıtlar")
    if not df.empty:
        # Sadece aktifleri göster
        st.dataframe(df[df['arsiv'] != True], use_container_width=True)
    else:
        st.info("Henüz kayıt bulunmuyor.")
