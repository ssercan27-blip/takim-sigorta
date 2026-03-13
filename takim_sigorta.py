import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. AYARLAR ---
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- 2. LOGO FONKSİYONU ---
def get_logo():
    for ext in ["jpg", "png", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['müşteri_adı', 'poliçe_türü', 'araç_plakası/tc', 'başlangıç_tarihi', 'bitiş_tarihi', 'telefon', 'referans', 'arsiv'])
        # Sütun isimlerini normalize et (Hata önleyici)
        raw_df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in raw_df.columns]
        return raw_df
    except:
        return pd.DataFrame()

# --- 4. GİRİŞ KONTROLÜ (LOGO VE MODERN GİRİŞ) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>🛡️ Takim Sigorta Yönetim Paneli</h3>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026":
                st.session_state.authenticated = True
                st.session_state.username = u
                st.rerun()
            else: st.error("Bilgiler hatalı!")
    st.stop()

# --- 5. ANA PROGRAM ---
df = load_data()

# Kenar Menüsü
logo_side = get_logo()
if logo_side: st.sidebar.image(logo_side, use_container_width=True)
st.sidebar.markdown(f"**Yetkili:** {st.session_state.username.upper()}")

# İŞLEM MERKEZİ (Tam Liste)
menu_options = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "📊 Analiz": "analiz",
    "🔔 Vade Takip": "vade"
}
choice = menu_options[st.sidebar.radio("İşlem Merkezi", list(menu_options.keys()))]

if st.sidebar.button("🔴 Güvenli Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

# --- 6. SAYFA İÇERİKLERİ ---

if choice == "yeni":
    st.subheader("📝 Yeni Poliçe Kayıt (Excel Formatlı)")
    with st.form("yeni_police_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        m_adi = col1.text_input("Müşteri Ad Soyad")
        p_turu = col2.selectbox("Poliçe Türü", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "DİĞER"])
        
        col3, col4 = st.columns(2)
        plaka = col3.text_input("Araç Plakası / TC")
        tel = col4.text_input("Telefon (WhatsApp için)")
        
        col5, col6 = st.columns(2)
        basla = col5.date_input("Başlangıç Tarihi", datetime.now())
        ref = col6.text_input("Referans")
        
        notlar = st.text_area("Poliçe Notu")
        
        if st.form_submit_button("✅ POLİÇEYİ SİSTEME KAYDET", use_container_width=True):
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
                    "notlar": notlar,
                    "arsiv": False
                }])
                conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
                st.success(f"Başarılı! {m_adi.upper()} sisteme eklendi.")
            else: st.warning("Lütfen zorunlu alanları (İsim ve Telefon) doldurun!")

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        # Sadece arşive gitmemişleri gösteriyoruz
        active_df = df[df['arsiv'] != True].copy()
        st.dataframe(active_df, use_container_width=True)
    else: st.info("Gösterilecek aktif kayıt bulunmuyor.")

elif choice == "analiz":
    st.subheader("📊 Analiz")
    st.info("Kayıtlar biriktikçe finansal tablolarınız burada görünecek.")

elif choice == "vade":
    st.subheader("🔔 Vade Takip")
    st.info("Vadesi yaklaşan poliçeler burada listelenecek.")
