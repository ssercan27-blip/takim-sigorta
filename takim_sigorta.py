import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI YÖNETİMİ ---
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "sercan": {"pw": "takim2026", "role": "admin"},
        "admin": {"pw": "admin44", "role": "admin"}
    }

# --- AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# --- LOGO GÖSTERİMİ ---
def show_logo(loc="main"):
    path = "logo.jpg" if os.path.exists("logo.jpg") else ("logo.png" if os.path.exists("logo.png") else None)
    if path:
        if loc == "main": st.image(path, width=200)
        else: st.sidebar.image(path, use_container_width=True)
    else:
        st.sidebar.title("🛡️ TAKİM SİGORTA")

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        
        # Sütun isimlerini temizle ve zorunlu isimleri eşle
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        
        # Kritik sütunların varlığını garanti et (Hata almamak için boş sütun oluşturur)
        required_cols = ['police_no', 'musteri_adi', 'sigorta_sirketi', 'police_turu', 'brut_prim', 'net_komisyon', 'bitis_tarihi', 'arsiv']
        for col in required_cols:
            if col not in raw_df.columns:
                raw_df[col] = False if col == 'arsiv' else ""
        
        # Dönüşümler
        raw_df['bitis_tarihi'] = pd.to_datetime(raw_df['bitis_tarihi'], errors='coerce')
        raw_df['brut_prim'] = pd.to_numeric(raw_df['brut_prim'], errors='coerce').fillna(0)
        raw_df['net_komisyon'] = pd.to_numeric(raw_df['net_komisyon'], errors='coerce').fillna(0)
        raw_df['arsiv'] = raw_df['arsiv'].astype(bool)
        
        return raw_df
    except:
        return pd.DataFrame()

# 1. GİRİŞ
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        show_logo("main")
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ", use_container_width=True):
            if u in st.session_state.users_db and st.session_state.users_db[u]["pw"] == p:
                st.session_state.authenticated, st.session_state.username = True, u
                st.session_state.role = st.session_state.users_db[u]["role"]
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

df = load_data()

# --- SIDEBAR ---
show_logo("sidebar")
st.sidebar.write(f"Hoş geldin, **{st.session_state.username.upper()}**")
opt = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}
if st.session_state.role == "admin": opt["🔐 Yönetici Paneli"] = "admin"
choice = opt[st.sidebar.radio("Menü", list(opt.keys()))]

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

# --- SAYFALAR ---
if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe")
    with st.form("k_form", clear_on_submit=True):
        p_no = st.text_input("Poliçe No")
        m_adi = st.text_input("Müşteri Ad Soyad")
        sirket = st.selectbox("Şirket", ["Aksigorta", "Allianz", "Anadolu", "Axa", "Türkiye", "Diğer"])
        brans = st.selectbox("Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("Prim", min_value=0.0)
        bas = st.date_input("Başlangıç", datetime.now())
        bitis = bas + relativedelta(years=1)
        if st.form_submit_button("KAYDET"):
            kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
            new = pd.DataFrame([{"police_no": p_no, "musteri_adi": m_adi, "sigorta_sirketi": sirket, "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc, "bitis_tarihi": bitis, "arsiv": False}])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new], ignore_index=True))
            st.success("Kaydedildi!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        # Arşivlenmemişleri ve geçerli verisi olanları göster
        active = df[df['arsiv'] == False].copy()
        search = st.text_input("🔍 Ara")
        if search:
            active = active[active.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        for i, r in active.iterrows():
            with st.container(border=True):
                c_inf, c_btn = st.columns([0.8, 0.2])
                c_inf.write(f"**{r['musteri_adi']}** | {r['police_no']} | {r['sigorta_sirketi']}")
                if c_btn.button("📁 Arşivle", key=f"ar_{i}"):
                    df.at[i, 'arsiv'] = True
                    conn.update(worksheet="Sayfa1", data=df)
                    st.success("Arşivlendi!"); st.rerun()

elif choice == "rapor":
    st.subheader("📊 Analiz")
    # Plotly Hatasını Engelleyen Temiz Veri
    rdf = df[(df['brut_prim'] > 0) & (df['sigorta_sirketi'] != "")].copy()
    if not rdf.empty:
        st.metric("Toplam Prim", f"{rdf['brut_prim'].sum():,.2f} TL")
        st.plotly_chart(px.pie(rdf, values='net_komisyon', names='police_turu', title="Branş Dağılımı"), use_container_width=True)
        st.plotly_chart(px.bar(rdf, x='sigorta_sirketi', y='brut_prim', title="Şirket Performansı"), use_container_width=True)
    else: st.info("Veri yok.")

elif choice == "vade":
    st.subheader("🔔 Vade Takip")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        vade_df = df[(df['arsiv'] == False) & (df['bitis_tarihi'].notnull())].copy()
        vade_df['kalan'] = (vade_df['bitis_tarihi'] - bugun).dt.days
        st.dataframe(vade_df[vade_df['kalan'] <= 30].sort_values('kalan'), use_container_width=True, hide_index=True)

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    new_u = st.text_input("Yeni Kullanıcı")
    new_p = st.text_input("Şifre")
    if st.button("Ekle"):
        st.session_state.users_db[new_u] = {"pw": new_p, "role": "user"}
        st.success("Eklendi")
