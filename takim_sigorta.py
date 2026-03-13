elif choice == "takip":
    st.subheader("🔎 Poliçe Takibi")
    
    if not df.empty:
        # --- YENİ FİLTRELEME SEÇENEĞİ ---
        filtre_turu = st.radio(
            "Görünüm Seçiniz:",
            ["Tümü", "Vadesi Yaklaşanlar (15 Gün)"],
            horizontal=True
        )

        # Düzenleme ve Silme Paneli (Açılır Menü)
        with st.expander("🛠️ Kayıt Düzenle veya Sil", expanded=False):
            secilen_no = st.selectbox("İşlem yapılacak Poliçe", ["Seçiniz..."] + sorted(df['police_no'].astype(str).unique().tolist()))
            if secilen_no != "Seçiniz...":
                idx = df[df['police_no'].astype(str) == secilen_no].index[0]
                row = df.loc[idx]
                with st.form("duzenleme_formu"):
                    u_musteri = st.text_input("Müşteri", value=str(row['musteri_adi']))
                    current_sirket_index = SIRKET_LISTESI.index(row['sigorta_sirketi']) if 'sigorta_sirketi' in row and row['sigorta_sirketi'] in SIRKET_LISTESI else 0
                    u_sirket = st.selectbox("Şirket", SIRKET_LISTESI, index=current_sirket_index)
                    u_prim = st.number_input("Prim", value=float(row['brut_prim']))
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 GÜNCELLE"):
                        df.at[idx, 'musteri_adi'] = u_musteri
                        df.at[idx, 'sigorta_sirketi'] = u_sirket
                        df.at[idx, 'brut_prim'] = u_prim
                        conn.update(worksheet=WORKSHEET_NAME, data=df)
                        st.success("Güncellendi!")
                        st.rerun()
                    if c2.form_submit_button("🗑️ SİL"):
                        new_df = df.drop(idx)
                        conn.update(worksheet=WORKSHEET_NAME, data=new_df)
                        st.success("Silindi!")
                        st.rerun()

        # --- VERİ SÜZME MANTIĞI ---
        search = st.text_input("🔍 Hızlı Ara (İsim/No/Şirket)")
        
        # Önce arama filtresini uygula
        display_df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
        
        # Sonra Vade filtresini uygula (Eğer seçiliyse)
        if filtre_turu == "Vadesi Yaklaşanlar (15 Gün)":
            bugun = pd.Timestamp(datetime.now().date())
            # Bitiş tarihi boş olmayanları al ve 15 gün kalanları filtrele
            display_df = display_df.dropna(subset=['bitis_tarihi'])
            display_df = display_df[
                (display_df['bitis_tarihi'] >= bugun) & 
                ((display_df['bitis_tarihi'] - bugun).dt.days <= 15)
            ]

        # TABLO GÖRÜNÜMÜ
        st.dataframe(
            display_df.sort_values('tanzim_tarihi', ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "tanzim_tarihi": st.column_config.DateColumn("Tanzim", format="DD.MM.YYYY"),
                "baslangic_tarihi": st.column_config.DateColumn("Başlangıç", format="DD.MM.YYYY"),
                "bitis_tarihi": st.column_config.DateColumn("Vade Sonu", format="DD.MM.YYYY"),
                "brut_prim": st.column_config.NumberColumn("Prim", format="%.2f TL")
            }
        )
        
        if display_df.empty:
            st.warning("Seçilen kriterlere uygun poliçe bulunamadı.")
