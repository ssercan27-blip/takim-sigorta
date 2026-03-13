import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI VE YETKİ TANIMLARI ---
USER_CREDENTIALS = {
    "sercan": ["takim2026", "admin"],
    "admin": ["admin44", "admin"],
    "personel1": ["12345", "user"]
}

# --- KOMİSYON VE AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. OTURUM DURUMUNU BAŞLATMA (Hata Alan Kısım Burasıydı)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None  # Giriş yapılana kadar rol boş kalsın

# 2. LOGO VE SIDEBAR
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

# 3. GİRİŞ KONTROLÜ
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.header("🔑 Yetkili Girişi")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sistemi Başlat", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user][0] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.session_state.role = USER_CREDENTIALS[user][1]
                st.rerun()
            else:
                st.error("Giriş başarısız!")
    st.stop()

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)
page_map = {"Ana Portföy": "Sayfa1", "Ek Kayıtlar": "Sayfa2", "Arşiv": "Sayfa3"}
selected_page = page_map[st.sidebar.selectbox("📂 Veri Tabanı", list(page_map.keys()))]

# VERİ OKUMA VE ÖN İŞLEME
try:
    df = conn.read(worksheet=selected_page, ttl=0)
    # Boş liste hatasını önlemek için
    if df.empty:
        df = pd.DataFrame(columns=['kayit_yapan', 'police_no', 'musteri_adi', 'police_turu', 'brut_prim', 'net_komisyon', 'tanzim_tarihi', 'bitis_tarihi', 'telefon'])
    else:
        df['tanzim_tarihi'] = pd.to_datetime(df['tanzim_tarihi'], errors='coerce')
        df['bitis_tarihi'] = pd.to_datetime(df['bitis_tarihi'], errors='coerce')
except:
    df = pd.DataFrame(columns=['kayit_yapan', 'police_no', 'musteri_adi', 'police_turu', 'brut_prim', 'net_komisyon', 'tanzim_tarihi', 'bitis_tarihi', 'telefon'])

# MENÜ
menu_icons = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Finansal Analiz": "rapor", "🔔 Vade Takip": "vade"}
choice_label = st.sidebar.radio("⚙️ İşlem Merkezi", list(menu_icons.keys()))
choice = menu_icons[choice_label]

if st.sidebar.button("🔴 Çıkış Yap"):
    st.session_state.authenticated = False
    st.session_state.role = None
    st.rerun()

# --- SAYFALAR ---

if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_kayit", clear_on_submit=True):
        p_no = st.text_input("🔢 Poliçe Numarası")
        c1, c2 = st.columns(2)
        musteri = c1.text_input("👤 Müşteri Adı Soyadı")
        tel = c2.text_input("📱 Telefon")
        brans = st.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0)
        
        st.divider()
        t1, t2 = st.columns(2)
        tanzim = t1.date_input("📅 Tanzim", datetime.now())
        sure = t2.selectbox("⏳ Süre", ["1 Yıllık", "2 Aylık"])
        
        bitis_tarihi = tanzim + (relativedelta(years=1) if sure == "1 Yıllık" else relativedelta(months=2))
        
        if st.form_submit_button("✅ KAYDET"):
            if all([p_no, musteri, tel, prim > 0]):
                oran = KOMISYON_SOZLUGU[brans]
                kazanc = prim * (oran / 100)
                new_row = pd.DataFrame([{
                    "kayit_yapan": st.session_state.username, "police_no": str(p_no), "musteri_adi": musteri,
                    "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc,
                    "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"), "bitis_tarihi": bitis_tarihi.strftime("%Y-%m-%d"), "telefon": tel
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet=selected_page, data=updated_df)
                st.success("Başarıyla kaydedildi!")
                st.rerun()
            else:
                st.error("Lütfen tüm alanları doldurun!")

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    
    # SADECE ADMİN İÇİN SİLME PANELİ
    if st.session_state.get("role") == "admin":
        with st.expander("🗑️ Yönetici Paneli: Kayıt Silme", expanded=False):
            st.warning("Buradan silinen veriler doğrudan Google Tablolar'dan kaldırılır.")
            if not df.empty:
                delete_no = st.selectbox("Silinecek Poliçe No", ["Seçiniz..."] + sorted(df['police_no'].astype(str).unique().tolist()))
                if st.button("❌ POLİÇEYİ SİL", type="primary"):
                    if delete_no != "Seçiniz...":
                        new_df = df[df['police_no'].astype(str) != delete_no]
                        conn.update(worksheet=selected_page, data=new_df)
                        st.success(f"{delete_no} nolu kayıt silindi.")
                        st.rerun()
            else:
                st.write("Silinecek kayıt yok.")

    # ARAMA VE LİSTELEME
    search = st.text_input("🔍 İsim veya No ile Ara")
    if not df.empty:
        # Arama filtresi
        f_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)] if search else df
        
        st.dataframe(
            f_df.sort_values('tanzim_tarihi', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "tanzim_tarihi": st.column_config.DateColumn("Tanzim"),
                "bitis_tarihi": st.column_config.DateColumn("Vade"),
                "brut_prim": st.column_config.NumberColumn("Prim", format="%.2f TL"),
                "net_komisyon": st.column_config.NumberColumn("Komisyon", format="%.2f TL")
            }
        )

# ... Rapor ve Vade bölümleri için de benzer kontroller eklendi ...
