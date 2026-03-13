import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import urllib.parse

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KOMİSYON VE AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. LOGO VE SIDEBAR
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

# 2. GÜVENLİK SİSTEMİ
USER_CREDENTIALS = {"sercan": "takim2026", "admin": "admin44"}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.header("🔑 Yetkili Girişi")
        user = st.text_input("Kullanıcı Adı").lower()
        pw = st.text_input("Şifre", type="password")
        if st.button("Sistemi Başlat", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user] == pw:
                st.session_state.authenticated = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Giriş başarısız!")
    st.stop()

# --- VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown(f"🚀 Yetkili: **{st.session_state.username.upper()}**")
page_map = {"Ana Portföy": "Sayfa1", "Ek Kayıtlar": "Sayfa2", "Arşiv": "Sayfa3"}
selected_page = page_map[st.sidebar.selectbox("📂 Veri Tabanı", list(page_map.keys()))]

# İŞLEM MERKEZİ MENÜSÜ
menu = {
    "📝 Yeni Poliçe": "kaydet",
    "🔎 Poliçe Takibi": "takip",
    "📊 Finansal Analiz": "rapor",
    "👤 Müşteri Detayları": "cari",
    "🔔 Vade Takip": "vade"
}
choice = menu[st.sidebar.radio("⚙️ İşlem Merkezi", list(menu.keys()))]

if st.sidebar.button("🔴 Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# VERİ OKUMA VE ÖN HAZIRLIK
try:
    df = conn.read(worksheet=selected_page, ttl=0)
    
    # EKSİK SÜTUN KONTROLÜ VE TARİH DÜZELTME (KRİTİK KISIM)
    if 'police_no' not in df.columns: df['police_no'] = ""
    
    # Tarih sütunlarını zorla tarih formatına çevir, hata varsa 'NaT' (Boş tarih) yap
    df['tanzim_tarihi'] = pd.to_datetime(df['tanzim_tarihi'], errors='coerce')
    df['baslangic_tarihi'] = pd.to_datetime(df['baslangic_tarihi'], errors='coerce')
    df['bitis_tarihi'] = pd.to_datetime(df['bitis_tarihi'], errors='coerce')
    
except:
    df = pd.DataFrame(columns=['kayit_yapan', 'police_no', 'musteri_adi', 'police_turu', 'kaynak', 'brut_prim', 'oran', 'net_komisyon', 'tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi', 'telefon'])

# --- SAYFA İÇERİKLERİ ---

if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Kaydı")
    with st.form("yeni_kayit", clear_on_submit=True):
        p_no = st.text_input("🔢 Poliçe Numarası")
        
        c1, c2 = st.columns(2)
        musteri = c1.text_input("👤 Müşteri Adı Soyadı")
        tel = c2.text_input("📱 Telefon (Örn: 90530...)")
        
        c3, c4 = st.columns(2)
        brans = c3.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
        kaynak = c4.radio("📡 Kaynak", ["Öz Portföy", "Dış Acente"], horizontal=True)
        
        prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0, step=100.0)
        
        st.divider()
        t1, t2, t3 = st.columns(3)
        tanzim_val = t1.date_input("📅 Tanzim Tarihi", datetime.now())
        baslangic_val = t2.date_input("🚀 Başlangıç Tarihi", datetime.now())
        
        sure_secenekleri = {"1 Yıllık": relativedelta(years=1), "2 Aylık": relativedelta(months=2)}
        sure_etiket = t3.selectbox("⏳ Poliçe Süresi", list(sure_secenekleri.keys()))
        
        bitis_val = baslangic_val + sure_secenekleri[sure_etiket]
        st.caption(f"ℹ️ Hesaplanan Bitiş: **{bitis_val.strftime('%d.%m.%Y')}**")
        
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            if all([p_no, musteri, tel, brans, prim > 0]):
                oran = KOMISYON_SOZLUGU[brans]
                uyg_oran = oran / 2 if kaynak == "Dış Acente" else oran
                kazanc = prim * (uyg_oran / 100)
                
                # VERİYİ KAYDEDERKEN STRING OLARAK FORMATLIYORUZ (GSHEETS İÇİN)
                new_row = pd.DataFrame([{
                    "kayit_yapan": st.session_state.username, 
                    "police_no": str(p_no), 
                    "musteri_adi": musteri, 
                    "police_turu": brans,
                    "kaynak": kaynak, 
                    "brut_prim": prim, 
                    "oran": f"%{uyg_oran:.2f}", 
                    "net_komisyon": kazanc,
                    "tanzim_tarihi": tanzim_val.strftime("%Y-%m-%d"), 
                    "baslangic_tarihi": baslangic_val.strftime("%Y-%m-%d"),
                    "bitis_tarihi": bitis_val.strftime("%Y-%m-%d"), 
                    "telefon": tel
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet=selected_page, data=updated_df)
                st.success(f"Poliçe {p_no} başarıyla kaydedildi.")
                st.rerun()
            else:
                st.error("⚠️ Lütfen zorunlu alanları doldurun.")

elif choice == "takip":
    st.subheader("🔎 Poliçe Takip ve Filtreleme")
    if not df.empty:
        col1, col2, col3 = st.columns([2, 2, 2])
        s_no = col1.text_input("🔢 Poliçe No Ara")
        s_isim = col2.text_input("👤 Müşteri Ara")
        s_brans = col3.multiselect("📑 Branş Seç", options=sorted(df['police_turu'].unique()))
        
        f_df = df.copy()
        if s_no: f_df = f_df[f_df['police_no'].astype(str).str.contains(s_no, case=False, na=False)]
        if s_isim: f_df = f_df[f_df['musteri_adi'].astype(str).str.contains(s_isim, case=False, na=False)]
        if s_brans: f_df = f_df[f_df['police_turu'].isin(s_brans)]
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Bulunan Poliçe", len(f_df))
        m2.metric("Toplam Brüt Prim", f"{f_df['brut_prim'].sum():,.2f} TL")
        m3.metric("Tahmini Net Kazanç", f"{f_df['net_komisyon'].sum():,.2f} TL")
        
        # Tabloyu Tanzim Tarihine göre sırala (Tarih formatında olduğu için düzgün sıralar)
        f_df = f_df.sort_values('tanzim_tarihi', ascending=False)
        
        display_df = f_df[['police_no', 'musteri_adi', 'police_turu', 'brut_prim', 'net_komisyon', 'tanzim_tarihi', 'bitis_tarihi', 'telefon']]
        display_df.columns = ['Poliçe No', 'Müşteri Adı', 'Branş', 'Brüt Prim', 'Komisyon', 'Tanzim', 'Vade Sonu', 'Telefon']
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tanzim": st.column_config.DateColumn("📅 Tanzim", format="DD.MM.YYYY"),
                "Vade Sonu": st.column_config.DateColumn("🏁 Vade Sonu", format="DD.MM.YYYY"),
                "Brüt Prim": st.column_config.NumberColumn("💰 Prim", format="%.2f TL"),
                "Komisyon": st.column_config.NumberColumn("📈 Komisyon", format="%.2f TL"),
            }
        )
    else:
        st.info("Henüz kayıtlı poliçe bulunamadı.")

