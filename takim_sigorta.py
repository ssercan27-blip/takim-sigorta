import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. FONKSİYONLAR VE LOGO AYARI ---
def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"):
            return f"logo.{ext}"
    return None

logo_file = get_logo()

# Tarayıcı sekmesindeki logo (Favicon)
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
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 3. GİRİŞ SİSTEMİ ---
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
            if u == "sercan" and p == "takim2026": # Senin ana girişin
                st.session_state.authenticated = True
                st.session_state.username = "sercan"
                st.session_state.role = "admin"
                st.rerun()
            elif u == "personel" and p == "takim2024":
                st.session_state.authenticated = True
                st.session_state.username = "personel"
                st.session_state.role = "user"
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

# --- 4. ANA MENÜ VE YÖNETİCİ KONTROLÜ ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)

menu_options = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "💳 Ödeme & Cari": "odeme",
    "📊 Analiz": "analiz"
}

# Sadece admin (Sercan) ise Yönetici Panelini göster
if st.session_state.get("role") == "admin":
    menu_options["🔐 Yönetici Paneli"] = "admin"

choice = menu_options[st.sidebar.radio("İşlem Merkezi", list(menu_options.keys()))]

# --- 5. SAYFALAR ---

if choice == "yeni":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_police_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        p_no = col1.text_input("Poliçe No")
        m_adi = col2.text_input("Müşteri Ad Soyad")
        
        col3, col4, col5 = st.columns(3)
        sirket = col3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        brans = col4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        plaka = col5.text_input("Plaka / TC No")
        
        col6, col7 = st.columns(2)
        tanzim = col6.date_input("Tanzim Tarihi", datetime.now())
        basla = col7.date_input("Başlangıç Tarihi", datetime.now())
        
        col8, col9 = st.columns(2)
        t_tutar = col8.number_input("Poliçe Tutarı (TL)", min_value=0.0)
        a_ucret = col9.number_input("Alınan Ücret (TL)", min_value=0.0)
        
        tel = st.text_input("Müşteri Telefon (WhatsApp)")
        ref = st.text_input("Referans")
        
        if st.form_submit_button("✅ SİSTEME KAYDET", use_container_width=True):
            bitis = basla + relativedelta(years=1)
            new_row = pd.DataFrame([{
                "police_no": p_no, "müşteri_adı": m_adi.upper(), "sigorta_sirketi": sirket,
                "poliçe_türü": brans, "plaka_tc": plaka.upper(), "telefon": tel,
                "tanzim_tarihi": tanzim.strftime("%d.%m.%Y"),
                "başlangıç_tarihi": basla.strftime("%d.%m.%Y"),
                "bitiş_tarihi": bitis.strftime("%d.%m.%Y"),
                "toplam_tutar": str(t_tutar), "alinan_ucret": str(a_ucret),
                "referans": ref, "kayıt_yapan": st.session_state.username, "arsiv": "FALSE"
            }])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Kayıt Başarıyla Eklendi!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        active_df = df[df['arsiv'].astype(str).upper() == "FALSE"]
        # Trafik lambası ve WhatsApp butonları burada listelenecek (önceki yapıyla aynı)
        st.dataframe(active_df, use_container_width=True)

elif choice == "odeme":
    st.subheader("💳 Cari Takip ve Ödemeler")
    df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
    df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
    st.metric("Bekleyen Toplam Tahsilat", f"{(df['toplam_tutar'].sum() - df['alinan_ucret'].sum()):,.2f} TL")
    st.write("### Borçlu Listesi")
    borclular = df[df['toplam_tutar'] > df['alinan_ucret']]
    st.table(borclular[['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret']])

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    st.write("Sadece Sercan Bey tarafından görülebilir. Kullanıcı ve Şirket ayarları yakında burada aktif edilecek.")
    if st.button("Tüm Verileri Görüntüle (Excel Modu)"):
        st.dataframe(df)

if st.sidebar.button("🔴 Güvenli Çıkış"):
    st.session_state.authenticated = False
    st.rerun()
