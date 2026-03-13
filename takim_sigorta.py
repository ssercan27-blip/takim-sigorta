import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. AYARLAR ---
st.set_page_config(page_title="Takim Sigorta | İşlem Merkezi", layout="wide")

# --- 2. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        # Sütun isimlerini tertemiz yapıyoruz
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        # Arşiv sütunundaki verileri garantili hale getiriyoruz
        if 'arsiv' in df.columns:
            df['arsiv'] = df['arsiv'].astype(str).str.strip().str.upper()
        return df
    except:
        return pd.DataFrame()

# --- 3. GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.header("🛡️ Takim Sigorta Giriş")
        u = st.text_input("Kullanıcı").lower().strip()
        p = st.text_input("Şifre", type="password").strip()
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026":
                st.session_state.update({"authenticated": True, "username": "sercan", "role": "Admin"})
                st.rerun()
            elif u == "personel" and p == "takim2024":
                st.session_state.update({"authenticated": True, "username": "personel", "role": "User"})
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

# --- 4. ANA YAPI ---
df = load_data_safe()

# SOL MENÜ (ESKİ SADE GÖRÜNÜM)
menu_options = ["📝 Yeni Poliçe", "🔎 Poliçe Takibi", "💳 Ödeme & Cari", "📊 Analiz"]
if st.session_state.role == "Admin":
    menu_options.append("🔐 Yönetici Paneli")

choice = st.sidebar.radio("İŞLEM MERKEZİ", menu_options)

# --- 5. SAYFALAR ---

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

        # TİKLEME MANTIĞI
        is_two_months = st.checkbox("Bu bir 2 Aylık Poliçedir")
        
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim Tarihi", datetime.now())
        basla = c7.date_input("Başlangıç Tarihi", datetime.now())
        
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Poliçe Tutarı (TL)", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret (TL)", min_value=0.0)
        tel = st.text_input("WhatsApp (5xxxxxxxxx)")
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            # Vade Hesaplama: Tikli ise 2 ay, değilse 1 yıl
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
            st.success("Kayıt Başarıyla Eklendi!"); st.rerun()

# --- POLİÇE TAKİBİ ---
elif choice == "🔎 Poliçe Takibi":
    st.subheader("🔎 Aktif Poliçeler")
    if not df.empty and 'arsiv' in df.columns:
        # GERÇEK ÇÖZÜM: Boşlukları temizle ve sadece FALSE olanları filtrele
        active_df = df[df['arsiv'] == "FALSE"].copy()
        if not active_df.empty:
            for i, row in active_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([0.8, 0.2])
                    col1.markdown(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Vade: **{row['bitiş_tarihi']}**")
                    col1.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']}")
                    wa_link = f"https://wa.me/90{row['telefon']}?text=Sayın%20{row['müşteri_adı']},%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolacaktır."
                    col2.link_button("💬 WhatsApp", wa_link, use_container_width=True)
        else: st.info("Takip edilecek aktif poliçe bulunamadı.")

# --- ÖDEME & CARİ ---
elif choice == "💳 Ödeme & Cari":
    st.subheader("💳 Cari Takip")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
        borc = df['toplam_tutar'].sum() - df['alinan_ucret'].sum()
        st.metric("Bekleyen Toplam Tahsilat", f"{borc:,.2f} TL")
        st.table(df[df['toplam_tutar'] > df['alinan_ucret']][['müşteri_adı', 'toplam_tutar', 'alinan_ucret']])

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
    st.write("Hoş geldiniz Sercan Bey. Tüm veritabanı aşağıdadır:")
    st.dataframe(df)

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.clear(); st.rerun()
