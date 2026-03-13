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

# --- 2. VERİ BAĞLANTISI (KESİN ÇÖZÜM) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        # Sütun isimlerini tertemiz yap (Boşlukları siler, küçük harf yapar)
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        # Arşiv sütununu garantiye al (FALSE/TRUE karmaşasını bitirir)
        if 'arsiv' in df.columns:
            df['arsiv'] = df['arsiv'].astype(str).str.strip().str.upper()
        return df
    except:
        return pd.DataFrame()

# --- 3. GİRİŞ SİSTEMİ (ADMİN KİLİDİ) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Kullanıcı Adı").lower().strip()
        p_in = st.text_input("Şifre", type="password").strip()
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u_in == "sercan" and p_in == "takim2026":
                st.session_state.update({"authenticated": True, "username": "sercan", "role": "Admin"})
                st.rerun()
            elif u_in == "personel" and p_in == "takim2024":
                st.session_state.update({"authenticated": True, "username": "personel", "role": "User"})
                st.rerun()
            else: st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- 4. ANA YAPI VE MENÜ (ESKİ GÖRÜNÜM) ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)
st.sidebar.markdown(f"**Hoş geldin, {st.session_state.username.upper()}**")

# Menü Listesi
menu_options = ["📝 Yeni Poliçe", "🔎 Poliçe Takibi", "💳 Ödeme & Cari", "📊 Analiz"]
if st.session_state.role == "Admin":
    menu_options.append("🔐 Yönetici Paneli")

# ESKİ RADİO BUTON GÖRÜNÜMÜ
choice = st.sidebar.radio("İŞLEM MERKEZİ", menu_options)

# --- 5. SAYFA İÇERİKLERİ ---

# --- YENİ POLİÇE ---
if choice == "📝 Yeni Poliçe":
    st.subheader("📝 Yeni Poliçe Kayıt")
    with st.form("yeni_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        brans = c4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        plaka = c5.text_input("Plaka / TC No")

        # Tikleme (SÜRE HESABI)
        is_two_months = st.checkbox("Bu bir 2 Aylık Poliçedir")
        
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim Tarihi", datetime.now())
        basla = c7.date_input("Başlangıç Tarihi", datetime.now())
        
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Toplam Tutar (TL)", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret (TL)", min_value=0.0)
        tel = st.text_input("WhatsApp (5xxxxxxxxx)")
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            # Vade Hesaplama: Tikliyse 2 ay, değilse 1 yıl ekle
            bitis = basla + relativedelta(months=2) if is_two_months else basla + relativedelta(years=1)
            
            # Veriyi TR formatında (GG.AA.YYYY) hazırla
            new_row = pd.DataFrame([{
                "police_no": p_no, 
                "müşteri_adı": m_adi.upper(), 
                "sigorta_sirketi": sirket, 
                "poliçe_türü": brans, 
                "plaka_tc": plaka.upper(), 
                "telefon": tel, 
                "tanzim_tarihi": tanzim.strftime("%d.%m.%Y"), 
                "başlangıç_tarihi": basla.strftime("%d.%m.%Y"), 
                "bitiş_tarihi": bitis.strftime("%d.%m.%Y"), 
                "toplam_tutar": t_tutar, 
                "alinan_ucret": a_ucret, 
                "arsiv": "FALSE", 
                "kayıt_yapan": st.session_state.username
            }])
            
            # Google Sheets'e gönder
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
            st.success(f"Kayıt Eklendi! Vade Tarihi: {bitis.strftime('%d.%m.%Y')}")
            st.rerun()
            
# --- POLİÇE TAKİBİ ---
elif choice == "🔎 Poliçe Takibi":
    st.subheader("🔎 Aktif Poliçeler")
    if not df.empty:
        # GERÇEK ÇÖZÜM: Filtreyi sarsılmaz yap
        active_df = df[df['arsiv'] == "FALSE"].copy()
        if not active_df.empty:
            for i, row in active_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([0.8, 0.2])
                    col1.markdown(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Vade: **{row['bitiş_tarihi']}**")
                    col1.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']}")
                    wa_link = f"https://wa.me/90{row['telefon']}?text=Merhaba%20{row['müşteri_adı']},%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolacaktır."
                    col2.link_button("💬 WhatsApp", wa_link, use_container_width=True)
        else: st.info("Takip edilecek aktif poliçe bulunamadı.")

# --- ÖDEME & CARİ ---
elif choice == "💳 Ödeme & Cari":
    st.subheader("💳 Cari Takip")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
        kalan = df['toplam_tutar'].sum() - df['alinan_ucret'].sum()
        st.metric("Bekleyen Toplam Tahsilat", f"{kalan:,.2f} TL")
        st.table(df[df['toplam_tutar'] > df['alinan_ucret']][['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret']])

# --- ANALİZ ---
elif choice == "📊 Analiz":
    st.subheader("📊 Portföy Analizi")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(df, names='sigorta_sirketi', title="Şirket Dağılımı"))
        c2.plotly_chart(px.bar(df, x='poliçe_türü', y='toplam_tutar', title="Branş Ciro"))

# --- YÖNETİCİ PANELİ ---
elif choice == "🔐 Yönetici Paneli":
    st.subheader("🔐 Yönetici Paneli")
    st.write(f"Hoş geldiniz Sercan Bey. Sistemdeki tüm ham veriler aşağıdadır:")
    st.dataframe(df)

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.clear(); st.rerun()



