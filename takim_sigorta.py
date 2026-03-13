import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- 1. AYARLAR VE GÖRSEL TEMA ---
st.set_page_config(page_title="Takim Sigorta | İşlem Merkezi", layout="wide", page_icon="🛡️")

# --- 2. LOGO VE GÖRSEL YÜKLEME FONKSİYONU ---
def get_logo(location="main"):
    # Klasördeki logoyu arar (png, jpg, jpeg)
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"):
            if location == "main":
                # Giriş ekranı için büyük logo
                return f"logo.{ext}"
            else:
                # Yan menü için daha küçük logo
                return f"logo.{ext}"
    return None

# --- 3. VERİ BAĞLANTISI VE ZIRHLI YÜKLEME ---
# Google Sheets bağlantısını kurar
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe():
    """Veriyi yükler ve sütun isimlerini normalize ederek hatayı önler."""
    try:
        # Google Sheets'ten veriyi oku (Sayfa1 isimli çalışma sayfasını)
        df = conn.read(worksheet="Sayfa1", ttl=0)
        
        # Eğer tablo boşsa, boş bir DataFrame döndür
        if df is None or df.empty:
            df = pd.DataFrame()
        
        # Sütun isimlerini küçük harfe zorla (Hata önleyici zırh)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # --- KRİTİK ZIRH: Eğer bu sütunlar yoksa, hata verme, boş olarak yarat ---
        # Bu sütunlar tabloda olmasa bile kod hata vermez, kendi oluşturur.
        required_columns = ['police_no', 'müşteri adı', 'sigorta şirketi', 'poliçe türü', 
                           'plaka/tc', 'telefon', 'tanzim tarihi', 'başlangıç tarihi', 
                           'bitiş tarihi', 'referans', 'kayıt yapan', 'arsiv']
        
        for col in required_columns:
            if col not in df.columns:
                # Arşiv sütununu FALSE, diğerlerini boş yap
                df[col] = "FALSE" if col == 'arsiv' else ""
        
        return df
    except Exception as e:
        # Hata durumunda boş DataFrame döndür, beyaz ekranı önle
        st.error(f"Veri yüklenirken hata oluştu (Lütfen Google Sheets başlıklarını kontrol edin): {e}")
        return pd.DataFrame()

# --- 4. KULLANICI VE YETKİ YÖNETİMİ ---
# Kullanıcı veritabanı (session_state içinde saklanır, kalıcı olması için veritabanına bağlanmalı)
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "sercan": {"pw": "takim2026", "role": "admin"},
        "admin": {"pw": "admin44", "role": "admin"},
        "personel": {"pw": "takim2024", "role": "user"}
    }

# Giriş kontrolü
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # Giriş Ekranı (Modern ve Logolu)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        # Ana logoyu yerleştir
        logo_path = get_logo(location="main")
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            # Logo yoksa ikon göster
            st.markdown("<h1 style='text-align: center;'>🛡️</h1>", unsafe_allow_html=True)
            
        st.markdown("<h2 style='text-align: center;'>Takim Sigorta Giriş</h2>", unsafe_allow_html=True)
        
        u = st.text_input("Kullanıcı Adı").lower()
        p = st.text_input("Şifre", type="password")
        
        if st.button("SİSTEME GİRİŞ", use_container_width=True):
            if u in st.session_state.users_db and st.session_state.users_db[u]["pw"] == p:
                # Giriş başarılı
                st.session_state.authenticated = True
                st.session_state.username = u
                st.session_state.role = st.session_state.users_db[u]["role"]
                st.rerun()
            else:
                st.error("Giriş bilgileri hatalı! Lütfen kontrol edin.")
    # Giriş yapmadıysa programın geri kalanını çalıştırma
    st.stop()

# --- 5. ANA PROGRAM VE YAN MENÜ ---
# Veriyi güvenli şekilde yükle
df = load_data_safe()

# Sidebar (Yan Menü) Düzeni
logo_side = get_logo(location="side")
if logo_side:
    st.sidebar.image(logo_side, use_container_width=True)

