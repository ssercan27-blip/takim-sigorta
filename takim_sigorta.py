import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. FONKSİYONLAR VE LOGO (EN ÜSTTE) ---
def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"):
            return f"logo.{ext}"
    return None

logo_file = get_logo()

# Tarayıcı sekmesi ve Favicon
st.set_page_config(
    page_title="Takim Sigorta | Yönetim",
    page_icon=logo_file if logo_file else "🛡️",
    layout="wide"
)

# --- 2. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        # Sütun isimlerini boşluksuz ve küçük harf yap (Hata önleyici)
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 3. GİRİŞ SİSTEMİ (YÖNETİCİ KİLİDİ BURADA) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None # Başlangıçta yetki yok

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026":
                st.session_state.authenticated = True
                st.session_state.username = "sercan"
                st.session_state.role = "admin" # Admin yetkisi mühürlendi
                st.rerun()
            elif u == "personel" and p == "takim2024":
                st.session_state.authenticated = True
                st.session_state.username = "personel"
                st.session_state.role = "user"
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- 4. ANA MENÜ YAPISI ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)
st.sidebar.markdown(f"**Giriş:** {st.session_state.username.upper()}")

# Menü Seçenekleri
menu_items = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "💳 Ödeme & Cari": "odeme",
    "📊 Analiz": "analiz"
}

# EĞER ADMİN İSE YÖNETİCİ PANELİNİ EKLE (Hatasız Kontrol)
if st.session_state.role == "admin":
    menu_items["🔐 Yönetici Paneli"] = "admin"

choice = menu_items[st.sidebar.radio("İŞLEM MERKEZİ", list(menu_items.keys()))]

# --- 5. SAYFA İÇERİKLERİ ---

# --- YENİ POLİÇE (Tanzim, Başlangıç, Plaka/TC Hepsi Burada) ---
if choice == "yeni":
    st.subheader("📝 Yeni Poliçe Kayıt")
    with st.form("yeni_kayit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        brans = c4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        plaka = c5.text_input("Plaka / TC No")
        
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim Tarihi", datetime.now())
        basla = c7.date_input("Başlangıç Tarihi", datetime.now())
        
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Poliçe Toplam Tutarı (TL)", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret (TL)", min_value=0.0)
        
        tel = st.text_input("Müşteri Telefon (WhatsApp)")
        ref = st.text_input("Referans / Aracı")
        notlar = st.text_area("Poliçe Notları")
        
        if st.form_submit_button("✅ SİSTEME VE GOOGLE SHEETS'E KAYDET"):
            bitis = basla + relativedelta(years=1)
            new_row = pd.DataFrame([{
                "police_no": p_no, "müşteri_adı": m_adi.upper(), "sigorta_sirketi": sirket,
                "poliçe_türü": brans, "plaka_tc": plaka.upper(), "telefon": tel,
                "tanzim_tarihi": tanzim.strftime("%d.%m.%Y"),
                "başlangıç_tarihi": basla.strftime("%d.%m.%Y"),
                "bitiş_tarihi": bitis.strftime("%d.%m.%Y"),
                "toplam_tutar": str(t_tutar), "alinan_ucret": str(a_ucret),
                "referans": ref, "kayıt_yapan": st.session_state.username, "arsiv": "FALSE", "notlar": notlar
            }])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Kayıt başarıyla eklendi!"); st.rerun()

# --- POLİÇE TAKİBİ ---
elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        # Sadece Arşivlenmemişleri Göster
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"]
        st.dataframe(active_df, use_container_width=True)
    else:
        st.info("Henüz poliçe kaydı bulunmuyor.")

# --- ÖDEME & CARİ ---
elif choice == "odeme":
    st.subheader("💳 Ödeme ve Cari Takip")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
        
        borc = df['toplam_tutar'].sum() - df['alinan_ucret'].sum()
        st.metric("Bekleyen Toplam Tahsilat", f"{borc:,.2f} TL")
        
        st.write("### 📜 Borçlu Müşteri Listesi")
        borclular = df[df['toplam_tutar'] > df['alinan_ucret']]
        st.table(borclular[['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret']])

# --- YÖNETİCİ PANELİ (ADMİN ÖZEL) ---
elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli (Sercan Bey)")
    st.write("Buradan tüm veritabanını Excel gibi görebilir ve silebilirsiniz.")
    st.dataframe(df)
    if st.button("Sistemi Yenile (Veri Çek)"):
        st.rerun()

# Çıkış Butonu
if st.sidebar.button("🔴 Güvenli Çıkış"):
    st.session_state.authenticated = False
    st.rerun()
