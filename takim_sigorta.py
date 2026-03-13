import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI VE YETKİ TANIMLARI ---
USER_CREDENTIALS = {
    "sercan": ["takim2026", "admin"],
    "admin": ["admin44", "admin"]
}

# --- AYARLAR VE LİSTELER ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

SIRKET_LISTESI = sorted([
    "Aksigorta", "Allianz Sigorta", "Anadolu Sigorta", "Ankara Sigorta", "Arex Sigorta", 
    "Atlas Mutuel Sigorta", "Axa Sigorta", "Bereket Sigorta", "Bupa Acıbadem Sigorta", 
    "Chubb Sigorta", "Corpus Sigorta", "Doğa Sigorta", "Eureko Sigorta", "Generali Sigorta", 
    "Güneş Sigorta", "HDI Sigorta", "Hepiyi Sigorta", "Koru Sigorta", "Magdeburger Sigorta", 
    "Mapfre Sigorta", "Neova Katılım Sigorta", "Orient Sigorta", "Prive Sigorta", 
    "Quick Sigorta", "Ray Sigorta", "Sompo Sigorta", "Şeker Sigorta", "Türk P&I Sigorta", 
    "Türkiye Sigorta", "Unico Sigorta", "VHV Sigorta", "Ziraat Sigorta", "Zurich Sigorta"
]) + ["Diğer"]

# 1. OTURUM DURUMU
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None

# 2. GİRİŞ EKRANI
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.header("🔑 Yetkili Girişi")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sistemi Başlat", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user][0] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.session_state.role = USER_CREDENTIALS[user][1]
                st.rerun()
            else:
                st.error("Giriş başarısız!")
    st.stop()

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)
WORKSHEET_NAME = "Sayfa1" 

def load_data():
    try:
        raw_df = conn.read(worksheet=WORKSHEET_NAME, ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        for col in ['tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_datetime(raw_df[col], errors='coerce')
        return raw_df
    except:
        return pd.DataFrame()

df = load_data()

# --- SIDEBAR ---
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
elif os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

st.sidebar.markdown(f"👤 Yetkili: **{st.session_state.username.upper()}**")
menu = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}
choice = menu[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu.keys()))]

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

# --- SAYFALAR ---
if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_kayit", clear_on_submit=True):
        p_no = st.text_input("🔢 Poliçe Numarası")
        c1, c2 = st.columns(2)
        musteri = c1.text_input("👤 Müşteri Adı Soyadı")
        tel = c2.text_input("📱 Telefon")
        
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("🏢 Sigorta Şirketi", SIRKET_LISTESI)
        brans = c4.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = c5.number_input("💰 Brüt Prim (TL)", min_value=0.0)
        
        st.divider()
        t1, t2, t3 = st.columns(3)
        tanzim = t1.date_input("📅 Tanzim Tarihi", datetime.now(), format="DD/MM/YYYY")
        baslangic = t2.date_input("🚀 Başlangıç Tarihi", datetime.now(), format="DD/MM/YYYY")
        sure = t3.selectbox("⏳ Süre", ["1 Yıllık", "2 Aylık"])
        
        bitis_tarihi = baslangic + (relativedelta(years=1) if sure == "1 Yıllık" else relativedelta(months=2))
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            if all([p_no, musteri, tel, prim > 0]):
                kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
                new_row = pd.DataFrame([{
                    "kayit_yapan": st.session_state.username, "police_no": str(p_no), 
                    "musteri_adi": musteri, "sigorta_sirketi": sirket, "police_turu": brans, 
                    "brut_prim": prim, "net_komisyon": kazanc, "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"), 
                    "baslangic_tarihi": baslangic.strftime("%Y-%m-%d"), "bitis_tarihi": bitis_tarihi.strftime("%Y-%m-%d"), 
                    "telefon": tel
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet=WORKSHEET_NAME, data=updated_df)
                st.success("Kayıt Başarılı!")
                st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        filtre_turu = st.radio("Görünüm:", ["Tümü", "Vadesi Yaklaşanlar (15 Gün)"], horizontal=True)
        
        with st.expander("🛠️ Kayıt Düzenle veya Sil", expanded=False):
            secilen_no = st.selectbox("Poliçe Seçin", ["Seçiniz..."] + sorted(df['police_no'].astype(str).unique().tolist()))
            if secilen_no != "Seçiniz...":
                idx = df[df['police_no'].astype(str) == secilen_no].index[0]
                row = df.loc[idx]
                with st.form("duzenleme_formu"):
                    u_musteri = st.text_input("Müşteri", value=str(row['musteri_adi']))
                    u_prim = st.number_input("Prim", value=float(row['brut_prim']))
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 GÜNCELLE"):
                        df.at[idx, 'musteri_adi'] = u_musteri
                        df.at[idx, 'brut_prim'] = u_prim
                        conn.update(worksheet=WORKSHEET_NAME, data=df)
                        st.success("Güncellendi!")
                        st.rerun()
                    if c2.form_submit_button("🗑️ SİL"):
                        new_df = df.drop(idx)
                        conn.update(worksheet=WORKSHEET_NAME, data=new_df)
                        st.success("Silindi!")
                        st.rerun()

        search = st.text_input("🔍 Hızlı Ara")
        display_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
        
        if filtre_turu == "Vadesi Yaklaşanlar (15 Gün)":
            bugun = pd.Timestamp(datetime.now().date())
            display_df = display_df.dropna(subset=['bitis_tarihi'])
            display_df = display_df[(display_df['bitis_tarihi'] >= bugun) & ((display_df['bitis_tarihi'] - bugun).dt.days <= 15)]

        st.dataframe(display_df.sort_values('tanzim_tarihi', ascending=False), use_container_width=True, hide_index=True)

elif choice == "rapor":
    st.subheader("📊 Analiz")
    if not df.empty:
        st.metric("Toplam Prim", f"{df['brut_prim'].sum():,.2f} TL")
        fig = px.pie(df, values='net_komisyon', names='police_turu', title="Branş Dağılımı")
        st.plotly_chart(fig, use_container_width=True)

elif choice == "vade":
    st.subheader("🔔 Vade Takip")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        v_df = df.dropna(subset=['bitis_tarihi']).copy()
        v_df['kalan'] = (v_df['bitis_tarihi'] - bugun).dt.days
        yaklasan = v_df[v_df['kalan'] <= 30].sort_values('kalan')
        st.dataframe(yaklasan[['police_no', 'musteri_adi', 'bitis_tarihi', 'kalan']], use_container_width=True, hide_index=True)
