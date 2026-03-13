import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta - Yönetim Paneli", layout="centered")

# 1. LOGO ALANI
if os.path.exists("logo.jpg"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.jpg", use_container_width=True)
else:
    st.markdown("<h1 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h1>", unsafe_allow_html=True)

# 2. KULLANICI BİLGİLERİ
USER_CREDENTIALS = {
    "sercan": "takim2026",
    "admin": "admin44",
    "personel1": "sigorta123"
}

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.divider()
        st.subheader("🔑 Personel Giriş Paneli")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sisteme Giriş Yap", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
        return False
    return True

if check_password():
    # 3. GOOGLE SHEETS BAĞLANTISI
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Yan Menü
    st.sidebar.title("📌 İşlem Merkezi")
    st.sidebar.write(f"Kullanıcı: **{st.session_state.username.upper()}**")
    
    # Sayfa Seçimi (Buraya Sayfa 2, 3, 4'ü ekledik)
    selected_page = st.sidebar.selectbox("Çalışılacak Sayfa", ["Sayfa1", "Sayfa2", "Sayfa3", "Sayfa4"])
    
    menu = ["Poliçe Kaydet", "Kayıtları Görüntüle"]
    choice = st.sidebar.radio("İşlem Menüsü", menu)
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

    # --- VERİ OKUMA ---
    try:
        # Seçilen sayfadaki veriyi oku
        df = conn.read(worksheet=selected_page, ttl=0)
    except Exception:
        # Sayfa boşsa veya hata verirse sütunları oluştur
        df = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'vade_tarihi', 'tutar'])

    # --- SAYFA İÇERİĞİ ---
    if choice == "Poliçe Kaydet":
        st.header(f"📝 {selected_page} - Yeni Kayıt")
        with st.form("kayit_formu", clear_on_submit=True):
            musteri_adi = st.text_input("Müşteri Adı Soyadı")
            police_turu = st.selectbox("Poliçe Türü", ["Trafik", "Kasko", "DASK", "Sağlık", "Konut", "İş Yeri", "Diğer"])
            vade_tarihi = st.date_input("Vade Bitiş Tarihi")
            tutar = st.number_input("Tutar (TL)", min_value=0.0, step=100.0)
            
            submit = st.form_submit_button("Veriyi Tabloya Gönder")
            
            if submit:
                if musteri_adi:
                    new_data = pd.DataFrame([{
                        "kayit_yapan": st.session_state.username,
                        "musteri_adi": musteri_adi,
                        "police_turu": police_turu,
                        "vade_tarihi": vade_tarihi.strftime("%Y-%m-%d"),
                        "tutar": tutar
                    }])
                    # Mevcut veriye ekle ve gönder
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    conn.update(worksheet=selected_page, data=updated_df)
                    st.success(f"Başarıyla {selected_page} sekmesine kaydedildi!")
                    st.balloons()
                else:
                    st.error("Lütfen müşteri adını doldurun.")

    elif choice == "Kayıtları Görüntüle":
        st.header(f"🔍 {selected_page} Verileri")
        if not df.empty:
            # Sercan veya Admin her şeyi görür, personel sadece kendi yaptıklarını
            if st.session_state.username in ["sercan", "admin"]:
                st.dataframe(df, use_container_width=True)
                st.metric("Bu Sayfadaki Toplam Ciro", f"{df['tutar'].sum():,.2f} TL")
            else:
                user_df = df[df['kayit_yapan'] == st.session_state.username]
                st.dataframe(user_df, use_container_width=True)
        else:
            st.info(f"{selected_page} sekmesinde henüz hiç kayıt yok.")
