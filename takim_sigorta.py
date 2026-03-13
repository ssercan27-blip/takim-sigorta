import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta - Yönetim Paneli", layout="wide")

# --- KOMİSYON ORANLARI ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. LOGO VE GÖRSEL DÜZEN
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

# 2. KULLANICI GİRİŞİ
USER_CREDENTIALS = {"sercan": "takim2026", "admin": "admin44"}

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔑 Sistem Girişi")
            user = st.text_input("Kullanıcı Adı").lower()
            pw = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap", use_container_width=True):
                if user in USER_CREDENTIALS and USER_CREDENTIALS[user] == pw:
                    st.session_state.authenticated = True
                    st.session_state.username = user
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- YENİLENEN İŞLEM MERKEZİ (SIDEBAR) ---
    st.sidebar.divider()
    st.sidebar.markdown(f"👤 Yetkili: **{st.session_state.username.upper()}**")
    
    st.sidebar.subheader("📂 Veri Yönetimi")
    # Sayfa isimlerini daha anlamlı hale getirdik (İstersen bunları Branşlara göre de ayırabiliriz)
    page_map = {
        "Ana Portföy": "Sayfa1",
        "Ek Kayıtlar": "Sayfa2",
        "Arşiv": "Sayfa3",
        "Özel Dosyalar": "Sayfa4"
    }
    selected_display_name = st.sidebar.selectbox("Çalışma Alanı Seçin", list(page_map.keys()))
    selected_page = page_map[selected_display_name]
    
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ Menü")
    menu = {
        "➕ Poliçe Kaydet": "kaydet",
        "📊 Finansal Rapor": "rapor"
    }
    choice_label = st.sidebar.radio("Yapılacak İşlem", list(menu.keys()))
    choice = menu[choice_label]
    
    st.sidebar.divider()
    if st.sidebar.button("🔴 Güvenli Çıkış", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    # --- VERİ OKUMA ---
    try:
        df = conn.read(worksheet=selected_page, ttl=0)
    except:
        df = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'kaynak', 'brut_prim', 'oran', 'net_komisyon', 'tanzim_tarihi', 'baslangic_tarihi'])

    # --- ANA EKRAN ---
    if choice == "kaydet":
        st.markdown(f"### 📋 {selected_display_name} / Yeni Poliçe Girişi")
        with st.form("kayit_formu", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                musteri_adi = st.text_input("👤 Müşteri Adı Soyadı")
                police_turu = st.selectbox("📑 Branş / Poliçe Türü", list(KOMISYON_SOZLUGU.keys()))
            with c2:
                kaynak = st.radio("📡 Poliçe Kaynağı", ["Öz Portföy", "Dış Acente"], horizontal=True)
                brut_prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0, step=500.0)
            
            st.divider()
            t1, t2 = st.columns(2)
            with t1:
                tanzim_tarihi = st.date_input("📅 Tanzim Tarihi", value=datetime.now())
            with t2:
                baslangic_tarihi = st.date_input("🚀 Başlangıç Tarihi", value=datetime.now())
            
            st.write("")
            submit = st.form_submit_button("✅ HESAPLA VE TABLOYA İŞLE", use_container_width=True)
            
            if submit:
                if musteri_adi:
                    ana_oran = KOMISYON_SOZLUGU[police_turu]
                    uygulanan_oran = ana_oran / 2 if kaynak == "Dış Acente" else ana_oran
                    net_komisyon = brut_prim * (uygulanan_oran / 100)
                    
                    new_data = pd.DataFrame([{
                        "kayit_yapan": st.session_state.username,
                        "musteri_adi": musteri_adi,
                        "police_turu": police_turu,
                        "kaynak": kaynak,
                        "brut_prim": brut_prim,
                        "oran": f"%{uygulanan_oran:.2f}",
                        "net_komisyon": net_komisyon,
                        "tanzim_tarihi": tanzim_tarihi.strftime("%Y-%m-%d"),
                        "baslangic_tarihi": baslangic_tarihi.strftime("%Y-%m-%d")
                    }])
                    
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    conn.update(worksheet=selected_page, data=updated_df)
                    st.success(f"Kayıt Başarılı! Net Komisyon: {net_komisyon:,.2f} TL")
                    st.balloons()
                else:
                    st.error("Hata: Müşteri adı boş bırakılamaz!")

    elif choice == "rapor":
        st.markdown(f"### 📊 {selected_display_name} / Finansal Durum")
        if not df.empty:
            display_df = df if st.session_state.username in ["sercan", "admin"] else df[df['kayit_yapan'] == st.session_state.username]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Brüt Prim", f"{display_df['brut_prim'].sum():,.2f} TL")
            m2.metric("Toplam Net Komisyon", f"{display_df['net_komisyon'].sum():,.2f} TL")
            m3.metric("Poliçe Adedi", len(display_df))
            
            st.divider()
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Bu alanda henüz bir kayıt bulunamadı.")
