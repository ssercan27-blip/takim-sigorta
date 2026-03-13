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

# --- LOGO KONTROL FONKSİYONU ---
def show_logo(location="main"):
    logo_path = None
    if os.path.exists("logo.jpg"): logo_path = "logo.jpg"
    elif os.path.exists("logo.png"): logo_path = "logo.png"
    
    if logo_path:
        if location == "main":
            st.image(logo_path, width=250)
        else:
            st.sidebar.image(logo_path, use_container_width=True)
    else:
        if location == "main":
            st.markdown("<h1 style='color: #1E88E5;'>🛡️ TAKİM SİGORTA</h1>", unsafe_allow_html=True)
        else:
            st.sidebar.markdown("### 🛡️ TAKİM SİGORTA")

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
        show_logo(location="main")
        st.markdown("### 🔑 Yetkili Girişi")
        user_input = st.text_input("Kullanıcı Adı").lower()
        pw_input = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if user_input in st.session_state.users_db and st.session_state.users_db[user_input]["pw"] == pw_input:
                st.session_state.authenticated = True
                st.session_state.username = user_input
                st.session_state.role = st.session_state.users_db[user_input]["role"]
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

df = load_data()

# --- SIDEBAR ---
show_logo(location="sidebar")
st.sidebar.markdown(f"**Yetkili:** {st.session_state.username.upper()}")
menu_options = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}
if st.session_state.role == "admin":
    menu_options["🔐 Yönetici Paneli"] = "admin"

choice = menu_options[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu_options.keys()))]

if st.sidebar.button("🔴 Çıkış Yap"):
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
        sirket = st.selectbox("🏢 Sigorta Şirketi", ["Aksigorta", "Allianz", "Anadolu", "Axa", "Türkiye Sigorta", "HDI", "Mapfre", "Sompo", "Diğer"])
        brans = st.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0)
        baslangic = st.date_input("🚀 Başlangıç", datetime.now())
        bitis_tarihi = baslangic + relativedelta(years=1)
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            if all([p_no, musteri, prim > 0]):
                kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
                new_row = pd.DataFrame([{
                    "police_no": p_no, "musteri_adi": musteri, "brut_prim": prim, "net_komisyon": kazanc,
                    "bitis_tarihi": pd.to_datetime(bitis_tarihi), "arsiv": False, "sigorta_sirketi": sirket, "police_turu": brans, "telefon": tel
                }])
                conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("Kayıt Başarılı!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    active_df = df[df['arsiv'] == False].copy() if not df.empty else pd.DataFrame()
    
    if not active_df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        # Filtreler
        search = st.text_input("🔍 Hızlı Ara")
        filtre = st.radio("Durum:", ["Tümü", "Vade Yaklaştı (15 Gün)"], horizontal=True)
        
        if search:
            active_df = active_df[active_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        if filtre == "Vade Yaklaştı (15 Gün)":
            active_df = active_df[(active_df['bitis_tarihi'] - bugun).dt.days <= 15]

        # Excel stili liste ve Arşiv Butonu
        for i, row in active_df.iterrows():
            with st.container(border=True):
                col_info, col_btn = st.columns([0.8, 0.2])
                with col_info:
                    st.write(f"**{row['musteri_adi']}** | {row['police_no']} | {row['sigorta_sirketi']}")
                    st.caption(f"Vade Sonu: {row['bitis_tarihi'].strftime('%d.%m.%Y')}")
                with col_btn:
                    if st.button("📁 Arşivle", key=f"btn_{i}"):
                        df.at[i, 'arsiv'] = True
                        conn.update(worksheet="Sayfa1", data=df)
                        st.success("Arşive gönderildi!"); st.rerun()
    else:
        st.info("Aktif poliçe bulunamadı.")

elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    if not df.empty:
        # Plotly hatasını önlemek için veriyi grafiğe uygun hale getiriyoruz
        report_df = df[(df['brut_prim'] > 0) & (df['sigorta_sirketi'] != "")].copy()
        
        if not report_df.empty:
            m1, m2 = st.columns(2)
            m1.metric("Toplam Üretim", f"{report_df['brut_prim'].sum():,.2f} TL")
            m2.metric("Toplam Kazanç", f"{report_df['net_komisyon'].sum():,.2f} TL")
            
            st.plotly_chart(px.pie(report_df, values='net_komisyon', names='police_turu', title="Branş Dağılımı"), use_container_width=True)
            st.plotly_chart(px.bar(report_df, x='sigorta_sirketi', y='brut_prim', color='police_turu', title="Şirket Performansı"), use_container_width=True)
        else:
            st.warning("Analiz edilecek veri bulunamadı.")

elif choice == "vade":
    st.subheader("🔔 Vade Takip")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        v_df = df[df['arsiv'] == False].copy()
        v_df['kalan'] = (v_df['bitis_tarihi'] - bugun).dt.days
        vade_list = v_df[v_df['kalan'] <= 30].sort_values('kalan')
        st.dataframe(vade_list[['musteri_adi', 'police_no', 'bitis_tarihi', 'kalan']], use_container_width=True, hide_index=True)

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    tab1, tab2 = st.tabs(["Kullanıcı Ekle", "Mevcut Kullanıcılar"])
    
    with tab1:
        with st.form("user_form"):
            new_u = st.text_input("Kullanıcı Adı")
            new_p = st.text_input("Şifre")
            new_r = st.selectbox("Yetki", ["user", "admin"])
            if st.form_submit_button("Kullanıcıyı Kaydet"):
                st.session_state.users_db[new_u] = {"pw": new_p, "role": new_r}
                st.success(f"{new_u} eklendi.")
    
    with tab2:
        st.write(st.session_state.users_db)
