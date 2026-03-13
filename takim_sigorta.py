import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta Takip", layout="centered")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

# Mevcut verileri oku
try:
    existing_data = conn.read(worksheet="Sheet1", ttl=0)
except:
    existing_data = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'vade_tarihi', 'tutar'])

st.title("🛡️ Takim Sigorta Poliçe Takip")

# Menü Seçenekleri
menu = ["Yeni Poliçe Ekle", "Poliçe Listesi"]
choice = st.sidebar.selectbox("İşlem Seçin", menu)

if choice == "Yeni Poliçe Ekle":
    st.subheader("📋 Yeni Kayıt Girişi")
    
    with st.form("police_form", clear_on_submit=True):
        kayit_yapan = st.text_input("Kayıt Yapan Personel")
        musteri_adi = st.text_input("Müşteri Adı Soyadı")
        police_turu = st.selectbox("Poliçe Türü", ["Trafik", "Kasko", "DASK", "Sağlık", "Konut", "Diğer"])
        vade_tarihi = st.date_input("Vade Bitiş Tarihi")
        tutar = st.number_input("Poliçe Tutarı (TL)", min_value=0.0, format="%.2f")
        
        submit = st.form_submit_button("Sisteme Kaydet")
        
        if submit:
            if musteri_adi and kayit_yapan:
                # Yeni veriyi hazırla
                new_row = pd.DataFrame([{
                    "kayit_yapan": kayit_yapan,
                    "musteri_adi": musteri_adi,
                    "police_turu": police_turu,
                    "vade_tarihi": vade_tarihi.strftime("%Y-%m-%d"),
                    "tutar": tutar
                }])
                
                # Mevcut veriye ekle
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                
                # Google Sheets'e geri yaz
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"{musteri_adi} adına poliçe başarıyla Google Tablolar'a kaydedildi!")
                st.balloons()
            else:
                st.error("Lütfen müşteri adı ve personel bilgisini doldurun.")

elif choice == "Poliçe Listesi":
    st.subheader("🔍 Kayıtlı Poliçeler")
    # Verileri Google Sheets'ten tazele
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("Henüz kayıtlı bir poliçe bulunamadı.")
