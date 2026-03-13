import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- 1. AYARLAR ---
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- 2. VERİ BAĞLANTISI (ZIRHLI MODEL) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_secure():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty:
            # Excel'indeki o sütunları buraya çiviliyoruz
            cols = ['müşteri_adı', 'poliçe_türü', 'araç_plakası/tc', 'başlangıç_tarihi', 
                    'bitiş_tarihi', 'telefon', 'referans', 'arsiv']
            return pd.DataFrame(columns=cols)
        
        # Sütun isimlerini kodun anlayacağı basit hale getir ama veriyi bozma
        raw_df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in raw_df.columns]
        return raw_df
    except Exception as e:
        # Hata olursa beyaz ekran yerine buraya yazacak
        st.error(f"Veri yükleme hatası: {e}")
        return pd.DataFrame()

# --- 3. GİRİŞ KONTROLÜ (LOGO VS. YOK, SADECE İŞLEV) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.subheader("🔑 Takim Sigorta Giriş")
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if u == "sercan" and p == "takim2026": # En hızlı giriş yolu
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

# --- 4. ANA PROGRAM ---
df = load_data_secure()

# Menüyü kenara alalım
menu = st.sidebar.radio("Menü Seçin", ["📝 Yeni Poliçe", "🔎 Poliçe Takibi"])

if menu == "📝 Yeni Poliçe":
    st.markdown("### 📝 Yeni Kayıt Girişi")
    with st.form("excel_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        m_adi = col1.text_input("Müşteri Ad Soyad")
        p_turu = col2.selectbox("Poliçe Türü", ["TRAFİK", "KASKO", "DASK", "TSS", "DİĞER"])
        
        col3, col4 = st.columns(2)
        plaka = col3.text_input("Plaka veya TC")
        tel = col4.text_input("Telefon (WhatsApp için)")
        
        col5, col6 = st.columns(2)
        basla = col5.date_input("Başlangıç Tarihi", datetime.now())
        referans = col6.text_input("Referans / Not")
        
        # Vadeyi otomatik 1 yıl sonrası yapalım
        bitis = basla + relativedelta(years=1)
        
        if st.form_submit_button("Sisteme İşle", use_container_width=True):
            if m_adi and tel:
                new_data = pd.DataFrame([{
                    "müşteri_adı": m_adi.upper(),
                    "poliçe_türü": p_turu,
                    "araç_plakası_tc": plaka.upper(),
                    "başlangıç_tarihi": basla.strftime("%d.%m.%Y"),
                    "bitiş_tarihi": bitis.strftime("%d.%m.%Y"),
                    "telefon": tel,
                    "referans": referans,
                    "arsiv": False
                }])
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(worksheet="Sayfa1", data=updated_df)
                st.success("Kaydedildi!")
            else: st.warning("Ad ve Telefon zorunlu!")

elif menu == "🔎 Poliçe Takibi":
    st.subheader("🔎 Aktif Poliçeler")
    if not df.empty:
        # Sadece arşive gitmemişleri göster
        active = df[df['arsiv'] != True]
        st.dataframe(active, use_container_width=True)
    else: st.info("Gösterilecek veri yok.")
