import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta Giriş", layout="centered")

# 1. LOGO VE GÖRSEL DÜZENLEME
# Dosya adını tam olarak senin belirttiğin gibi güncelledim
if os.path.exists("image_0.png.jpg"):
    st.image("image_0.png.jpg", width=200)
else:
    st.title("🛡️ TAKİM SİGORTA")

# 2. KULLANICI GİRİŞ SİSTEMİ
USER_CREDENTIALS = {
    "sercan": "takim2026",
    "personel1": "sigorta123",
    "admin": "admin44"
}

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("🔑 Personel Girişi")
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
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
    
    try:
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
    except:
        existing_data = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'vade_tarihi', 'tutar'])

    st.sidebar.success(f"Hoş geldin, {st.session_state.username.capitalize()}")
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

    st.title("🛡️ Poliçe Yönetim Sistemi")

    menu = ["Yeni Poliçe Ekle", "Poliçe Listesi (Kişisel)"]
    choice = st.sidebar.selectbox("İşlem Menüsü", menu)

    if choice == "Yeni Poliçe Ekle":
        st.subheader("📋 Yeni Kayıt Girişi")
        with st.form("police_form", clear_on_submit=True):
            musteri_adi = st.text_input("Müşteri Adı Soyadı")
            police_turu = st.selectbox("Poliçe Türü", ["Trafik", "Kasko", "DASK", "Sağlık", "Konut", "Diğer"])
            vade_tarihi = st.date_input("Vade Bitiş Tarihi")
            tutar = st.number_input("Poliçe Tutarı (TL)", min_value=0.0, format="%.2f")
            
            submit = st.form_submit_button("Sisteme Kaydet")
            
            if submit:
                if musteri_adi:
                    new_row = pd.DataFrame([{
                        "kayit_yapan": st.session_state.username,
                        "musteri_adi": musteri_adi,
                        "police_turu": police_turu,
                        "vade_tarihi": vade_tarihi.strftime("%Y-%m-%d"),
                        "tutar": tutar
                    }])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    st.success("Kayıt başarıyla Google Tablo'ya eklendi!")
                else:
                    st.error("Müşteri adı boş bırakılamaz.")

    elif choice == "Poliçe Listesi (Kişisel)":
        st.subheader(f"🔍 {st.session_state.username.capitalize()} - Kayıtlı Poliçeler")
        data = conn.read(worksheet="Sheet1", ttl=0)
        
        if not data.empty:
            user_data = data[data['kayit_yapan'] == st.session_state.username]
            if not user_data.empty:
                st.dataframe(user_data, use_container_width=True)
            else:
                st.info("Henüz size ait bir kayıt bulunamadı.")
        else:
            st.info("Sistemde kayıtlı veri yok.")
