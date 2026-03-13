import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta - Finansal Yönetim", layout="centered")

# 1. LOGO ALANI
if os.path.exists("logo.jpg"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.jpg", use_container_width=True)
else:
    st.markdown("<h1 style='text-align: center; color: #cc0000;'>🛡️ TAKİM SİGORTA</h1>", unsafe_allow_html=True)

# 2. KULLANICI BİLGİLERİ
USER_CREDENTIALS = {"sercan": "takim2026", "admin": "admin44", "personel1": "sigorta123"}

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
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    st.sidebar.title("📌 İşlem Merkezi")
    st.sidebar.write(f"Kullanıcı: **{st.session_state.username.upper()}**")
    
    selected_page = st.sidebar.selectbox("Çalışılacak Sayfa", ["Sayfa1", "Sayfa2", "Sayfa3", "Sayfa4"])
    menu = ["Poliçe Kaydet", "Kayıtları & Komisyonları Gör"]
    choice = st.sidebar.radio("İşlem Menüsü", menu)
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

    # --- VERİ OKUMA ---
    try:
        df = conn.read(worksheet=selected_page, ttl=0)
    except:
        df = pd.DataFrame(columns=['kayit_yapan', 'musteri_adi', 'police_turu', 'vade_tarihi', 'brut_prim', 'komisyon_orani', 'net_komisyon'])

    # --- SAYFA İÇERİĞİ ---
    if choice == "Poliçe Kaydet":
        st.header(f"📝 {selected_page} - Yeni Kayıt")
        with st.form("kayit_formu", clear_on_submit=True):
            musteri_adi = st.text_input("Müşteri Adı Soyadı")
            police_turu = st.selectbox("Poliçe Türü", ["Trafik", "Kasko", "DASK", "Sağlık", "Konut", "İş Yeri", "Diğer"])
            vade_tarihi = st.date_input("Vade Bitiş Tarihi")
            
            # Finansal Alanlar
            brut_prim = st.number_input("Poliçe Brüt Prim (TL)", min_value=0.0, step=100.0)
            komisyon_orani = st.slider("Komisyon Oranı (%)", 0, 100, 15) # Varsayılan %15
            
            submit = st.form_submit_button("Hesapla ve Kaydet")
            
            if submit:
                if musteri_adi:
                    # Komisyon Hesabı: Brüt Prim * (Oran / 100)
                    net_komisyon = brut_prim * (komisyon_orani / 100)
                    
                    new_data = pd.DataFrame([{
                        "kayit_yapan": st.session_state.username,
                        "musteri_adi": musteri_adi,
                        "police_turu": police_turu,
                        "vade_tarihi": vade_tarihi.strftime("%Y-%m-%d"),
                        "brut_prim": brut_prim,
                        "komisyon_orani": f"%{komisyon_orani}",
                        "net_komisyon": net_komisyon
                    }])
                    
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    conn.update(worksheet=selected_page, data=updated_df)
                    st.success(f"Kayıt Eklendi! Net Komisyonunuz: {net_komisyon:,.2f} TL")
                    st.balloons()
                else:
                    st.error("Müşteri adı boş geçilemez.")

    elif choice == "Kayıtları & Komisyonları Gör":
        st.header(f"🔍 {selected_page} Finansal Özet")
        
        if not df.empty:
            # Yetki Filtresi
            display_df = df if st.session_state.username in ["sercan", "admin"] else df[df['kayit_yapan'] == st.session_state.username]
            
            # Özet Metrikler
            c1, c2 = st.columns(2)
            toplam_prim = display_df['brut_prim'].sum()
            toplam_komisyon = display_df['net_komisyon'].sum()
            
            c1.metric("Toplam Ciro (Brüt)", f"{toplam_prim:,.2f} TL")
            c2.metric("Toplam Kazanç (Komisyon)", f"{toplam_komisyon:,.2f} TL", delta_color="normal")
            
            st.divider()
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Bu sayfada henüz kayıt bulunmuyor.")