st.sidebar.markdown(f"**Hoş geldin:** {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Yetki:** {st.session_state.role.upper()}")

# İşlem Merkezi (Ana Menü)
menu_options = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "📊 Analiz & Rapor": "analiz"
}

# Sadece admin ise Yönetici Paneli'ni göster
if st.session_state.role == "admin":
    menu_options["🔐 Yönetici Paneli"] = "admin"

choice = menu_options[st.sidebar.radio("İŞLEM MERKEZİ", list(menu_options.keys()))]

# Güvenli Çıkış Butonu
if st.sidebar.button("🔴 Güvenli Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

# --- 6. SAYFA İÇERİKLERİ ---

# --- 6.1 YENİ POLİÇE KAYIT ---
if choice == "yeni":
    st.subheader("📝 Yeni Poliçe Kayıt Formu")
    st.info("Lütfen tüm alanları eksiksiz doldurun. Kayıt yapan kişi otomatik olarak mühürlenecektir.")
    
    with st.form("yeni_police_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        p_no = col1.text_input("🔢 Poliçe Numarası", placeholder="Poliçe no giriniz...")
        m_adi = col2.text_input("👤 Müşteri Ad Soyad", placeholder="İsim soyisim giriniz...")
        
        col3, col4, col5 = st.columns(3)
        s_sirketi = col3.selectbox("🏢 Sigorta Şirketi", ["Allianz", "Axa", "Anadolu", "Türkiye", "Sompo", "Mapfre", "HDI", "Diğer"])
        p_turu = col4.selectbox("📑 Branş", ["TRAFİK", "KASKO", "DASK", "TSS", "KONUT", "İŞYERİ", "DİĞER"])
        plaka = col5.text_input("🚗 Plaka / TC No", placeholder="Örn: 34ABC123")
        
        col6, col7 = st.columns(2)
        tel = col6.text_input("💬 Telefon (WhatsApp)", placeholder="Örn: 5321234567")
        ref = col7.text_input("🔗 Referans / Aracı", placeholder="Örn: Galerici Ahmet")
        
        col8, col9 = st.columns(2)
        tanzim = col8.date_input("📅 Tanzim Tarihi", datetime.now())
        basla = col9.date_input("📅 Başlangıç Tarihi", datetime.now())
        
        # Bitiş tarihini otomatik hesapla (1 yıl sonrası)
        bitis_auto = basla + relativedelta(years=1)
        st.warning(f"💡 Otomatik Hesaplanan Vade Sonu: **{bitis_auto.strftime('%d.%m.%Y')}**")
        
        notlar = st.text_area("🗒️ Poliçe Notu")
        
        if st.form_submit_button("✅ POLİÇEYİ SİSTEME KAYDET", use_container_width=True):
            # Zorunlu alan kontrolü
            if p_no and m_adi and tel and s_sirketi and p_turu:
                # Yeni veriyi DataFrame formatına sok
                new_row = pd.DataFrame([{
                    "police_no": str(p_no),
                    "müşteri_adı": m_adi.upper(), # İsmi otomatik büyük harf yap
                    "sigorta_sirketi": s_sirketi,
                    "poliçe_türü": p_turu,
                    "plaka_tc": plaka.upper(),
                    "telefon": tel,
                    "tanzim_tarihi": tanzim.strftime("%d.%m.%Y"),
                    "başlangıç_tarihi": basla.strftime("%d.%m.%Y"),
                    "bitiş_tarihi": bitis_auto.strftime("%d.%m.%Y"), # Otomatik tarihi kullan
                    "referans": ref,
                    "kayıt_yapan": st.session_state.username, # Giriş yapanı mühürle
                    "notlar": notlar,
                    "arsiv": "FALSE" # Her yeni kayıt aktiftir
                }])
                
                # Mevcut veriye ekle ve Google Sheets'i güncelle
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sayfa1", data=updated_df)
                
                st.success(f"Poliçe {st.session_state.username.upper()} tarafından başarıyla Google Sheets'e eklendi!")
                st.balloons()
                st.rerun() # Sayfayı yenile ki yeni kayıt tabloda görünsün
            else:
                st.error("Lütfen Poliçe No, Müşteri, Şirket, Branş ve Telefon alanlarını boş bırakmayın!")

# --- 6.2 POLİÇE TAKİBİ VE OPERASYON ---
elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi ve Operasyon Merkezi")
    
    if not df.empty and 'arsiv' in df.columns:
        # Sadece aktif (arşivlenmemiş) poliçeleri filtrele (Zırhlı Filtreleme)
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"].copy()
        
        if not active_df.empty:
            # Tarihleri datetime formatına çevir (Vade takibi için)
            active_df['bitiş_datetime'] = pd.to_datetime(active_df['bitiş_tarihi'], format='%d.%m.%Y', errors='coerce')
            bugun = pd.Timestamp(datetime.now().date())
            
            # Vadeye göre sırala (Vadesi geçmişler en üstte)
            active_df = active_df.sort_values(by='bitiş_datetime')
            
            # Kayıtları listele
            for i, row in active_df.iterrows():
                # Trafik Lambası Mantığı (Vade Takibi)
                kalan_gun = (row['bitiş_datetime'] - bugun).days if pd.notnull(row['bitiş_datetime']) else 999
                
                if kalan_gun < 0:
                    icon, lamba_html = "🔴", "<span style='color:red; font-weight:bold;'>VADESİ GEÇMİŞ</span>"
                elif kalan_gun <= 15:
                    icon, lamba_html = "🟡", "<span style='color:orange; font-weight:bold;'>VADE YAKLAŞTI</span>"
                else:
                    icon, lamba_html = "🟢", "<span style='color:green; font-weight:bold;'>GÜNCEL</span>"
                
                # Her poliçeyi bir kutu içinde göster
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([0.45, 0.2, 0.15, 0.2])
                    
                    c1.markdown(f"{icon} **{row['müşteri_adı']}** | {row['police_no']} | {lamba_html}")
                    c1.caption(f"🏢 {row['sigorta_sirketi']} | 📑 {row['poliçe_türü']} | 🚗 {row['plaka_tc']} | 📅 Vade: {row['bitiş_tarihi']}")
                    c1.caption(f"🔗 Ref: {row['referans']} | 👤 Kayıt Yapan: {row['kayıt_yapan']}")
                    
                    # WhatsApp Butonu
                    # Telefon numarasını WhatsApp formatına uygun hale getir (Başında 0 olmadan)
                    clean_tel = str(row['telefon']).strip().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
                    if clean_tel.startswith("0"): clean_tel = clean_tel[1:]
                    
                    # WhatsApp mesaj taslağı
                    wa_msg = f"Merhaba%20{row['müşteri_adı']}.%20Takim%20Sigorta'dan%20ulaşıyoruz.%20{row['police_no']}%20nolu%20{row['poliçe_türü']}%20poliçenizin%20vadesi%20{row['bitiş_tarihi']}%20tarihinde%20dolacaktır.%20Yenileme%20işlemleri%20için%20bize%20ulaşabilirsiniz."
                    wa_link = f"https://wa.me/90{clean_tel}?text={wa_msg}"
                    
                    c2.link_button("💬 WhatsApp İletişim", wa_link, use_container_width=True)
                    
                    # Arşivle Butonu
                    if c4.button("📁 Arşivle", key=f"arc_{i}_{row['police_no']}", use_container_width=True):
                        # Google Sheets'teki orijinal DataFrame'de ilgili satırı TRUE yap
                        df.at[i, 'arsiv'] = "TRUE"
                        conn.update(worksheet="Sayfa1", data=df)
                        st.success(f"{row['müşteri_adı']} adına kayıtlı poliçe arşive kaldırıldı!")
                        st.balloons()
                        st.rerun()
        else:
            st.info("Gösterilecek aktif poliçe kaydı bulunmuyor.")
    else:
        st.warning("Veri tabanı henüz oluşturulmamış veya boş. Lütfen Yeni Poliçe kaydı yapın.")

# --- 6.3 ANALİZ VE RAPOR ---
elif choice == "analiz":
    st.subheader("📊 Analiz ve Finansal Raporlar")
    
    if not df.empty:
        # Tüm kayıtlar üzerinden analiz (Arşivler dahil olabilir)
        m1, m2 = st.columns(2)
        m1.metric("Toplam Kayıtlı Poliçe", f"{len(df)} Adet")
        
        # Sadece aktif olanları analiz et
        active_df = df[df['arsiv'].astype(str).str.upper() == "FALSE"].copy()
        m2.metric("Aktif Poliçe Sayısı", f"{len(active_df)} Adet")
        
        st.divider()
        c1, c2 = st.columns(2)
        
        # Branş Dağılımı Grafiği
        if 'poliçe_türü' in df.columns:
            fig_brans = px.pie(df, names='poliçe_türü', title="Branş Dağılımı (Toplam)", hole=0.3)
            c1.plotly_chart(fig_brans, use_container_width=True)
            
        # Şirket Dağılımı Grafiği
        if 'sigorta_sirketi' in df.columns:
            fig_sirket = px.bar(df, x='sigorta_sirketi', title="Sigorta Şirketi Performansı", color='sigorta_sirketi')
            c2.plotly_chart(fig_sirket, use_container_width=True)
            
        # Personel Performansı Grafiği
        if 'kayıt_yapan' in df.columns:
            st.write("### 👤 Personel İşlem Dağılımı")
            fig_personel = px.histogram(df, x='kayıt_yapan', color='kayıt_yapan', title="Kimin Kaç Poliçe Girdi?")
            st.plotly_chart(fig_personel, use_container_width=True)
    else:
        st.info("Analiz yapılacak veri henüz birikmedi.")

# --- 6.4 YÖNETİCİ PANELİ (ADMİN ÖZEL) ---
elif choice == "admin":
    st.subheader("🔐 Yönetici Paneli")
    
    # Sadece admin yetkisi olanlar görebilir (Sidebar'da kontrol edildi ama burası da ek güvenlik)
    if st.session_state.role != "admin":
        st.error("Bu panele giriş yetkiniz bulunmamaktadır.")
        st.stop()
        
    st.write("### 👤 Kullanıcı Yönetimi")
    # Mevcut kullanıcıları listele
    for user_name, user_info in st.session_state.users_db.items():
        with st.container(border=True):
            col_u, col_r, col_act = st.columns([2, 2, 1])
            col_u.write(f"👤 **{user_name.upper()}**")
            # Yetki değiştirme menüsü
            new_role = col_r.selectbox(f"Yetki ({user_name})", ["admin", "user"], index=0 if user_info['role'] == "admin" else 1, key=f"role_{user_name}")
            if col_act.button("Güncelle", key=f"up_{user_name}"):
                # Yetkiyi güncelle
                st.session_state.users_db[user_name]['role'] = new_role
                st.success(f"{user_name} yetkisi güncellendi.")
    
    st.divider()
    # Yeni Kullanıcı Ekleme
    with st.expander("➕ Yeni Kullanıcı Tanımla"):
        with st.form("yeni_kullanici_form", clear_on_submit=True):
            nu_name = st.text_input("Kullanıcı Adı")
            nu_pw = st.text_input("Şifre", type="password")
            nu_role = st.selectbox("Yetki Seviyesi", ["user", "admin"])
            
            if st.form_submit_button("Sisteme Ekle"):
                if nu_name and nu_pw:
                    # Kullanıcıyı session_state veritabanına ekle
                    # Kalıcı olması için Google Sheets'e veya veritabanına yazılmalı
                    st.session_state.users_db[nu_name.lower()] = {"pw": nu_pw, "role": nu_role}
                    st.success(f"Yeni kullanıcı {nu_name.upper()} başarıyla oluşturuldu!")
                    st.rerun()
                else:
                    st.error("Lütfen tüm alanları doldurun!")
