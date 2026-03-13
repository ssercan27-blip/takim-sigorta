import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- AYARLAR VE LİSTELER ---
USER_CREDENTIALS = {"sercan": ["takim2026", "admin"], "admin": ["admin44", "admin"]}
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}
SIRKET_LISTESI = sorted([
    "Aksigorta", "Allianz Sigorta", "Anadolu Sigorta", "Ankara Sigorta", "Arex Sigorta", 
    "Atlas Mutuel Sigorta", "Axa Sigorta", "Bereket Sigorta", "Bupa Acıbadem Sigorta", 
    "Chubb Sigorta", "Corpus Sigorta", "Doğa Sigorta", "Eureko Sigorta", "Generali Sigorta", 
    "HDI Sigorta", "Hepiyi Sigorta", "Koru Sigorta", "Magdeburger Sigorta", 
    "Mapfre Sigorta", "Neova Katılım Sigorta", "Orient Sigorta", "Prive Sigorta", 
    "Quick Sigorta", "Ray Sigorta", "Sompo Sigorta", "Şeker Sigorta", "Türk P&I Sigorta", 
    "Türkiye Sigorta", "Unico Sigorta", "VHV Sigorta", "Ziraat Sigorta", "Zurich Sigorta"
]) + ["Diğer"]

# --- LOGO VE VERİ YÜKLEME ---
def get_logo():
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("logo.png"): return "logo.png"
    return None

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        for col in ['tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_datetime(raw_df[col], errors='coerce')
        for col in ['brut_prim', 'net_komisyon']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        return raw_df
    except:
        return pd.DataFrame()

# 1. OTURUM KONTROLÜ
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.markdown("### 🔑 Yetkili Girişi")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sistemi Başlat", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user][0] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Hatalı giriş!")
    st.stop()

df = load_data()

# --- SIDEBAR ---
logo = get_logo()
if logo: st.sidebar.image(logo, use_container_width=True)
st.sidebar.markdown(f"**Yetkili:** {st.session_state.username.upper()}")
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
        tanzim = t1.date_input("📅 Tanzim", datetime.now())
        baslangic = t2.date_input("🚀 Başlangıç", datetime.now())
        sure = st.selectbox("⏳ Süre", ["1 Yıllık", "2 Aylık"])
        bitis_tarihi = baslangic + (relativedelta(years=1) if sure == "1 Yıllık" else relativedelta(months=2))
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            if all([p_no, musteri, prim > 0]):
                kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
                new_row = pd.DataFrame([{
                    "kayit_yapan": st.session_state.username, "police_no": str(p_no), "musteri_adi": musteri,
                    "sigorta_sirketi": sirket, "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc,
                    "tanzim_tarihi": tanzim, "baslangic_tarihi": baslangic, "bitis_tarihi": bitis_tarihi, "telefon": tel
                }])
                conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("Poliçe Başarıyla Kaydedildi!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        def durum_belirle(bitis):
            if pd.isnull(bitis): return "⚪ Bilgi Yok"
            kalan = (bitis - bugun).days
            if kalan < 0: return "🔴 Vadesi Geçmiş"
            if kalan <= 15: return "🟡 Vade Yaklaştı"
            return "🟢 Güncel"
        df['durum'] = df['bitis_tarihi'].apply(durum_belirle)

        # Üst Metrikler
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Poliçe", len(df))
        c2.metric("Güncel Poliçe", len(df[df['durum'] == "🟢 Güncel"]))
        c3.metric("Vadesi Yaklaşan (15 Gün)", len(df[df['durum'] == "🟡 Vade Yaklaştı"]))

        search = st.text_input("🔍 Hızlı Ara (İsim/No/Plaka)")
        filtre = st.radio("Durum Filtresi:", ["Tümü", "🟢 Güncel", "🟡 Vade Yaklaştı", "🔴 Vadesi Geçmiş"], horizontal=True)
        
        d_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
        if filtre != "Tümü": d_df = d_df[d_df['durum'] == filtre]

        st.dataframe(d_df.sort_values('bitis_tarihi'), use_container_width=True, hide_index=True,
                     column_config={"durum": "Durum", "brut_prim": st.column_config.NumberColumn("Prim", format="%.2f TL"),
                                    "bitis_tarihi": st.column_config.DateColumn("Vade Sonu", format="DD.MM.YYYY")})

elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("Toplam Prim Üretimi", f"{df['brut_prim'].sum():,.2f} TL")
        c2.metric("Toplam Net Komisyon", f"{df['net_komisyon'].sum():,.2f} TL")
        
        st.plotly_chart(px.pie(df, values='net_komisyon', names='police_turu', title="Branş Dağılımı"), use_container_width=True)
        st.plotly_chart(px.bar(df, x='sigorta_sirketi', y='brut_prim', color='sigorta_sirketi', title="Şirket Bazlı Performans"), use_container_width=True)

elif choice == "vade":
    st.subheader("🔔 Vade Takip Merkezi")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        df['kalan_gun'] = (df['bitis_tarihi'] - bugun).dt.days
        vade_df = df[df['kalan_gun'] <= 30].sort_values('kalan_gun')
        
        if not vade_df.empty:
            st.warning(f"Önümüzdeki 30 gün içinde vadesi dolacak {len(vade_df)} poliçe var.")
            st.dataframe(vade_df[['musteri_adi', 'police_no', 'sigorta_sirketi', 'bitis_tarihi', 'kalan_gun']], 
                         use_container_width=True, hide_index=True,
                         column_config={"kalan_gun": "Kalan Gün", "bitis_tarihi": st.column_config.DateColumn("Bitiş", format="DD.MM.YYYY")})
        else:
            st.success("Harika! Önümüzdeki 30 gün içinde vadesi dolacak poliçe bulunmuyor.")
