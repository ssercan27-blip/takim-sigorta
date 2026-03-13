import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI YÖNETİMİ ---
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "sercan": {"pw": "takim2026", "role": "admin"},
        "admin": {"pw": "admin44", "role": "admin"}
    }

# --- SABİT LİSTELER ---
KOMISYON_ORANLARI = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# --- LOGO KONTROL ---
def get_logo():
    for ext in ["jpg", "png", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['police_no', 'musteri_adi', 'sigorta_sirketi', 'police_turu', 'brut_prim', 'net_komisyon', 'tanzim_tarihi', 'bitis_tarihi', 'arsiv'])
        
        # Sütun isimlerini normalize et
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        return raw_df
    except:
        return pd.DataFrame()

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.subheader("Takim Sigorta Giriş")
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("SİSTEMİ BAŞLAT", use_container_width=True):
            if u in st.session_state.users_db and st.session_state.users_db[u]["pw"] == p:
                st.session_state.authenticated = True
                st.session_state.username = u
                st.rerun()
            else: st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- ANA PROGRAM ---
df = load_data()
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
choice = st.sidebar.radio("İşlem Menüsü", ["📝 Yeni Poliçe", "🔎 Poliçe Takibi", "📊 Analiz"])

if choice == "📝 Yeni Poliçe":
    st.markdown("### 📝 Yeni Poliçe Kayıt Ekranı")
    
    with st.form("yeni_police_formu", clear_on_submit=True):
        col1, col2 = st.columns(2)
        p_no = col1.text_input("Poliçe Numarası")
        m_adi = col2.text_input("Müşteri Ad Soyad")
        
        col3, col4, col5 = st.columns(3)
        sirket = col3.selectbox("Şirket", ["Aksigorta", "Allianz", "Anadolu", "Axa", "Türkiye", "Diğer"])
        brans = col4.selectbox("Branş", list(KOMISYON_ORANLARI.keys()))
        prim = col5.number_input("Brüt Prim (TL)", min_value=0.0)
        
        tanzim = st.date_input("Tanzim Tarihi", datetime.now())
        bitis = tanzim + relativedelta(years=1)
        
        st.write(f"💡 Otomatik Vade Sonu: **{bitis.strftime('%d.%m.%Y')}**")
        
        if st.form_submit_button("✅ POLİÇEYİ KAYDET"):
            if p_no and m_adi and prim > 0:
                kazanc = prim * (KOMISYON_ORANLARI[brans] / 100)
                new_row = pd.DataFrame([{
                    "police_no": str(p_no), "musteri_adi": m_adi.upper(), "sigorta_sirketi": sirket,
                    "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc,
                    "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"), "bitis_tarihi": bitis.strftime("%Y-%m-%d"),
                    "arsiv": False
                }])
                conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("Poliçe başarıyla kaydedildi!")
                st.rerun()
            else:
                st.error("Lütfen tüm alanları doldurun!")

# Diğer menüler için boş iskelet (bozulmaması için)
elif choice == "🔎 Poliçe Takibi":
    st.info("Bu bölüm bir sonraki adımda entegre edilecektir. Şu an 'Yeni Poliçe' aktif.")

elif choice == "📊 Analiz":
    st.info("Bu bölüm bir sonraki adımda entegre edilecektir. Şu an 'Yeni Poliçe' aktif.")