# (Diğer bölümler aynı kalabilir, tarih düzelten kısım yukarıdaki 'Veri Okuma' ve 'Takip' kısmıdır)
elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    if not df.empty:
        # Tarihi olmayan satırları rapordan geçici olarak çıkar ki hata vermesin
        rdf = df.dropna(subset=['tanzim_tarihi'])
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Brüt Prim", f"{rdf['brut_prim'].sum():,.2f} TL")
        m2.metric("Toplam Net Kazanç", f"{rdf['net_komisyon'].sum():,.2f} TL")
        m3.metric("Poliçe Sayısı", len(rdf))
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(rdf, values='net_komisyon', names='police_turu', title="Branş Dağılımı", hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            rdf['ay'] = rdf['tanzim_tarihi'].dt.strftime('%Y-%m')
            aylik = rdf.groupby('ay')['net_komisyon'].sum().reset_index()
            fig2 = px.line(aylik, x='ay', y='net_komisyon', title="Aylık Kazanç Trendi", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

elif choice == "cari":
    st.subheader("👤 Müşteri Detayları")
    if not df.empty:
        df['benzersiz_musteri'] = df['musteri_adi'].astype(str) + " - " + df['telefon'].astype(str)
        secilen = st.selectbox("Müşteri Seçin", ["Seçiniz..."] + sorted(list(df['benzersiz_musteri'].unique())))
        
        if secilen != "Seçiniz...":
            m_df = df[df['benzersiz_musteri'] == secilen]
            st.info(f"**Müşteri:** {secilen} | **Poliçe Sayısı:** {len(m_df)}")
            st.dataframe(m_df[['police_no', 'police_turu', 'brut_prim', 'tanzim_tarihi', 'bitis_tarihi']], use_container_width=True, hide_index=True)

elif choice == "vade":
    st.subheader("🔔 Vade Takip Merkezi")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        # Tarihi olmayanları filtrele
        v_df = df.dropna(subset=['bitis_tarihi']).copy()
        v_df['kalan_gun'] = (v_df['bitis_tarihi'] - bugun).dt.days
        vade_df = v_df[(v_df['kalan_gun'] <= 30) & (v_df['kalan_gun'] >= -5)].sort_values('kalan_gun')
        
        if not vade_df.empty:
            for _, row in vade_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    durum = "🔴" if row['kalan_gun'] < 0 else "🟠"
                    col1.markdown(f"### {durum} {row['musteri_adi']}")
                    col1.write(f"**Poliçe No:** {row['police_no']} | **Vade:** {row['bitis_tarihi'].strftime('%d.%m.%Y')}")
                    
                    tel = str(row['telefon']).strip()
                    if not tel.startswith('90') and len(tel) > 0: tel = "90" + (tel[1:] if tel.startswith('0') else tel)
                    msg = f"Sayın {row['musteri_adi']}, Takim Sigorta'dan hatırlatırız: {row['police_no']} nolu poliçe vadeniz dolmaktadır."
                    wa_url = f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}"
                    col2.link_button("💬 Hatırlat", wa_url, use_container_width=True)
        else: st.success("Yakın zamanda vadesi dolacak poliçe yok.")
