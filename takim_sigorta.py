import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta - Personel Paneli", layout="centered")

# 1. LOGO VE GÖRSEL DÜZENLEME
# Dosya adını logo.jpg olarak güncelledik
if os.path.exists("logo.jpg"):
    # Logoyu ortalamak için sütun kullanıyoruz
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.jpg", use_container_width=True)
else:
    st.markdown("<h1 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h1>", unsafe_allow_html=True)

# 2. KULLANICI GİRİŞ SİSTEMİ
# Buradan personel ekleyebilir veya şifreleri değiştirebilirsin
USER_CREDENTIALS = {
    "sercan": "takim2026",
    "personel1": "sigorta123",
    "admin": "admin44"
}

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.divider()
        st.subheader("🔑 Personel Giriş Paneli")
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap", use_container_width=True):
            # Küçük/büyük harf duyarlılığını önlemek için .lower() ekledik
            user_lower = user.lower()
            if user_lower in USER_CREDENTIALS and USER_CREDENTIALS[user_lower] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user_lower
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
        return False
    return True

if check_password():
    # 3. VERİTABANI (GOOGLE SHEETS) BAĞLANTISI
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Mevcut verileri oku
    try:
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
    except:
        existing_data = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'vade_tarihi', 'tutar'])

    # Yan Menü (Sidebar)
    st.sidebar.title("📌 Menü")
    st.sidebar.success(f"Personel: {st.session_state.username.upper()}")
    
    menu = ["Yeni Poliçe Ekle", "Poliçelerim", "Tüm Poliçeler (Admin)"]
    choice = st.sidebar.radio("Yapmak İstediğiniz İşlem", menu)
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

    # --- SAYFA İÇERİKLERİ ---

    if choice == "Yeni Poliçe Ekle":
        st.header("📝 Yeni Poliçe Kaydı")
        with st.form("police_form", clear_on_submit=True):
            musteri_adi = st.text_input("Müşteri Adı Soyadı")
            police_turu = st.selectbox("Poliçe Türü", ["Trafik", "Kasko", "DASK", "Sağlık", "Konut", "İş Yeri", "Diğer"])
            vade_tarihi = st.date_input("Vade Bitiş Tarihi")
            tutar = st.number_input("Poliçe Tutarı (TL)", min_value=0.0, step=100.0)
            
            submit = st.form_submit_button("Sisteme İşle")
            
            if submit:
                if musteri_adi:
                    new_row = pd.DataFrame([{
                        "kayit_yapan": st.session_state.username,
                        "musteri_adi": musteri_adi,
                        "police_turu": police_turu,
                        "vade_tarihi": vade_tarihi.strftime("%Y-%m-%d"),
                        "tutar": tutar
                    }])
                    # Yeni satırı ekle
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    # Google Sheets'i güncelle
                    conn.update(worksheet="Sheet1", data=updated_df)
                    st.success(f"{musteri_adi} kaydı başarıyla tamamlandı!")
                    st.balloons()
                else:
                    st.error("Lütfen müşteri adını giriniz.")

    elif choice == "Poliçelerim":
        st.header(f"🔍 Kayıtlarım ({st.session_state.username})")
        data = conn.read(worksheet="Sheet1", ttl=0)
        if not data.empty:
            # Sadece giriş yapan personelin kayıtlarını süz
            user_data = data[data['kayit_yapan'] == st.session_state.username]
            if not user_data.empty:
                st.dataframe(user_data, use_container_width=True)
            else:
                st.info("Henüz eklediğiniz bir poliçe bulunmuyor.")
        else:
            st.info("Sistemde hiç veri yok.")

    elif choice == "Tüm Poliçeler (Admin)":
        if st.session_state.username == "admin" or st.session_state.username == "sercan":
            st.header("📊 Genel Poliçe Listesi")
            data = conn.read(worksheet="Sheet1", ttl=0)
            st.dataframe(data, use_container_width=True)
            # Toplam Ciro Göstergesi
            toplam = data['tutar'].sum()
            st.metric("Toplam Tahsilat", f"{toplam:,.2f} TL")
        else:
            st.warning("Bu alanı görme yetkiniz yok!")
