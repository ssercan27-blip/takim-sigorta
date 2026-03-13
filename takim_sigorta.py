import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. AYARLAR ---
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
        # SÜTUN NORMALİZASYONU (Hayati Kısım)
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 3. GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.subheader("🛡️ Takim Sigorta Giriş")
        u = st.text_input("Kullanıcı").lower().strip()
        p = st.text_input("Şifre", type="password").strip()
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u == "sercan" and p == "takim2026":
                st.session_state.update({"authenticated": True, "username": u, "role": "Admin"})
                st.rerun()
            elif u == "personel" and p == "takim2024":
                st.session_state.update({"authenticated": True, "username": u, "role": "User"})
                st.rerun()
            else: st.error("Hatalı!")
    st.stop()

# --- 4. VERİ VE MENÜ ---
df = load_data_safe()

# SOL MENÜ (ASLA KAYBOLMAZ)
st.sidebar.title("İŞLEM MERKEZİ")
menu_map = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "💳 Ödeme & Cari": "odeme",
    "📊 Analiz": "analiz"
}

if st.session_state.role == "Admin":
    menu_map["🔐 Yönetici Paneli"] = "admin"

choice = menu_map[st.sidebar.radio("Sayfa Seçin", list(menu_map.keys()))]

# --- 5. SAYFALAR ---

if choice == "yeni":
    st.subheader("📝 Yeni Kayıt Girişi")
    with st.form("kayit_formu", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        
        c3, c4 = st.columns(2)
        sirket = c3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        brans = c4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        
        plaka = st.text_input("Plaka / TC No")
        is_two_months = st.checkbox("Bu bir 2 Aylık Poliçedir")
        
        c5, c6 = st.columns(2)
        tanzim = c5.date_input("Tanzim Tarihi", datetime.now())
        basla = c6.date_input("Başlangıç Tarihi", datetime.now())
        
        c7, c8 = st.columns(2)
        t_tutar = c7.number_input("Poliçe Tutarı (TL)", min_value=0.0)
        a_ucret = c8.number_input("Alınan Ücret (TL)", min_value=0.0)
        tel = st.text_input("WhatsApp (5xxxxxxxxx)")
        
        if st.form_submit_button("✅ SİSTEME İŞLE"):
            # Vade Hesaplama
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
            st.success(f"Kaydedildi! Vade: {bitis.strftime('%d.%m.%Y')}"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takip Ekranı")
    if not df.empty:
        # FİLTRELEME GÜNCELLEMESİ: Boşlukları ve tip hatalarını temizleyerek bak
        active_df = df[df['arsiv'].astype(str).str.strip().str.upper() == "FALSE"].copy()
        
        if not active_df.empty:
            for i, row in active_df.iterrows():
                with st.container(border=True):
                    col_detay, col_wa = st.columns([0.8, 0.2])
                    col_detay.markdown(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Bitiş: **{row['bitiş_tarihi']}**")
                    col_detay.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']}")
                    wa_link = f"https://wa.me/90{row['telefon']}?text=Sayın%20{row['müşteri_adı']},%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolacaktır."
                    col_wa.link_button("💬 WhatsApp", wa_link, use_container_width=True)
        else:
            st.info("Aktif poliçe bulunamadı. Lütfen 'arsiv' sütununu kontrol edin.")

elif choice == "odeme":
    st.subheader("💳 Ödeme ve Cari")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
        borc = df['toplam_tutar'].sum() - df['alinan_ucret'].sum()
        st.metric("Bekleyen Tahsilat", f"{borc:,.2f} TL")
        borclular = df[df['toplam_tutar'] > df['alinan_ucret']]
        st.table(borclular[['müşteri_adı', 'toplam_tutar', 'alinan_ucret']])

elif choice == "analiz":
    st.subheader("📊 Analiz")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(df, names='sigorta_sirketi', title="Şirket Dağılımı"))
        c2.plotly_chart(px.bar(df, x='poliçe_türü', y='toplam_tutar', title="Ciro"))

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    st.write(f"Aktif Admin: {st.session_state.username.upper()}")
    st.dataframe(df)

if st.sidebar.button("🔴 Çıkış"):
    st.session_state.clear(); st.rerun()
