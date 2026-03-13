import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. LOGO VE SAYFA AYARI ---
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

# --- 3. GİRİŞ SİSTEMİ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        u = st.text_input("Kullanıcı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026":
                st.session_state.update({"authenticated": True, "username": u, "role": "admin"})
                st.rerun()
            elif u == "personel" and p == "takim2024":
                st.session_state.update({"authenticated": True, "username": u, "role": "user"})
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

# --- 4. ANA YAPI ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)

menu = {"📝 Yeni Poliçe": "yeni", "🔎 Poliçe Takibi": "takip", "💳 Ödeme & Cari": "odeme", "📊 Analiz": "analiz"}
if st.session_state.role == "admin": menu["🔐 Yönetici Paneli"] = "admin"
choice = menu[st.sidebar.radio("Menü", list(menu.keys()))]

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
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim", datetime.now())
        basla = c7.date_input("Başlangıç", datetime.now())
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Toplam Tutar", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret", min_value=0.0)
        tel = st.text_input("WhatsApp (5xxxxxxxxx)")
        if st.form_submit_button("✅ KAYDET"):
            bitis = basla + relativedelta(years=1)
            new_row = pd.DataFrame([{"police_no": p_no, "müşteri_adı": m_adi.upper(), "sigorta_sirketi": sirket, "poliçe_türü": brans, "plaka_tc": plaka.upper(), "telefon": tel, "tanzim_tarihi": tanzim.strftime("%d.%m.%Y"), "başlangıç_tarihi": basla.strftime("%d.%m.%Y"), "bitiş_tarihi": bitis.strftime("%d.%m.%Y"), "toplam_tutar": t_tutar, "alinan_ucret": a_ucret, "arsiv": "FALSE", "kayıt_yapan": st.session_state.username}])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Kaydedildi!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        # Arşivlenmemişleri ve vadesi yaklaşanları göster
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"].copy()
        for i, row in active_df.iterrows():
            with st.container(border=True):
                col_a, col_b = st.columns([0.8, 0.2])
                col_a.write(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Vade: {row['bitiş_tarihi']}")
                # WhatsApp Butonu
                wa_link = f"https://wa.me/90{row['telefon']}?text=Merhaba%20{row['müşteri_adı']}"
                col_b.link_button("💬 WhatsApp", wa_link, use_container_width=True)

elif choice == "odeme":
    st.subheader("💳 Cari Takip")
    df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
    df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
    st.metric("Toplam Bekleyen", f"{(df['toplam_tutar'].sum() - df['alinan_ucret'].sum()):,.2f} TL")
    st.table(df[df['toplam_tutar'] > df['alinan_ucret']][['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret']])

elif choice == "analiz":
    st.subheader("📊 Analiz Raporları")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        fig1 = px.pie(df, names='sigorta_sirketi', title="Şirket Dağılımı")
        c1.plotly_chart(fig1)
        fig2 = px.bar(df, x='poliçe_türü', y='toplam_tutar', title="Branş Bazlı Ciro")
        c2.plotly_chart(fig2)

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    st.write(f"**Aktif Yönetici:** {st.session_state.username.upper()}")
    st.write("### Tüm Kayıtlar")
    st.dataframe(df)

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.authenticated = False; st.rerun()
