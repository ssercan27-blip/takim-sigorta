import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Takim Sigorta | Yönetim Paneli", layout="wide")

# --- KULLANICI YÖNETİMİ ---
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "sercan": {"pw": "takim2026", "role": "admin"},
        "admin": {"pw": "admin44", "role": "admin"}
    }

# --- AYARLAR ---
KOMISYON_SOZLUGU = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

# --- LOGO VE VERİ YÜKLEME ---
def show_logo(loc="main"):
    path = "logo.jpg" if os.path.exists("logo.jpg") else ("logo.png" if os.path.exists("logo.png") else None)
    if path:
        if loc == "main": st.image(path, width=200)
        else: st.sidebar.image(path, use_container_width=True)
    else:
        st.sidebar.title("🛡️ TAKİM SİGORTA")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        raw_df = conn.read(worksheet="Sayfa1", ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame()
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        
        # Sütunları Garanti Altına Al
        for col in ['brut_prim', 'net_komisyon']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        
        if 'bitis_tarihi' in raw_df.columns:
            raw_df['bitis_tarihi'] = pd.to_datetime(raw_df['bitis_tarihi'], errors='coerce')
        
        if 'arsiv' not in raw_df.columns: raw_df['arsiv'] = False
        return raw_df
    except:
        return pd.DataFrame()

# 1. GİRİŞ KONTROLÜ
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        show_logo("main")
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ", use_container_width=True):
            if u in st.session_state.users_db and st.session_state.users_db[u]["pw"] == p:
                st.session_state.authenticated, st.session_state.username = True, u
                st.session_state.role = st.session_state.users_db[u]["role"]
                st.rerun()
            else: st.error("Bilgiler hatalı!")
    st.stop()

df = load_data()

# --- SIDEBAR ---
show_logo("sidebar")
st.sidebar.write(f"Hoş geldin, **{st.session_state.username.upper()}**")
opt = {"📝 Yeni Poliçe": "kaydet", "🔎 Poliçe Takibi": "takip", "📊 Analiz": "rapor", "🔔 Vade Takip": "vade"}
if st.session_state.role == "admin": opt["🔐 Yönetici Paneli"] = "admin"
choice = opt[st.sidebar.radio("Menü", list(opt.keys()))]

# --- SAYFALAR ---

if choice == "kaydet":
    st.subheader("📝 Yeni Poliçe Girişi")
    with st.form("p_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_no = c1.text_input("Poliçe No")
        m_adi = c2.text_input("Müşteri Ad Soyad")
        sirket = st.selectbox("Sigorta Şirketi", ["Aksigorta", "Allianz", "Anadolu", "Axa", "Türkiye", "Diğer"])
        brans = st.selectbox("Branş", list(KOMISYON_SOZLUGU.keys()))
        prim = st.number_input("Brüt Prim (TL)", min_value=0.0)
        tanzim = st.date_input("Tanzim Tarihi", datetime.now())
        if st.form_submit_button("✅ SİSTEME KAYDET"):
            kazanc = prim * (KOMISYON_SOZLUGU[brans] / 100)
            bitis = tanzim + relativedelta(years=1)
            new = pd.DataFrame([{"police_no": p_no, "musteri_adi": m_adi, "sigorta_sirketi": sirket, "police_turu": brans, "brut_prim": prim, "net_komisyon": kazanc, "bitis_tarihi": bitis, "arsiv": False}])
            conn.update(worksheet="Sayfa1", data=pd.concat([df, new], ignore_index=True))
            st.success("Kayıt Başarılı!"); st.rerun()

elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi (Renkli Durum)")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        active = df[df['arsiv'] == False].copy()
        
        for i, r in active.iterrows():
            kalan = (r['bitis_tarihi'] - bugun).days if pd.notnull(r['bitis_tarihi']) else 999
            # Renk ve Durum Belirleme
            if kalan < 0: color, label = "🔴", "Vadesi Geçmiş"
            elif kalan <= 15: color, label = "🟡", "Vade Yaklaştı"
            else: color, label = "🟢", "Güncel"
            
            with st.container(border=True):
                col_i, col_b = st.columns([0.8, 0.2])
                col_i.write(f"{color} **{r['musteri_adi']}** | {r['police_no']} | {label}")
                col_i.caption(f"Şirket: {r['sigorta_sirketi']} | Vade: {r['bitis_tarihi'].strftime('%d.%m.%Y')}")
                if col_b.button("📁 Arşivle", key=f"ar_{i}"):
                    df.at[i, 'arsiv'] = True
                    conn.update(worksheet="Sayfa1", data=df)
                    st.success("Arşivlendi!"); st.rerun()

elif choice == "rapor":
    st.subheader("📊 Finansal Analiz")
    rdf = df[df['brut_prim'] > 0].copy()
    if not rdf.empty:
        c1, c2 = st.columns(2)
        c1.metric("Toplam Üretim", f"{rdf['brut_prim'].sum():,.2f} TL")
        c2.metric("Toplam Kazanç", f"{rdf['net_komisyon'].sum():,.2f} TL")
        st.plotly_chart(px.pie(rdf, values='net_komisyon', names='police_turu', title="Branş Dağılımı"), use_container_width=True)
    else:
        st.warning("Henüz prim girişi yapılmadığı için analiz oluşturulamıyor.")

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    # Mevcut Kullanıcıları Listeleme ve Düzenleme
    st.write("### Mevcut Kullanıcılar")
    for u_name, u_info in st.session_state.users_db.items():
        col_u, col_r, col_btn = st.columns([2, 2, 1])
        col_u.write(f"👤 **{u_name}**")
        new_role = col_r.selectbox(f"Yetki Değiştir ({u_name})", ["admin", "user"], index=0 if u_info['role'] == "admin" else 1, key=f"role_{u_name}")
        if col_btn.button("Güncelle", key=f"upd_{u_name}"):
            st.session_state.users_db[u_name]['role'] = new_role
            st.success("Yetki güncellendi!")

    st.divider()
    with st.expander("➕ Yeni Kullanıcı Ekle"):
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Yeni Şifre")
        if st.button("Kaydet"):
            st.session_state.users_db[nu] = {"pw": np, "role": "user"}
            st.success("Kullanıcı eklendi.")
