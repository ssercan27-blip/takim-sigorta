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
    # Sadece senin istediğin o asıl logoyu arar
    for ext in ["jpg", "png", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. VERİ BAĞLANTISI (ZIRHLI SİSTEM) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty:
            raw_df = pd.DataFrame()
        
        # Sütun isimlerini ne olursa olsun normalize et
        raw_df.columns = [str(c).strip().lower() for c in raw_df.columns]
        
        # --- KRİTİK ZIRH: Eğer bu sütunlar yoksa, hata verme, boş olarak yarat ---
        required_columns = ['müşteri adı', 'poliçe türü', 'plaka/tc', 'bitiş tarihi', 'telefon', 'referans', 'arsiv']
        for col in required_columns:
            if col not in raw_df.columns:
                raw_df[col] = False if col == 'arsiv' else ""
        
        return raw_df
    except:
        return pd.DataFrame()

# --- 4. GİRİŞ VE YETKİ KONTROLÜ ---
if "users_db" not in st.session_state:
    st.session_state.users_db = {"sercan": {"pw": "takim2026", "role": "admin"}}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>Giriş Yapın</h3>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u in st.session_state.users_db and st.session_state.users_db[u]["pw"] == p:
                st.session_state.authenticated = True
                st.session_state.username = u
                st.session_state.role = st.session_state.users_db[u]["role"]
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

# --- 5. ANA PROGRAM ---
df = load_data_safe()

# Sidebar Menü
logo_side = get_logo()
if logo_side: st.sidebar.image(logo_side, use_container_width=True)

# İŞLEM MERKEZİ (Sabitlendi)
menu = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "📊 Analiz": "analiz"
}
if st.session_state.role == "admin":
    menu["🔐 Yönetici Paneli"] = "admin"

choice = menu[st.sidebar.radio("İşlem Merkezi", list(menu.keys()))]

# --- 6. SAYFALAR ---

if choice == "yeni":
    st.subheader("📝 Yeni Kayıt Girişi")
    with st.form("yeni_form", clear_on_submit=True):
        m_adi = st.text_input("Müşteri Ad Soyad")
        p_turu = st.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "DİĞER"])
        plaka = st.text_input("Plaka / TC")
        tel = st.text_input("Telefon")
        basla = st.date_input("Başlangıç", datetime.now())
        if st.form_submit_button("✅ KAYDET"):
            bitis = basla + relativedelta(years=1)
            new_row = pd.DataFrame([{
                "müşteri adı": m_adi.upper(), "poliçe türü": p_turu, "plaka/tc": plaka.upper(),
                "bitiş tarihi": bitis.strftime("%d.%m.%Y"), "telefon": tel, "arsiv": False
            }])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Kaydedildi!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    # Zırh: 'arsiv' sütunu load_data_safe içinde garanti edildiği için KeyError vermez
    active_df = df[df['arsiv'] != True]
    if not active_df.empty:
        for i, r in active_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([0.8, 0.2])
                c1.write(f"👤 **{r['müşteri adı']}** | 🚗 {r['plaka/tc']} | 📅 {r['bitiş tarihi']}")
                if c2.button("📁 Arşivle", key=f"arc_{i}"):
                    df.at[i, 'arsiv'] = True
                    conn.update(worksheet="Sayfa1", data=df)
                    st.success("Arşivlendi!"); st.rerun()
    else: st.info("Aktif kayıt yok.")

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    st.write("Kullanıcı Listesi:")
    st.json(st.session_state.users_db)
    # Yeni kullanıcı ekleme alanı
    with st.expander("➕ Kullanıcı Ekle"):
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Şifre")
        if st.button("Ekle"):
            st.session_state.users_db[nu] = {"pw": np, "role": "user"}
            st.success("Eklendi.")
