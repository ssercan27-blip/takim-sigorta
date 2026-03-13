elif choice == "cari":
    st.subheader("👤 Müşteri Detayları ve İşlem Geçmişi")
    
    if not df.empty:
        # AYNI İSİM KARIŞIKLIĞINI ÖNLEME:
        # Müşterileri "İsim (Telefon)" şeklinde birleştirerek benzersiz bir liste yapıyoruz.
        df['benzersiz_musteri'] = df['musteri_adi'] + " - " + df['telefon'].astype(str)
        
        musteri_listesi = sorted(df['benzersiz_musteri'].unique())
        secilen_benzersiz = st.selectbox("İncelemek istediğiniz müşteriyi seçin", ["Seçiniz..."] + musteri_listesi)
        
        if secilen_benzersiz != "Seçiniz...":
            # Seçilen benzersiz kimliğe göre veriyi süzüyoruz
            musteri_df = df[df['benzersiz_musteri'] == secilen_benzersiz]
            
            # Ekranın üstünde müşteri özeti
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Toplam Poliçe", f"{len(musteri_df)} Adet")
            with c2:
                st.metric("Toplam Brüt Prim", f"{musteri_df['brut_prim'].sum():,.2f} TL")
            with c3:
                st.metric("Toplam Net Kazanç", f"{musteri_df['net_komisyon'].sum():,.2f} TL")
            
            st.divider()
            st.write(f"### 📑 {secilen_benzersiz} - Poliçe Dökümü")
            
            # Tabloyu daha okunaklı gösterelim
            st.dataframe(
                musteri_df[['police_turu', 'kaynak', 'brut_prim', 'net_komisyon', 'tanzim_tarihi', 'bitis_tarihi']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Henüz kayıtlı müşteri bulunmuyor.")

# --- VADE TAKİP HATALARI İÇİN DÜZELTME ---
elif choice == "vade":
    st.subheader("🔔 Vade Takip Merkezi")
    
    if not df.empty:
        # Tarih formatlarını ve telefonları sağlama alıyoruz
        df['bitis_tarihi'] = pd.to_datetime(df['bitis_tarihi'], errors='coerce')
        bugun = pd.Timestamp(datetime.now().date())
        
        # Kalan gün hesabı
        df['kalan_gun'] = (df['bitis_tarihi'] - bugun).dt.days
        
        # Sadece vadesi 30 gün içinde olanları ve yeni geçmiş (5 gün) olanları getir
        vade_listesi = df[(df['kalan_gun'] <= 30) & (df['kalan_gun'] >= -5)].sort_values('kalan_gun')
        
        if not vade_listesi.empty:
            for _, row in vade_listesi.iterrows():
                # Kalan güne göre renk kodu
                gun = row['kalan_gun']
                durum_rengi = "🔴" if gun < 0 else "🟠" if gun < 7 else "🟢"
                
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### {durum_rengi} {row['musteri_adi']}")
                        st.write(f"**Branş:** {row['police_turu']} | **Vade Tarihi:** {row['bitis_tarihi'].strftime('%d.%m.%Y')}")
                        st.write(f"**Kalan Süre:** {gun} Gün")
                    
                    with c2:
                        # WhatsApp linkini hazırlama
                        tel = str(row['telefon']).strip()
                        if not tel.startswith('90') and len(tel) > 0:
                            tel = "90" + (tel[1:] if tel.startswith('0') else tel)
                        
                        msg = f"Sayın {row['musteri_adi']}, Takim Sigorta'dan hatırlatırız: {row['police_turu']} poliçenizin vadesi dolmaktadır."
                        wa_url = f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}"
                        
                        st.link_button("💬 Hatırlat", wa_url, use_container_width=True)
        else:
            st.success("Takip edilmesi gereken acil bir vade bulunmuyor.")
