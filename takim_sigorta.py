import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse
import plotly.express as px

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

# 1. OTURUM BAŞLATMA
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None

# 2. GİRİŞ KONTROLÜ
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

# --- VERİ BAĞLANTISI VE OKUMA ---
conn = st.connection("gsheets", type=GSheetsConnection)
page_map = {"Ana Portföy": "Sayfa1", "Ek Kayıtlar": "Sayfa2", "Arşiv": "Sayfa3"}
selected_page = st.sidebar.selectbox("📂 Veri Tabanı", list(page_map.keys()))
worksheet_name = page_map[selected_page]

def load_data():
    try:
        raw_df = conn.read(worksheet=worksheet_name, ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame()
        
        # SÜTUN İSİMLERİNİ STANDARTLAŞTIR (Hata Önleyici)
        # Hepsini küçük harf yap, boşlukları alt tireye çevir
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        
        # Tarih sütunlarını güvenli dönüştür
        for col in ['tanzim_tarihi', 'bitis_tarihi', 'baslangic_tarihi']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_datetime(raw_df[col], errors='coerce')
        
        # Sayısal sütunları güvenli dönüştür
        for col in ['brut_prim', 'net_komisyon']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
                
        return raw_df
    except Exception as e:
        st.error(f"Veri okunurken hata oluştu: {e}")
        return pd.DataFrame()

df = load_data()

# SIDEBAR MENÜ
st.sidebar.markdown(f"👤 Yetkili: **{st.session_state.username.upper()}**")
menu_icons = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Finansal Analiz": "rapor", "🔔 Vade Takip": "vade"}
choice_label = st.sidebar.radio("⚙️ İşlem Merkezi", list(menu_icons.keys()))
choice = menu_icons[choice_label]

if st.sidebar.button("🔴 Çıkış Yap"):
    st.session_state.authenticated = False
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
                
                # Mevcut veriye ekle
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet=worksheet_name, data=updated_df)
                st.success("Kayıt Başarılı!")
                st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    
    if st.session_state.get("role") == "admin" and not df.empty:
        with st.expander("🗑️ Kayıt Sil (Admin)", expanded=False):
            delete_no = st.selectbox("Silinecek No", ["Seçiniz..."] + df['police_no'].astype(str).tolist())
            if st.button("❌ SİL") and delete_no != "Seçiniz...":
                new_df = df[df['police_no'].astype(str) != delete_no]
                conn.update(worksheet=worksheet_name, data=new_df)
                st.success("Silindi!")
                st.rerun()

    search = st.text_input("🔍 Hızlı Arama")
    if not df.empty:
        f_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
        st.dataframe(f_df, use_container_width=True, hide_index=True)
    else:
        st.info("Gösterilecek veri bulunamadı.")

elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    if not df.empty and 'net_komisyon' in df.columns:
        m1, m2 = st.columns(2)
        m1.metric("Toplam Prim", f"{df['brut_prim'].sum():,.2f} TL")
        m2.metric("Toplam Komisyon", f"{df['net_komisyon'].sum():,.2f} TL")
        
        fig = px.pie(df, values='net_komisyon', names='police_turu', title="Branş Dağılımı")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Analiz için veri bulunamadı.")

elif choice == "vade":
    st.subheader("🔔 Vade Takip")
    if not df.empty and 'bitis_tarihi' in df.columns:
        bugun = pd.Timestamp(datetime.now().date())
        # Boş tarihleri temizle
        v_df = df.dropna(subset=['bitis_tarihi']).copy()
        v_df['kalan'] = (v_df['bitis_tarihi'] - bugun).dt.days
        yaklasan = v_df[v_df['kalan'] <= 30].sort_values('kalan')
        
        if not yaklasan.empty:
            st.write(yaklasan[['police_no', 'musteri_adi', 'bitis_tarihi', 'kalan']])
        else:
            st.success("Yakın zamanda vadesi dolacak poliçe yok.")
    else:
        st.info("Vade takibi için geçerli veri yok.")
