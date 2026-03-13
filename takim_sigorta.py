import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- BRANŞ VE KOMİSYON AYARLARI ---
KOMISYON_ORANLARI = {
    "Trafik": 6.50, "Kasko": 9.50, "Konut": 20.00, "İşyeri": 12.00,
    "DASK": 9.75, "TSS": 16.25, "Yol yardım": 16.25, "Mali Sorumluluk": 6.50, "Diğer": 10.00
}

SIRKETLER = sorted([
    "Aksigorta", "Allianz Sigorta", "Anadolu Sigorta", "Ankara Sigorta", "Axa Sigorta", 
    "Doğa Sigorta", "HDI Sigorta", "Mapfre Sigorta", "Sompo Sigorta", "Türkiye Sigorta"
]) + ["Diğer"]

def render_yeni_police(df, conn):
    st.markdown("### 📝 Yeni Poliçe Kayıt Merkezi")
    st.info("Lütfen poliçe bilgilerini eksiksiz giriniz. Komisyon ve Vade otomatik hesaplanacaktır.")

    with st.form("yeni_kayit_formu", clear_on_submit=True):
        # Üst Panel: Müşteri ve No
        c1, c2 = st.columns(2)
        p_no = c1.text_input("🔢 Poliçe Numarası", placeholder="Örn: 12345678")
        m_adi = c2.text_input("👤 Müşteri Adı Soyadı", placeholder="Örn: Ahmet Yılmaz")

        # Orta Panel: Şirket ve Branş
        c3, c4, c5 = st.columns(3)
        sirket = c3.selectbox("🏢 Sigorta Şirketi", SIRKETLER)
        brans = c4.selectbox("📑 Branş", list(KOMISYON_ORANLARI.keys()))
        prim = c5.number_input("💰 Brüt Prim (TL)", min_value=0.0, step=100.0, format="%.2f")

        # Alt Panel: Tarihler
        st.divider()
        t1, t2 = st.columns(2)
        tanzim = t1.date_input("📅 Tanzim Tarihi", datetime.now())
        sure = t2.selectbox("⏳ Poliçe Süresi", ["1 Yıllık", "6 Aylık", "2 Aylık"])
        
        # Otomatik Hesaplamalar
        if sure == "1 Yıllık": bitis = tanzim + relativedelta(years=1)
        elif sure == "6 Aylık": bitis = tanzim + relativedelta(months=6)
        else: bitis = tanzim + relativedelta(months=2)

        st.warning(f"💡 Otomatik Vade Sonu: **{bitis.strftime('%d.%m.%Y')}**")

        # Gönderme Butonu
        submit = st.form_submit_button("🚀 POLİÇEYİ SİSTEME İŞLE", use_container_width=True)

        if submit:
            if p_no and m_adi and prim > 0:
                # Komisyon Hesabı
                kazanc = prim * (KOMISYON_ORANLARI[brans] / 100)
                
                # Yeni Satır Oluşturma
                new_data = pd.DataFrame([{
                    "police_no": str(p_no),
                    "musteri_adi": str(m_adi).upper(),
                    "sigorta_sirketi": sirket,
                    "police_turu": brans,
                    "brut_prim": float(prim),
                    "net_komisyon": float(kazanc),
                    "tanzim_tarihi": tanzim.strftime("%Y-%m-%d"),
                    "bitis_tarihi": bitis.strftime("%Y-%m-%d"),
                    "arsiv": False # Her yeni kayıt aktiftir
                }])

                # Google Sheets Güncelleme
                try:
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    conn.update(worksheet="Sayfa1", data=updated_df)
                    st.balloons()
                    st.success(f"✅ {m_adi} adına {brans} poliçesi başarıyla kaydedildi!")
                except Exception as e:
                    st.error(f"Veri gönderilirken hata oluştu: {e}")
            else:
                st.error("Lütfen Poliçe No, Müşteri Adı ve Prim alanlarını boş bırakmayın!")

# Bu fonksiyonu ana kodundaki 'choice == "yeni"' kısmına yapıştıracağız.
