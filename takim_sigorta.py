import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, timedelta
import urllib.parse

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KOMİSYON VE AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. LOGO VE SIDEBAR
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

# 2. GÜVENLİK SİSTEMİ
USER_CREDENTIALS = {"sercan": "takim2026", "admin": "admin44"}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.header("🔑 Yetkili Girişi")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sistemi Başlat", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Giriş başarısız!")
    st.stop()

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown(f"🚀 Yetkili: **{st.session_state.username.upper()}**")
page_map = {"Ana Portföy": "Sayfa1", "Ek Kayıtlar": "Sayfa2", "Arşiv": "Sayfa3"}
selected_page = page_map[st.sidebar.selectbox("📂 Veri Tabanı", list(page_map.keys()))]

# İŞLEM MERKEZİ MENÜSÜ
menu = {
    "📝 Yeni Poliçe": "kaydet",
    "🔎 Poliçe Takibi": "takip",
    "📊 Finansal Analiz": "rapor",
    "👤 Müşteri Detayları": "cari",
    "🔔 Vade Takip": "vade"
}
choice = menu[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu.keys()))]

if st.sidebar.button("🔴 Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# VERİ OKUMA VE ÖN HAZIRLIK
try:
    df = conn.read(worksheet=selected_page, ttl=0)
    df['tanzim_tarihi'] = pd.to_datetime(df['tanzim_tarihi'], errors='coerce')
    df['baslangic_tarihi'] = pd.to_datetime(df['baslangic_tarihi'], errors='coerce')
    df['bitis_tarihi'] = pd.to_datetime(df['bitis_tarihi'], errors='coerce')
except:
    df = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'kaynak', 'brut_prim', 'oran', 'net_komisyon', 'tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi', 'telefon'])

# --- SAYFA İÇERİKLERİ ---

if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_kayit", clear_on_submit=True):
        c1, c2 = st.columns(2)
        musteri = c1.text_input("👤 Müşteri Adı Soyadı")
        tel = c2.text_input("📱 Telefon (Örn: 90530...)")
        brans = c1.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        kaynak = c2.radio("📡 Kaynak", ["Öz Portföy", "Dış Acente"], horizontal=True)
        prim = c1.number_input("💰 Brüt Prim (TL)", min_value=0.0, step=500.0)
        
        t1, t2, t3 = st.columns(3)
        tanzim = t1.date_input("📅 Tanzim", datetime.now())
        baslangic = t2.date_input("🚀 Başlangıç", datetime.now())
        bitis = t3.date_input("🏁 Bitiş", baslangic + timedelta(days=365))
        
        if st.form_submit_button("✅ Kaydet"):
            oran = KOMISYON_SOZLUGU[brans]
            uyg_oran = oran / 2 if kaynak == "Dış Acente" else oran
            kazanc = prim * (uyg_oran / 100)
            
            new_row = pd.DataFrame([{
                "kayit_yapan": st.session_state.username, "musteri_adi": musteri, "police_turu": brans,
                "kaynak": kaynak, "brut_prim": prim, "oran": f"%{uyg_oran:.2f}", "net_komisyon": kazanc,
                "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"), "baslangic_tarihi": baslangic.strftime("%Y-%m-%d"),
                "bitis_tarihi": bitis.strftime("%Y-%m-%d"), "telefon": tel
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet=selected_page, data=updated_df)
            st.success("Kayıt Başarılı!")

elif choice == "takip":
    st.subheader("🔎 Poliçe Takip ve Arama")
    if not df.empty:
        with st.expander("🔍 Arama Filtreleri", expanded=True):
            f1, f2, f3 = st.columns(3)
            search_name = f1.text_input("Müşteri Adı")
            search_brans = f2.multiselect("Branş", options=df['police_turu'].unique())
            search_source = f3.multiselect("Kaynak", options=df['kaynak'].unique())
        
        filtered = df.copy()
        if search_name: filtered = filtered[filtered['musteri_adi'].str.contains(search_name, case=False, na=False)]
        if search_brans: filtered = filtered[filtered['police_turu'].isin(search_brans)]
        if search_source: filtered = filtered[filtered['kaynak'].isin(search_source)]
        
        st.dataframe(filtered.sort_values('tanzim_tarihi', ascending=False), use_container_width=True, hide_index=True)
    else: st.info("Henüz poliçe kaydı bulunmuyor.")

elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Brüt Prim", f"{df['brut_prim'].sum():,.2f} TL")
        m2.metric("Toplam Net Kazanç", f"{df['net_komisyon'].sum():,.2f} TL")
        m3.metric("Poliçe Sayısı", len(df))
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(df, values='net_komisyon', names='police_turu', title="Branş Dağılımı", hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            df['ay'] = df['tanzim_tarihi'].dt.strftime('%Y-%m')
            aylik = df.groupby('ay')['net_komisyon'].sum().reset_index()
            fig2 = px.line(aylik, x='ay', y='net_komisyon', title="Aylık Kazanç Trendi", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

elif choice == "cari":
    st.subheader("👤 Müşteri Detayları")
    if not df.empty:
        df['benzersiz_musteri'] = df['musteri_adi'] + " - " + df['telefon'].astype(str)
        secilen = st.selectbox("Müşteri Seçin", ["Seçiniz..."] + sorted(list(df['benzersiz_musteri'].unique())))
        
        if secilen != "Seçiniz...":
            m_df = df[df['benzersiz_musteri'] == secilen]
            st.info(f"**Toplam Kazanç:** {m_df['net_komisyon'].sum():,.2f} TL | **Poliçe Sayısı:** {len(m_df)}")
            st.dataframe(m_df[['police_turu', 'brut
