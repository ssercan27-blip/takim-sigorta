import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. AYARLAR VE LOGO ---
def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

logo_file = get_logo()
st.set_page_config(page_title="Takim Sigorta | İşlem Merkezi", page_icon=logo_file if logo_file else "🛡️", layout="wide")

# --- 2. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        # Sütunları normalize et (Boşlukları ve büyük/küçük harf hatalarını gider)
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 3. KULLANICI VE GİRİŞ SİSTEMİ ---
if "users_db" not in st.session_state:
    st.session_state.users_db = [
        {"kullanici": "sercan", "sifre": "takim2026", "yetki": "Admin"},
        {"kullanici": "personel", "sifre": "takim2024", "yetki": "Personel"}
    ]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Kullanıcı").lower()
        p_in = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            user = next((item for item in st.session_state.users_db if item["kullanici"] == u_in and item["sifre"] == p_in), None)
            if user:
                st.session_state.update({"authenticated": True, "username": u_in, "role": user["yetki"]})
                st.rerun()
            else: st.error("Hatalı Giriş!")
    st.stop()

# --- 4. ANA YAPI (MENÜ VE VERİ) ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)
st.sidebar.markdown(f"**Hoş geldin, {st.session_state.username.upper()}**")

# Menü Tanımı (EKSİKSİZ LİSTE)
menu = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "💳 Ödeme & Cari": "odeme",
    "📊 Analiz": "analiz"
}

# Eğer Admin (Sercan) ise Yönetici Panelini Ekle
if st.session_state.role == "Admin":
    menu["🔐 Yönetici Paneli"] = "admin"

choice = menu[st.sidebar.radio("İŞLEM MERKEZİ", list(menu.keys()))]

# --- 5. SAYFA İÇERİKLERİ ---

# --- YENİ POLİÇE ---
if choice == "yeni":
    st.subheader("📝 Yeni Poliçe Kayıt")
    with st.form("yeni_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        brans = c4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        plaka = c5.text_input("Plaka / TC No")

        # Tikleme ile Süre Seçimi
        is_two_months = st.checkbox("⚠️ Bu Poliçe 2 Aylıktır (İşaretlenmezse 1 yıl hesaplanır)")
        
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim Tarihi", datetime.now())
        basla = c7.date_input("Başlangıç Tarihi", datetime.now())
        
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Toplam Poliçe Tutarı (TL)", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret (TL)", min_value=0.0)
        tel = st.text_input("Müşteri Telefon (5xxxxxxxxx)")
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            # Tarih Hesaplama
            bitis = basla + relativedelta(months=2) if is_two_months else basla + relativedelta(years=1)
            
            new_row = pd.DataFrame([{
                "police_no": p_no, "müşteri_adı": m_adi.upper(), "sigorta_sirketi": sirket, 
                "poliçe_türü": brans, "plaka_tc": plaka.upper(), "telefon": tel, 
                "tanzim_tarihi": tanzim.strftime("%d.%m.%Y"), 
                "başlangıç_tarihi": basla.strftime("%d.%m.%Y"), 
                "bitiş_tarihi": bitis.strftime("%d.%m.%Y"), 
                "toplam_tutar": t_tutar, "alinan_ucret": a_ucret, 
                "arsiv": "FALSE", "kayıt_yapan": st.session_state.username
            }])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Kayıt Başarılı!"); st.rerun()

# --- POLİÇE TAKİBİ ---
elif choice == "takip":
    st.subheader("🔎 Aktif Poliçe Takibi")
    if not df.empty:
        # Sadece Arşivlenmemiş (FALSE) olanları göster
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"].copy()
        if not active_df.empty:
            for i, row in active_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([0.8, 0.2])
                    col1.markdown(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Vade: **{row['bitiş_tarihi']}**")
                    col1.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']} | 👤 Kaydeden: {row['kayıt_yapan']}")
                    wa_link = f"https://wa.me/90{row['telefon']}?text=Merhaba%20{row['müşteri_adı']},%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolmaktadır."
                    col2.link_button("💬 WhatsApp", wa_link, use_container_width=True)
        else: st.info("Şu an takip edilecek aktif bir kayıt bulunmuyor.")

# --- ÖDEME & CARİ ---
elif choice == "odeme":
    st.subheader("💳 Ödeme ve Cari Durum")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
        toplam_borc = df['toplam_tutar'].sum() - df['alinan_ucret'].sum()
        st.metric("Bekleyen Toplam Tahsilat", f"{toplam_borc:,.2f} TL")
        borclular = df[df['toplam_tutar'] > df['alinan_ucret']]
        st.write("### 📜 Borçlu Listesi")
        st.table(borclular[['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret']])

# --- ANALİZ ---
elif choice == "analiz":
    st.subheader("📊 Portföy Analizi")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(df, names='sigorta_sirketi', title="Şirket Bazlı Dağılım"))
        c2.plotly_chart(px.bar(df, x='poliçe_türü', y='toplam_tutar', title="Branş Bazlı Ciro"))

# --- YÖNETİCİ PANELİ ---
elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    tab_u, tab_d = st.tabs(["👤 Kullanıcı Yönetimi", "🗂️ Tüm Veritabanı"])
    with tab_u:
        st.write("### Mevcut Kullanıcılar")
        st.table(pd.DataFrame(st.session_state.users_db))
        with st.expander("Yeni Personel Ekle / Güncelle"):
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre")
            y = st.selectbox("Yetki", ["Admin", "Personel"])
            if st.button("Kaydet"):
                st.session_state.users_db = [usr for usr in st.session_state.users_db if usr["kullanici"] != u]
                st.session_state.users_db.append({"kullanici": u, "sifre": p, "yetki": y})
                st.success("Kullanıcı listesi güncellendi!"); st.rerun()
    with tab_d:
        st.write("### Ham Veri (Google Sheets)")
        st.dataframe(df)

if st.sidebar.button("🔴 Güvenli Çıkış"):
    st.session_state.authenticated = False; st.rerun()
