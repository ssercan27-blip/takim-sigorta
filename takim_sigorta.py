import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI YÖNETİMİ (Session State) ---
if "users_db" not in st.session_state:
    # Başlangıç kullanıcıları - Burayı Admin panelinden değiştirebileceksin
    st.session_state.users_db = {
        "sercan": {"pw": "takim2026", "role": "admin"},
        "personel": {"pw": "takim123", "role": "user"}
    }

# --- AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        
        # Tarih ve Sayısal Dönüşüm
        for col in ['tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_datetime(raw_df[col], errors='coerce')
        for col in ['brut_prim', 'net_komisyon']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        
        # Arşiv sütunu yoksa oluştur
        if 'arsiv' not in raw_df.columns:
            raw_df['arsiv'] = False
        return raw_df
    except:
        return pd.DataFrame()

# 1. GİRİŞ KONTROLÜ
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            if user in st.session_state.users_db and st.session_state.users_db[user]["pw"] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.session_state.role = st.session_state.users_db[user]["role"]
                st.rerun()
            else:
                st.error("Bilgiler hatalı!")
    st.stop()

df = load_data()

# --- SIDEBAR ---
st.sidebar.markdown(f"**Hoş geldin, {st.session_state.username.upper()}**")
menu_options = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}

# Admin ise Yönetici Paneli'ni ekle
if st.session_state.role == "admin":
    menu_options["🔐 Yönetici Paneli"] = "admin"

choice = menu_options[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu_options.keys()))]

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
        sirket = st.selectbox("🏢 Sigorta Şirketi", ["Aksigorta", "Allianz", "Anadolu", "Axa", "Türkiye", "Diğer"])
        brans = st.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0)
        baslangic = st.date_input("🚀 Başlangıç Tarihi", datetime.now())
        bitis_tarihi = baslangic + relativedelta(years=1)
        
        if st.form_submit_button("✅ KAYDET"):
            kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
            new_row = pd.DataFrame([{
                "police_no": p_no, "musteri_adi": musteri, "brut_prim": prim, "net_komisyon": kazanc,
                "bitis_tarihi": bitis_tarihi, "arsiv": False, "sigorta_sirketi": sirket, "police_turu": brans
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sayfa1", data=updated_df)
            st.success("Kaydedildi!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    # Arşivlenmemişleri göster
    active_df = df[df['arsiv'] == False].copy()
    
    if not active_df.empty:
        # Excel stilinde durum belirleme
        bugun = pd.Timestamp(datetime.now().date())
        active_df['durum'] = active_df['bitis_tarihi'].apply(lambda x: "🟢 Güncel" if (x - bugun).days > 15 else "🟡 Yaklaştı")
        
        # ARŞİVLEME BUTONU EKLEME
        for i, row in active_df.iterrows():
            col_data, col_btn = st.columns([0.85, 0.15])
            with col_data:
                st.info(f"{row['musteri_adi']} | {row['police_no']} | Vade: {row['bitis_tarihi'].strftime('%d.%m.%Y')}")
            with col_btn:
                if st.button("📁 Arşivle", key=f"ars_{i}"):
                    df.at[i, 'arsiv'] = True
                    conn.update(worksheet="Sayfa1", data=df)
                    st.success("Arşivlendi!"); st.rerun()
    else:
        st.write("Aktif poliçe bulunamadı.")

elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    # Hata veren kısmı düzelttik: Veriyi temizleyip gönderiyoruz
    if not df.empty:
        report_df = df[df['brut_prim'] > 0].copy()
        c1, c2 = st.columns(2)
        c1.metric("Toplam Prim", f"{report_df['brut_prim'].sum():,.2f} TL")
        c2.metric("Net Kazanç", f"{report_df['net_komisyon'].sum():,.2f} TL")
        
        if not report_df.empty:
            fig1 = px.pie(report_df, values='net_komisyon', names='police_turu', title="Kazanç Dağılımı")
            st.plotly_chart(fig1, use_container_width=True)
            fig2 = px.bar(report_df, x='sigorta_sirketi', y='brut_prim', color='police_turu', title="Şirket Performansı")
            st.plotly_chart(fig2, use_container_width=True)

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    st.write("Kullanıcı Adı ve Şifre İşlemleri")
    
    with st.expander("➕ Yeni Kullanıcı Ekle"):
        new_user = st.text_input("Yeni Kullanıcı Adı")
        new_pw = st.text_input("Yeni Şifre", type="password")
        new_role = st.selectbox("Yetki", ["user", "admin"])
        if st.button("Kullanıcıyı Tanımla"):
            st.session_state.users_db[new_user] = {"pw": new_pw, "role": new_role}
            st.success(f"{new_user} başarıyla eklendi!")

    st.write("---")
    st.write("Current Users:", st.session_state.users_db)
