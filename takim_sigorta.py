# --- 1. SEKME LOGOSU DÜZELTMESİ ---
# Bu ayar sayesinde tarayıcı sekmesinde kalkan yerine senin logon görünecek
logo_path = get_logo() # Daha önce tanımladığımız logo bulucu fonksiyon
st.set_page_config(
    page_title="Takim Sigorta | Yönetim", 
    layout="wide", 
    page_icon=logo_path if logo_path else "🛡️" 
)

# --- 2. ÖDEME VE CARİ TAKİP EKRANI (YENİ BÖLÜM) ---
# Menüye "Ödeme Takibi"ni ekliyoruz
menu_options = {
    "📝 Yeni Poliçe": "yeni",
    "🔎 Poliçe Takibi": "takip",
    "💳 Ödeme & Cari": "odeme", # Yeni eklenen alan
    "📊 Analiz": "analiz",
    "🔐 Yönetici Paneli": "admin"
}

# --- ÖDEME EKRANI İÇERİĞİ ---
if choice == "odeme":
    st.subheader("💳 Ödeme ve Cari Takip Merkezi")
    
    # Sadece ödemesi tamamlanmamış veya borcu olanları listeleyebiliriz
    if not df.empty:
        # Toplam borç ve tahsilat özeti
        t_borc = pd.to_numeric(df['toplam_tutar'], errors='coerce').sum()
        t_alinan = pd.to_numeric(df['alinan_ucret'], errors='coerce').sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Ciro", f"{t_borc:,.2f} TL")
        c2.metric("Tahsil Edilen", f"{t_alinan:,.2f} TL")
        c3.metric("Bekleyen Tahsilat", f"{(t_borc - t_alinan):,.2f} TL", delta_color="inverse")
        
        st.divider()
        
        # Ödeme detayları tablosu
        st.write("### 📜 Güncel Borç/Alacak Listesi")
        st.dataframe(df[['müşteri_adı', 'police_no', 'toplam_tutar', 'alinan_ucret', 'odeme_tipi']], use_container_width=True)
    else:
        st.info("Henüz ödeme kaydı bulunmuyor.")
