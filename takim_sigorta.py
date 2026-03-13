import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
import plotly.express as px

# LOGO
def get_logo():
    for ext in ["png","jpg","jpeg"]:
        if os.path.exists(f"logo.{ext}"):
            return f"logo.{ext}"
    return None

logo_file = get_logo()

st.set_page_config(
    page_title="Takim Sigorta | İşlem Merkezi",
    page_icon=logo_file if logo_file else "🛡️",
    layout="wide"
)

# GOOGLE SHEETS BAĞLANTI
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)

        if df is None or df.empty:
            return pd.DataFrame()

        df.columns = [str(c).strip().lower().replace(" ","_").replace("/","_") for c in df.columns]

        if "arsiv" in df.columns:
            df["arsiv"] = df["arsiv"].astype(str).str.upper().str.strip()

        return df

    except:
        return pd.DataFrame()

# GİRİŞ SİSTEMİ
if "authenticated" not in st.session_state:
    st.session_state.authenticated=False
    st.session_state.username=""
    st.session_state.role=""

if not st.session_state.authenticated:

    c1,c2,c3 = st.columns([1,1.2,1])

    with c2:

        if logo_file:
            st.image(logo_file,use_container_width=True)

        st.markdown("<h2 style='text-align:center'>Takim Sigorta Giriş</h2>",unsafe_allow_html=True)

        u_in = st.text_input("Kullanıcı Adı").lower().strip()
        p_in = st.text_input("Şifre",type="password")

        if st.button("SİSTEME GİRİŞ",use_container_width=True):

            if u_in=="sercan" and p_in=="takim2026":

                st.session_state.authenticated=True
                st.session_state.username="sercan"
                st.session_state.role="Admin"
                st.rerun()

            elif u_in=="personel" and p_in=="takim2024":

                st.session_state.authenticated=True
                st.session_state.username="personel"
                st.session_state.role="User"
                st.rerun()

            else:
                st.error("Kullanıcı adı veya şifre hatalı")

    st.stop()

# VERİYİ YÜKLE
df = load_data_safe()

if logo_file:
    st.sidebar.image(logo_file,use_container_width=True)

st.sidebar.markdown(f"**Hoş geldin {st.session_state.username.upper()}**")

menu_options = [
"📝 Yeni Poliçe",
"🔎 Poliçe Takibi",
"💳 Ödeme & Cari",
"📊 Analiz"
]

if st.session_state.role=="Admin":
    menu_options.append("🔐 Yönetici Paneli")

choice = st.sidebar.radio("İŞLEM MERKEZİ",menu_options)

# YENİ POLİÇE
if choice=="📝 Yeni Poliçe":

    st.subheader("📝 Yeni Poliçe Kaydı")

    with st.form("police_form"):

        c1,c2 = st.columns(2)

        with c1:

            p_no = st.text_input("Poliçe No")
            m_adi = st.text_input("Müşteri Adı")
            sirket = st.text_input("Sigorta Şirketi")

            brans = st.selectbox(
                "Poliçe Türü",
                ["TRAFİK","KASKO","SAĞLIK"]
            )

            plaka = st.text_input("Plaka / TC")
            tel = st.text_input("Telefon")

        with c2:

            tanzim = st.date_input("Tanzim Tarihi")
            basla = st.date_input("Başlangıç Tarihi")

            is_two_months = st.checkbox("2 Aylık Poliçe")

            t_tutar = st.number_input("Toplam Tutar",0)
            a_ucret = st.number_input("Alınan Ücret",0)

        submit = st.form_submit_button("✅ SİSTEME KAYDET")

        if submit:

            bitis = basla + relativedelta(months=2) if is_two_months else basla + relativedelta(years=1)

            new_row = pd.DataFrame([{

                "police_no":p_no,
                "musteri_adi":m_adi.upper(),
                "sigorta_sirketi":sirket,
                "police_turu":brans,
                "plaka_tc":plaka.upper(),
                "telefon":tel,
                "tanzim_tarihi":str(tanzim),
                "baslangic_tarihi":str(basla),
                "bitis_tarihi":str(bitis),
                "toplam_tutar":t_tutar,
                "alinan_ucret":a_ucret,
                "arsiv":"FALSE",
                "kayit_yapan":st.session_state.username

            }])

            conn.update(
                worksheet="Sayfa1",
                data=pd.concat([df,new_row],ignore_index=True)
            )

            st.success(f"Kayıt eklendi. Vade: {bitis}")
            st.rerun()

# POLİÇE TAKİBİ
elif choice=="🔎 Poliçe Takibi":

    st.subheader("🔎 Aktif Poliçeler")

    if not df.empty:

        active_df = df[df["arsiv"]=="FALSE"]

        if not active_df.empty:

            for i,row in active_df.iterrows():

                with st.container(border=True):

                    c1,c2 = st.columns([0.8,0.2])

                    c1.markdown(
                        f"👤 **{row['musteri_adi']}** | 🚗 {row['plaka_tc']} | 📅 Vade: **{row['bitis_tarihi']}**"
                    )

                    c1.caption(
                        f"🏢 {row['sigorta_sirketi']} | 📑 {row['police_turu']}"
                    )

                    tel = str(row["telefon"])

                    if tel.startswith("0"):
                        tel = tel[1:]

                    wa = f"https://wa.me/90{tel}?text=Merhaba%20{row['musteri_adi']},%20poliçenizin%20vadesi%20{row['bitis_tarihi']}%20tarihinde%20dolacaktır."

                    c2.link_button("💬 WhatsApp",wa,use_container_width=True)

        else:
            st.info("Aktif poliçe bulunamadı")

# CARİ TAKİP
elif choice=="💳 Ödeme & Cari":

    st.subheader("💳 Cari Takip")

    if not df.empty:

        df["toplam_tutar"]=pd.to_numeric(df["toplam_tutar"],errors="coerce").fillna(0)
        df["alinan_ucret"]=pd.to_numeric(df["alinan_ucret"],errors="coerce").fillna(0)

        kalan = df["toplam_tutar"].sum()-df["alinan_ucret"].sum()

        st.metric("Bekleyen Tahsilat",f"{kalan:,.2f} TL")

        st.table(
            df[df["toplam_tutar"]>df["alinan_ucret"]][
                ["musteri_adi","police_no","toplam_tutar","alinan_ucret"]
            ]
        )

# ANALİZ
elif choice=="📊 Analiz":

    st.subheader("📊 Portföy Analizi")

    if not df.empty:

        df["toplam_tutar"]=pd.to_numeric(df["toplam_tutar"],errors="coerce").fillna(0)

        c1,c2 = st.columns(2)

        fig1 = px.pie(df,names="sigorta_sirketi",title="Şirket Dağılımı")
        fig2 = px.bar(df,x="police_turu",y="toplam_tutar",title="Branş Ciro")

        c1.plotly_chart(fig1,use_container_width=True)
        c2.plotly_chart(fig2,use_container_width=True)

# YÖNETİCİ PANELİ
elif choice=="🔐 Yönetici Paneli":

    st.subheader("🔐 Yönetici Paneli")

    st.dataframe(df)

# ÇIKIŞ
if st.sidebar.button("🔴 Çıkış"):

    st.session_state.clear()
    st.rerun()
