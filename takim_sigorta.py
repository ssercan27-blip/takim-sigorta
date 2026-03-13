import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. AYARLAR VE LOGO ---
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
        # Sütunları normalize et (Boşlukları temizle)
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 3. KULLANICI YÖNETİMİ (HAFIZALI) ---
if "users_db" not in st.session_state:
    st.session_state.users_db = [
        {"kullanici": "sercan", "sifre": "takim2026", "yetki": "Admin"},
        {"kullanici": "personel", "sifre": "takim2024", "yetki": "Personel"}
    ]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Kullanıcı Adı").lower()
        p_in = st.text_input("Şifre", type="password")
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            found_user = next((item for item in st.session_state.users_db if item["kullanici"] == u_in and item["sifre"] == p_in), None)
            if found_user:
                st.session_state.update({"authenticated": True, "username": u_in, "role": found_user["yetki"]})
                st.rerun()
            else: st.error("Hatalı Giriş!")
    st.stop()

# --- 4. ANA YAPI ---
df = load_data_safe()
if logo_file: st.sidebar.image(logo_file, use_container_width=True)

# Menü Tanımları
menu = {"📝 Yeni Poliçe": "yeni", "🔎 Poliçe Takibi": "takip", "💳 Ödeme & Cari": "odeme", "📊 Analiz": "analiz"}
if st.session_state.role == "Admin": menu["🔐 Yönetici Paneli"] = "admin"
choice = menu[st.sidebar.radio("Menü Seçimi", list(menu.keys()))]

# --- 5. SAYFALAR ---

# --- YENİ POLİÇE KAYIT ---
if choice == "yeni":
    st.subheader("📝 Yeni Poliçe Kayıt Formu")
    with st.form("yeni_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("Şirket", ["Allianz", "Axa", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        brans = c4.selectbox("Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        plaka = c5.text_input("Plaka / TC No")

        # Trafik Özel Seçimi
        vade_secimi = "1 Yıl"
        if brans == "TRAFİK":
            vade_secimi = st.radio("Poliçe Süresi", ["2 Ay", "1 Yıl"], horizontal=True)
        
        c6, c7 = st.columns(2)
        tanzim = c6.date_input("Tanzim Tarihi", datetime.now())
        basla = c7.date_input("Başlangıç Tarihi", datetime.now())
        
        c8, c9 = st.columns(2)
        t_tutar = c8.number_input("Toplam Tutar (TL)", min_value=0.0)
        a_ucret = c9.number_input("Alınan Ücret (TL)", min_value=0.0)
        
        tel = st.text_input("Müşteri Telefon (5xxxxxxxxx)")
        
        if st.form_submit_button("✅ SİSTEME VE SHEETS'E KAYDET"):
            # Bitiş Tarihi Hesaplama
            if brans == "TRAFİK" and vade_secimi == "2 Ay":
                bitis = basla + relativedelta(months=2)
            else:
                bitis = basla + relativedelta(years=1)
            
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

# --- POLİÇE TAKİBİ (Sadece Aktifler) ---
elif choice == "takip":
    st.subheader("🔎 Aktif Poliçeler Takip Ekranı")
    if not df.empty:
        # FİLTRE: Sadece arsiv sütunu FALSE olanlar
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"].copy()
        if not active_df.empty:
            for i, row in active_df.iterrows():
                with st.container(border=True):
                    col_detay, col_wa = st.columns([0.8, 0.2])
                    col_detay.markdown(f"👤 **{row['müşteri_adı']}** | 🚗 {row['plaka_tc']} | 📅 Vade: **{row['bitiş_tarihi']}**")
                    col_detay.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']} | 👤 Kayıt: {row['kayıt_yapan']}")
                    # WhatsApp
                    tel_no = str(row['telefon']).strip()
                    wa_msg = f"Sayın%20{row['müşteri_adı']},%20{row['poliçe_türü']}%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolacaktır."
                    col_wa.link_button("💬 Mesaj At", f"https://wa.me/90{tel_no}?text={wa_msg}", use_container_width=True)
        else: st.info("Şu an takip edilecek aktif bir poliçe bulunmuyor.")

# --- ÖDEME & CARİ ---
elif choice == "odeme":
    st.subheader("💳 Cari Borç / Alacak Takibi")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        df['alinan_ucret'] = pd.to_numeric(df['alinan_ucret'], errors='coerce').fillna(0)
        kalan = df['toplam_tutar'].sum() - df['alinan_ucret'].sum()
        st.metric("Bekleyen Tahsilat", f"{kalan:,.2f} TL")
        borclular = df[df['toplam_tutar'] > df['alinan_ucret']]
        st.table(borclular[['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret']])

# --- ANALİZ ---
elif choice == "analiz":
    st.subheader("📊 Grafiksel Analiz")
    if not df.empty:
        df['toplam_tutar'] = pd.to_numeric(df['toplam_tutar'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(df, names='sigorta_sirketi', title="Şirket Dağılımı"))
        c2.plotly_chart(px.bar(df, x='poliçe_türü', y='toplam_tutar', title="Branş Ciro"))

# --- YÖNETİCİ PANELİ (Kullanıcı İşlemleri) ---
elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    tab_users, tab_db = st.tabs(["👥 Kullanıcı Yönetimi", "🗂️ Tüm Veritabanı"])
    
    with tab_users:
        st.write("### Mevcut Kullanıcı Listesi")
        st.table(pd.DataFrame(st.session_state.users_db))
        
        with st.expander("➕ Yeni Kullanıcı Ekle veya Şifre Güncelle"):
            new_u = st.text_input("Kullanıcı Adı")
            new_p = st.text_input("Şifre")
            new_y = st.selectbox("Yetki", ["Admin", "Personel"])
            if st.button("Kullanıcıyı Kaydet"):
                # Mevcut olanı silip yenisini ekle (Güncelleme mantığı)
                st.session_state.users_db = [u for u in st.session_state.users_db if u["kullanici"] != new_u]
                st.session_state.users_db.append({"kullanici": new_u, "sifre": new_p, "yetki": new_y})
                st.success(f"{new_u} kullanıcısı güncellendi."); st.rerun()

    with tab_db:
        st.write("### Google Sheets Üzerindeki Ham Veriler")
        st.dataframe(df)

if st.sidebar.button("🔴 Güvenli Çıkış"):
    st.session_state.authenticated = False; st.rerun()
