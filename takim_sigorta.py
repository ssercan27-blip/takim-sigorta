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
        if raw_df is None or raw_df.empty:
            # Boşsa iskelet oluştur
            return pd.DataFrame(columns=['police_no', 'musteri_adi', 'sigorta_sirketi', 'police_turu', 'brut_prim', 'net_komisyon', 'bitis_tarihi', 'arsiv'])
        
        # SÜTUN TEMİZLİĞİ VE SABİTLEME (Hataları önleyen kritik kısım)
        raw_df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_df.columns]
        
        # Eğer beklenen sütunlar yoksa hata vermemesi için boş ekle
        expected = ['police_no', 'musteri_adi', 'sigorta_sirketi', 'police_turu', 'brut_prim', 'net_komisyon', 'bitis_tarihi', 'arsiv']
        for col in expected:
            if col not in raw_df.columns:
                raw_df[col] = False if col == 'arsiv' else (0 if col in ['brut_prim', 'net_komisyon'] else "")
        
        # Veri Tiplerini Zorla
        raw_df['brut_prim'] = pd.to_numeric(raw_df['brut_prim'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        raw_df['net_komisyon'] = pd.to_numeric(raw_df['net_komisyon'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        raw_df['bitis_tarihi'] = pd.to_datetime(raw_df['bitis_tarihi'], errors='coerce')
        raw_df['arsiv'] = raw_df['arsiv'].apply(lambda x: True if str(x).lower() == 'true' else False)
        
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
        p_no = st.text_input("Poliçe No")
        m_adi = st.text_input("Müşteri Ad Soyad")
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
    st.subheader("🔎 Poliçe Takibi")
    if not df.empty:
        bugun = pd.Timestamp(datetime.now().date())
        # Sadece arşivlenmemişleri filtrele
        active = df[df['arsiv'] == False].copy()
        
        if active.empty:
            st.info("Gösterilecek aktif poliçe bulunmuyor.")
        else:
            for i, r in active.iterrows():
                # Vade hesaplama ve lamba rengi
                kalan = (r['bitis_tarihi'] - bugun).days if pd.notnull(r['bitis_tarihi']) else 999
                if kalan < 0: icon, label = "🔴", "Vadesi Geçmiş"
                elif kalan <= 15: icon, label = "🟡", "Vade Yaklaştı"
                else: icon, label = "🟢", "Güncel"
                
                with st.container(border=True):
                    col_text, col_act = st.columns([0.8, 0.2])
                    with col_text:
                        st.write(f"{icon} **{r['musteri_adi']}** | {r['police_no']} | {label}")
                        st.caption(f"Şirket: {r['sigorta_sirketi']} | Vade: {r['bitis_tarihi'].strftime('%d.%m.%Y') if pd.notnull(r['bitis_tarihi']) else 'Belirsiz'}")
                    with col_act:
                        if st.button("📁 Arşivle", key=f"ars_{i}"):
                            df.at[i, 'arsiv'] = True
                            conn.update(worksheet="Sayfa1", data=df)
                            st.rerun()

elif choice == "rapor":
    st.subheader("📊 Analiz")
    # Sayısal veri olanları süz
    rdf = df[df['brut_prim'] > 0].copy()
    if not rdf.empty:
        st.metric("Toplam Üretim", f"{rdf['brut_prim'].sum():,.2f} TL")
        st.plotly_chart(px.pie(rdf, values='net_komisyon', names='police_turu', title="Kazanç Dağılımı"), use_container_width=True)
    else:
        st.warning("Henüz analiz edilecek veri yok.")

elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    # Kullanıcı Listesi ve Yetki Değiştirme
    st.write("### Kullanıcı Yönetimi")
    for u_name, u_info in st.session_state.users_db.items():
        c_u, c_r, c_b = st.columns([2, 2, 1])
        c_u.write(f"👤 **{u_name}**")
        new_r = c_r.selectbox(f"Yetki ({u_name})", ["admin", "user"], index=0 if u_info['role'] == "admin" else 1, key=f"adm_{u_name}")
        if c_b.button("Güncelle", key=f"up_btn_{u_name}"):
            st.session_state.users_db[u_name]['role'] = new_r
            st.success("Güncellendi!")
    
    st.divider()
    with st.expander("➕ Yeni Kullanıcı Ekle"):
        nu = st.text_input("Yeni İsim")
        np = st.text_input("Yeni Şifre")
        if st.button("Ekle"):
            st.session_state.users_db[nu] = {"pw": np, "role": "user"}
            st.rerun()
