import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. FONKSİYONLAR (Hata almamak için en üstte olmalı) ---

def get_logo():
    """Klasördeki logoyu bulur."""
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"):
            return f"logo.{ext}"
    return None

# Fonksiyonu tanımladık, şimdi logoyu değişkene alabiliriz
logo_file = get_logo()

# --- 2. SAYFA AYARLARI (Sekme Logosu Burada Çözüldü) ---
st.set_page_config(
    page_title="Takim Sigorta | İşlem Merkezi",
    page_icon=logo_file if logo_file else "🛡️",
    layout="wide"
)

# --- 3. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if df is None or df.empty:
            df = pd.DataFrame()
        # Sütun isimlerini normalize et
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        
        # Eksik sütunları zırh olarak ekle
        required = ['police_no', 'müşteri_adı', 'sigorta_sirketi', 'poliçe_türü', 'plaka_tc', 
                    'telefon', 'tanzim_tarihi', 'başlangıç_tarihi', 'bitiş_tarihi', 
                    'referans', 'kayıt_yapan', 'arsiv', 'toplam_tutar', 'alinan_ucret', 'odeme_tipi']
        for col in required:
            if col not in df.columns:
                df[col] = "0" if "tutar" in col or "ucret" in col else ("FALSE" if col == 'arsiv' else "")
        return df
    except:
        return pd.DataFrame()

# --- 4. GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026": # Hızlı giriş
                st.session_state.authenticated = True
                st.session_state.username = u
                st.rerun()
            else: st.error("Hatalı giriş!")
    st.stop()

# --- 5. ANA EKRAN ---
df = load_data_safe()

# Yan Menü
if logo_file: st.sidebar.image(logo_file, use_container_width=True)
st.sidebar.markdown(f"**Yetkili:** {st.session_state.username.upper()}")

menu = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "💳 Ödeme & Cari": "odeme",
    "📊 Analiz": "analiz"
}
choice = menu[st.sidebar.radio("İşlem Merkezi", list(menu.keys()))]

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

# --- 6. SAYFALAR ---

if choice == "yeni":
    st.subheader("📝 Yeni Poliçe ve Ödeme Kaydı")
    with st.form("yeni_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Diğer"])
        brans = c4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT"])
        plaka = c5.text_input("Plaka / TC")
        
        c6, c7 = st.columns(2)
        t_tutar = c6.number_input("Toplam Poliçe Tutarı (TL)", min_value=0.0)
        a_ucret = c7.number_input("Alınan Ücret (TL)", min_value=0.0)
        
        tel = st.text_input("Telefon (WhatsApp)")
        
        if st.form_submit_button("✅ KAYDET VE SHEETS'E GÖNDER"):
            bitis = datetime.now() + relativedelta(years=1)
            new_row = pd.DataFrame([{
                "police_no": p_no, "müşteri_adı": m_adi.upper(), "sigorta_sirketi": sirket,
                "poliçe_türü": brans, "plaka_tc": plaka.upper(), "telefon": tel,
                "tanzim_tarihi": datetime.now().strftime("%d.%m.%Y"),
                "bitiş_tarihi": bitis.strftime("%d.%m.%Y"),
                "toplam_tutar": str(t_tutar), "alinan_ucret": str(a_ucret),
                "odeme_tipi": "Nakit/Kredi Kartı", "arsiv": "FALSE", "kayıt_yapan": st.session_state.username
            }])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Kayıt Başarılı!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Aktif Poliçeler")
    active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"]
    st.dataframe(active_df[['police_no', 'müşteri_adı', 'plaka_tc', 'bitiş_tarihi']], use_container_width=True)

elif choice == "odeme":
    st.subheader("💳 Ödeme ve Cari Takip")
    # Cari hesaplama
    df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
    df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
    
    col1, col2 = st.columns(2)
    col1.metric("Toplam Tahsilat", f"{df['alinan_ucret'].sum():,.2f} TL")
    col2.metric("Bekleyen Bakiyeler", f"{(df['toplam_tutar'].sum() - df['alinan_ucret'].sum()):,.2f} TL")
    
    st.write("### Detaylı Liste")
    st.table(df[df['toplam_tutar'] > df['alinan_ucret']][['müşteri_adı', 'toplam_tutar', 'alinan_ucret']])

elif choice == "analiz":
    st.info("Veriler biriktikçe grafikler burada oluşacak.")
