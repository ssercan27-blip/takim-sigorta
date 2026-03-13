import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, timedelta

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta - Yönetim Paneli", layout="wide")

# --- KOMİSYON ORANLARI ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# 1. LOGO VE SIDEBAR
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h2>", unsafe_allow_html=True)

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
    
    st.sidebar.divider()
    st.sidebar.markdown(f"👤 Yetkili: **{st.session_state.username.upper()}**")
    
    page_map = {"Ana Portföy": "Sayfa1", "Ek Kayıtlar": "Sayfa2", "Arşiv": "Sayfa3"}
    selected_display_name = st.sidebar.selectbox("📂 Çalışma Alanı", list(page_map.keys()))
    selected_page = page_map[selected_display_name]
    
    menu = {"➕ Poliçe Kaydet": "kaydet", "📊 Rapor ve Analiz": "rapor"}
    choice = menu[st.sidebar.radio("⚙️ Menü", list(menu.keys()))]
    
    if st.sidebar.button("🔴 Güvenli Çıkış", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    # --- VERİ OKUMA ---
    try:
        df = conn.read(worksheet=selected_page, ttl=0)
        df['tanzim_tarihi'] = pd.to_datetime(df['tanzim_tarihi'])
        df['baslangic_tarihi'] = pd.to_datetime(df['baslangic_tarihi'])
        df['bitis_tarihi'] = pd.to_datetime(df['bitis_tarihi'])
    except:
        df = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'kaynak', 'brut_prim', 'oran', 'net_komisyon', 'tanzim_tarihi', 'baslangic_tarihi', 'bitis_tarihi'])

    if choice == "kaydet":
        st.markdown(f"### 📋 {selected_display_name} / Yeni Poliçe Girişi")
        with st.form("kayit_formu", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                musteri_adi = st.text_input("👤 Müşteri Adı Soyadı")
                police_turu = st.selectbox("📑 Branş", list(KOMISYON_SOZLUGU.keys()))
            with c2:
                kaynak = st.radio("📡 Kaynak", ["Öz Portföy", "Dış Acente"], horizontal=True)
                brut_prim = st.number_input("💰 Brüt Prim (TL)", min_value=0.0, step=500.0)
            
            st.divider()
            t1, t2, t3 = st.columns(3)
            with t1:
                tanzim = st.date_input("📅 Tanzim", value=datetime.now())
            with t2:
                baslangic = st.date_input("🚀 Başlangıç", value=datetime.now())
            with t3:
                bitis = st.date_input("🏁 Bitiş (Vade)", value=baslangic + timedelta(days=365))
            
            if st.form_submit_button("✅ HESAPLA VE KAYDET", use_container_width=True):
                if musteri_adi:
                    ana_oran = KOMISYON_SOZLUGU[police_turu]
                    uyg_oran = ana_oran / 2 if kaynak == "Dış Acente" else ana_oran
                    komisyon = brut_prim * (uyg_oran / 100)
                    
                    new_row = pd.DataFrame([{
                        "kayit_yapan": st.session_state.username, "musteri_adi": musteri_adi,
                        "police_turu": police_turu, "kaynak": kaynak, "brut_prim": brut_prim,
                        "oran": f"%{uyg_oran:.2f}", "net_komisyon": komisyon,
                        "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"),
                        "baslangic_tarihi": baslangic.strftime("%Y-%m-%d"),
                        "bitis_tarihi": bitis.strftime("%Y-%m-%d")
                    }])
                    
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet=selected_page, data=updated_df)
                    st.success(f"Kayıt Başarılı!")
                    st.balloons()

    elif choice == "rapor":
        st.markdown(f"### 📊 {selected_display_name} / Finansal Analiz")
        
        if not df.empty:
            with st.expander("🔍 Filtrele ve Ara", expanded=False):
                f1, f2 = st.columns(2)
                search = f1.text_input("Müşteri Ara")
                branch = f2.multiselect("Branş", options=df['police_turu'].unique())
            
            f_df = df.copy()
            if search: f_df = f_df[f_df['musteri_adi'].str.contains(search, case=False, na=False)]
            if branch: f_df = f_df[f_df['police_turu'].isin(branch)]

            # --- GRAFİKLER ---
            if not f_df.empty:
                st.divider()
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.write("**Branş Bazlı Komisyon Dağılımı**")
                    fig1 = px.pie(f_df, values='net_komisyon', names='police_turu', hole=0.4)
                    st.plotly_chart(fig1, use_container_width=True)
                    
                with col_chart2:
                    st.write("**Kaynak Bazlı Kazanç**")
                    # Gruplama hatasını önlemek için kontrol
                    source_data = f_df.groupby('kaynak')['net_komisyon'].sum().reset_index()
                    fig2 = px.bar(source_data, x='kaynak', y='net_komisyon', color='kaynak')
                    st.plotly_chart(fig2, use_container_width=True)

                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.metric("Toplam Brüt", f"{f_df['brut_prim'].sum():,.2f} TL")
                m2.metric("Net Kazanç", f"{f_df['net_komisyon'].sum():,.2f} TL")
                m3.metric("Kayıt Sayısı", len(f_df))
                
                st.dataframe(f_df, use_container_width=True)
            else:
                st.warning("Aranan kriterlere uygun kayıt bulunamadı.")
        else:
            st.info("Henüz veri yok.")
