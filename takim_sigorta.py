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
st.set_page_config(page_title="Takim Sigorta | Yönetim", page_icon=logo_file if logo_file else "🛡️", layout="wide")

# --- 2. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 3. KULLANICI YÖNETİMİ ---
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
        st.markdown("<h2 style='text-align: center;'>Giriş Paneli</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Kullanıcı Adı").lower()
        p_in = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            user = next((item for item in st.session_state.users_db if item["kullanici"] == u_in and item["sifre"] == p_in), None)
            if user:
                st.session_state.update({"authenticated": True, "username": u_in, "role": user["yetki"]})
                st.rerun()
            else: st.error("Hatalı Giriş!")
    st.stop()

# --- 4. ANA YAPI ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)

menu = {"📝 Yeni Poliçe": "yeni", "🔎 Poliçe Takibi": "takip", "💳 Ödeme & Cari": "odeme", "📊 Analiz": "analiz"}
if st.session_state.role == "Admin": menu["🔐 Yönetici Paneli"] = "admin"
choice = menu[st.sidebar.radio("Menü Seçimi", list(menu.keys()))]

# --- 5. SAYFALAR ---

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

        # --- TİKLEME MANTIĞI (SÜRE) ---
        is_two_months = st.checkbox("⚠️ Bu bir 2 Aylık Poliçedir (İşaretlenmezse 1 Yıl hesaplanır)")
        
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim Tarihi", datetime.now())
        basla = c7.date_input("Başlangıç Tarihi", datetime.now())
        
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Toplam Tutar (TL)", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret (TL)", min_value=0.0)
        
        tel = st.text_input("WhatsApp (5xxxxxxxxx)")
        
        if st.form_submit_button("✅ KAYDET VE GÖNDER"):
            # Tarih Hesaplama
            if is_two_months:
                bitis = basla + relativedelta(months=2)
            else:
                bitis = basla + relativedelta(years=1)
            
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
            st.success(f"Kayıt Tamam! Vade: {bitis.strftime('%d.%m.%Y')}"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        # Sadece arşive gitmemiş olanları süz
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"].copy()
        if not active_df.empty:
            for i, row in active_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([0.8, 0.2])
                    col1.markdown(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Vade: **{row['bitiş_tarihi']}**")
                    col1.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']}")
                    wa_link = f"https://wa.me/90{row['telefon']}?text=Sayın%20{row['müşteri_adı']},%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolacaktır."
                    col2.link_button("💬 Mesaj", wa_link, use_container_width=True)
        else: st.info("Şu an takip edilecek poliçe yok.")

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    tab1, tab2 = st.tabs(["👥 Kullanıcı Yönetimi", "🗂️ Veritabanı"])
    with tab1:
        st.write("### Kullanıcı Listesi")
        st.table(pd.DataFrame(st.session_state.users_db))
        with st.expander("👤 Kullanıcı Ekle/Güncelle"):
            nu = st.text_input("Kullanıcı")
            np = st.text_input("Şifre")
            ny = st.selectbox("Yetki", ["Admin", "Personel"])
            if st.button("Kaydet"):
                st.session_state.users_db = [u for u in st.session_state.users_db if u["kullanici"] != nu]
                st.session_state.users_db.append({"kullanici": nu, "sifre": np, "yetki": ny})
                st.success("Kullanıcı güncellendi."); st.rerun()
    with tab2:
        st.dataframe(df)

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.authenticated = False; st.rerun()
