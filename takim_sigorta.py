import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import os

# --- LOGO DOSYA ADI ---
# Ekran görüntüne göre tam dosya ismini buraya yazdım
logo_path = 'image_0.png.jpg'

# --- SAYFA AYARLARI (SEKME SİMGESİ BURADA AYARLANIR) ---
try:
    # Sekme simgesi (favicon) için logonu kullanıyoruz
    st.set_page_config(
        page_title="Takim Sigorta", 
        layout="wide", 
        page_icon=logo_path # Kalkan yerine logon gelecek
    )
except:
    st.set_page_config(page_title="Takim Sigorta", layout="wide")

# --- VERİTABANI BAĞLANTISI ---
def veri_baglan():
    return sqlite3.connect('takim_sigorta.db', check_same_thread=False)

def tablo_olustur():
    conn = veri_baglan()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cariler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kayit_yapan TEXT,
            musteri_adi TEXT,
            police_turu TEXT,
            vade_tarihi TEXT,
            tutar REAL
        )
    ''')
    conn.commit()
    conn.close()

tablo_olustur()

# --- ÜST PANEL: LOGO VE BAŞLIK YAN YANA ---
header_col1, header_col2 = st.columns([1, 8])

with header_col1:
    if os.path.exists(logo_path):
        image = Image.open(logo_path)
        st.image(image, width=100)
    else:
        st.write("🛡️")

with header_col2:
    st.title("Takim Sigorta Takip Sistemi")

st.markdown("---") 

# --- YAN PANEL (SIDEBAR) ---
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=100)

st.sidebar.header("Kullanıcı Paneli")
kullanici = st.sidebar.selectbox("Kim İşlem Yapıyor?", ["Sercan", "Ekip Arkadaşı 1", "Ekip Arkadaşı 2"])

menu = ["Ana Sayfa", "Yeni Poliçe Ekle", "Poliçeleri Listele"]
secim = st.sidebar.selectbox("Menü İşlemleri", menu)

# --- ANA SAYFA ---
if secim == "Ana Sayfa":
    st.subheader(f"Hoş Geldin, {kullanici}!")
    st.info("Takim Sigorta dijital takip paneline hoş geldiniz.")
    
    conn = veri_baglan()
    df = pd.read_sql_query("SELECT * FROM cariler", conn)
    col_a, col_b = st.columns(2)
    col_a.metric("Toplam Kayıt", len(df))
    col_b.metric("Toplam Ciro (TL)", f"{df['tutar'].sum():,.2f}")
    conn.close()

# --- YENİ POLİÇE EKLE ---
elif secim == "Yeni Poliçe Ekle":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("kayit_formu", clear_on_submit=True):
        m_adi = st.text_input("Müşteri Adı Soyadı")
        p_turu = st.selectbox("Poliçe Türü", ["Trafik", "Kasko", "Konut", "DASK", "Sağlık", "İşyeri", "Diğer"])
        vade = st.date_input("Vade Tarihi")
        tutar = st.number_input("Poliçe Tutarı (TL)", min_value=0.0, step=100.0)
        
        submit = st.form_submit_button("Sisteme Kaydet")
        
        if submit:
            if m_adi:
                conn = veri_baglan()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cariler (kayit_yapan, musteri_adi, police_turu, vade_tarihi, tutar) VALUES (?, ?, ?, ?, ?)",
                               (kullanici, m_adi, p_turu, str(vade), tutar))
                conn.commit()
                conn.close()
                st.success(f"✅ {m_adi} adına poliçe başarıyla kaydedildi!")
            else:
                st.error("⚠️ Lütfen müşteri adını girmeyi unutmayın.")

# --- POLİÇELERİ LİSTELE ---
elif secim == "Poliçeleri Listele":
    st.subheader("📋 Güncel Poliçe Listesi")
    conn = veri_baglan()
    df = pd.read_sql_query("SELECT * FROM cariler ORDER BY id DESC", conn)
    
    search = st.text_input("Müşteri isminde ara...")
    if search:
        df = df[df['musteri_adi'].str.contains(search, case=False, na=False)]
    
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Listeyi İndir", csv, "takim_sigorta_liste.csv", "text/csv")
    conn.close()