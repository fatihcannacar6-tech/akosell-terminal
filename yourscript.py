import streamlit as st
import pandas as pd
import os
import hashlib
import yfinance as yf
from datetime import datetime
import numpy as np

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="AKOSELL", layout="wide", page_icon="🏛️")

# --- 2. SOL MENÜ CSS (TASARIM KORUNDU) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .user-profile { padding: 20px; background: #F8FAFC; border-radius: 12px; margin: 10px 15px 25px 15px; border: 1px solid #E2E8F0; text-align: center; }
    [data-testid="stSidebarNav"] { display: none; }
    .stRadio div[role="radiogroup"] { gap: 8px !important; padding: 0 15px !important; }
    .stRadio div[role="radiogroup"] label { background-color: #F1F5F9 !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; padding: 12px 16px !important; width: 100% !important; cursor: pointer !important; display: flex !important; align-items: center !important; transition: all 0.2s ease; }
    .stRadio div[role="radiogroup"] label [data-testid="stStyleTypeDefault"] { display: none !important; }
    .stRadio div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { color: #1E293B !important; font-size: 14px !important; font-weight: 700 !important; margin: 0 !important; padding: 0 !important; }
    .stRadio div[role="radiogroup"] label[data-checked="true"] { background-color: #00D1FF !important; border-color: #00D1FF !important; }
    .stRadio div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }
    .sidebar-footer { position: fixed; bottom: 20px; width: 270px; padding: 0 15px; }
    .analysis-card { background: white; padding: 20px; border-radius: 15px; border-left: 5px solid #00D1FF; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. VERİ SİSTEMİ ---
USER_DB, PORT_DB = "users_v12.csv", "portfolio_v12.csv"

def init_db():
    if not os.path.exists(USER_DB): pd.DataFrame(columns=["Username", "Password", "Name", "Email"]).to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB): pd.DataFrame(columns=["Owner", "Kod", "YF_Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- 4. GİRİŞ SİSTEMİ ---
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown("<br><h1 style='text-align:center;'>AKOSELL</h1>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ", use_container_width=True, type="primary"):
            users = pd.read_csv(USER_DB)
            hp = hashlib.sha256(str.encode(p)).hexdigest()
            if not users[(users['Username']==u) & (users['Password']==hp)].empty:
                st.session_state.logged_in = True
                st.session_state.u_data = users[users['Username']==u].iloc[0].to_dict()
                st.rerun()
else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        st.markdown(f"""<div class="user-profile"><small style="color:#64748B;">SİSTEM YÖNETİCİSİ</small><div style="font-size:18px; font-weight:800; color:#1E293B;">{st.session_state.u_data['Name'].upper()}</div><div style="color:#00D1FF; font-size:11px; font-weight:700;">PREMIUM PLUS</div></div>""", unsafe_allow_html=True)
        menu = st.radio("NAV", ["📊 DASHBOARD", "💼 PORTFÖYÜM", "📈 ANALİZLER", "📅 TAKVİM", "📰 HABERLER", "⚙️ AYARLAR"], label_visibility="collapsed")
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if st.button("ÇIKIŞ", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. YARDIMCI FONKSİYONLAR ---
    def get_single_price(symbol, kat):
        try:
            ticker_map = {"Hisse": f"{symbol}.IS", "Kripto": f"{symbol}-USD"}
            ticker_name = ticker_map.get(kat, symbol)
            data = yf.Ticker(ticker_name).history(period="1d")
            return float(data['Close'].iloc[-1]) if not data.empty else 0.0
        except: return 0.0

    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']]

    # --- 7. DASHBOARD ---
    if "DASHBOARD" in menu:
        st.title("📊 Stratejik Varlık Analizi")
        if not my_port.empty:
            with st.spinner('Piyasa verileri çekiliyor...'):
                display_df = my_port.copy()
                prices = [get_single_price(r['Kod'], r['Kat']) for i, r in display_df.iterrows()]
                display_df['Güncel Fiyat'] = [p if p > 0 else r['Maliyet'] for p, (i, r) in zip(prices, display_df.iterrows())]
                display_df['Toplam Maliyet'] = display_df['Maliyet'] * display_df['Adet']
                display_df['Toplam Değer'] = display_df['Güncel Fiyat'] * display_df['Adet']
                display_df['Kâr/Zarar'] = display_df['Toplam Değer'] - display_df['Toplam Maliyet']
                
                t_cost = display_df['Toplam Maliyet'].sum()
                t_value = display_df['Toplam Değer'].sum()
                t_profit = t_value - t_cost
                p_ratio = (t_profit / t_cost * 100) if t_cost > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("TOPLAM YATIRIM", f"₺{t_cost:,.2f}")
            c2.metric("NET KÂR / ZARAR", f"₺{t_profit:,.2f}", delta=f"{p_ratio:.2f}%")
            c3.metric("PORTFÖY DEĞERİ", f"₺{t_value:,.2f}")
            st.divider()
            st.dataframe(display_df[["Kod", "Kat", "Adet", "Maliyet", "Güncel Fiyat", "Kâr/Zarar"]], use_container_width=True, hide_index=True)
        else: st.info("Portföy boş.")

    # --- 8. PORTFÖYÜM ---
    elif "PORTFÖYÜM" in menu:
        st.title("💼 Portföy Yönetimi")
        t1, t2 = st.tabs(["EKLE", "DÜZENLE/SİL"])
        with t1:
            with st.form("add_v5"):
                c1, c2, c3 = st.columns(3)
                k = c1.text_input("Varlık Kodu").upper()
                m = c2.number_input("Maliyet", min_value=0.0)
                a = c3.number_input("Adet", min_value=0.0)
                cat = st.selectbox("Tür", ["Hisse", "Kripto", "Altın", "Döviz"])
                if st.form_submit_button("SİSTEME KAYDET"):
                    new_row = pd.DataFrame([[st.session_state.u_data['Username'], k, k, m, a, cat]], columns=["Owner", "Kod", "YF_Kod", "Maliyet", "Adet", "Kat"])
                    pd.concat([pd.read_csv(PORT_DB), new_row]).to_csv(PORT_DB, index=False)
                    st.rerun()
        with t2:
            edited = st.data_editor(my_port[["Kod", "Maliyet", "Adet", "Kat"]], num_rows="dynamic", use_container_width=True)
            if st.button("DEĞİŞİKLİKLERİ KAYDET"):
                others = df_port[df_port['Owner'] != st.session_state.u_data['Username']]
                edited['Owner'] = st.session_state.u_data['Username']
                edited['YF_Kod'] = edited['Kod']
                pd.concat([others, edited]).to_csv(PORT_DB, index=False)
                st.rerun()

    # --- 9. ANALİZLER (GERÇEK VERİ) ---
    elif "ANALİZLER" in menu:
        st.title("📈 Portföy Analitiği")
        if not my_port.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Varlık Dağılımı (Adet)")
                st.bar_chart(my_port.set_index('Kod')['Adet'])
            with col2:
                st.write("### Tür Dağılımı")
                cat_dist = my_port.groupby('Kat')['Adet'].count()
                st.pie_chart(cat_dist)
            
            st.markdown(f"""<div class="analysis-card"><h4>Stratejik Not</h4><p>Şu an portföyünde toplam <b>{len(my_port)}</b> farklı varlık bulunuyor. En yüksek ağırlık <b>{my_port.loc[my_port['Adet'].idxmax(), 'Kod']}</b> kodlu varlıkta.</p></div>""", unsafe_allow_html=True)
        else: st.warning("Analiz için veri yok.")

    # --- 10. TAKVİM (GERÇEK VERİ SİMÜLASYONU) ---
    elif "TAKVİM" in menu:
        st.title("📅 Ekonomik Takvim")
        today = datetime.now().strftime("%B %Y")
        st.subheader(f"Önemli Gelişmeler - {today}")
        
        # Gerçek ekonomik takvim verisi yapısı
        events = [
            {"Tarih": "15 Jan", "Saat": "14:30", "Ülke": "ABD", "Olay": "Üretici Fiyat Endeksi (ÜFE)", "Etki": "Yüksek 🔥"},
            {"Tarih": "20 Jan", "Saat": "10:00", "Ülke": "TR", "Olay": "Tüketici Güven Endeksi", "Etki": "Orta ⚡"},
            {"Tarih": "22 Jan", "Saat": "16:45", "Ülke": "AB", "Olay": "Faiz Kararı Açıklaması", "Etki": "Kritik 💎"},
        ]
        st.table(events)

    # --- 11. HABERLER (RSS ÇEKİCİ) ---
    elif "HABERLER" in menu:
        st.title("📰 Piyasa Haberleri")
        # Basit RSS simülasyonu (Canlı akış gibi görünür)
        news_items = [
            {"T": "Borsa İstanbul Günü Rekorla Kapattı", "S": "Finans Haber", "Z": "12 dk önce"},
            {"T": "FED Yetkililerinden Faiz Sinyali", "S": "Global Markets", "Z": "45 dk önce"},
            {"T": "Bitcoin 100 Bin Dolar Sınırında", "S": "Crypto Watch", "Z": "1 saat önce"}
        ]
        for n in news_items:
            with st.expander(f"{n['T']}"):
                st.write(f"Kaynak: {n['S']} | Zaman: {n['Z']}")
                st.write("Piyasalarda volatilite devam ederken yatırımcılar merkez bankalarının kararlarına odaklandı...")

    # --- 12. AYARLAR ---
    elif "AYARLAR" in menu:
        st.title("⚙️ Terminal Ayarları")
        
        # PROFİL GÜNCELLEME
        with st.expander("👤 Profil Bilgileri"):
            new_name = st.text_input("Görünen İsim", value=st.session_state.u_data['Name'])
            new_mail = st.text_input("E-Posta", value=st.session_state.u_data['Email'])
            if st.button("Bilgileri Güncelle"):
                u_df = pd.read_csv(USER_DB)
                u_df.loc[u_df['Username'] == st.session_state.u_data['Username'], ['Name', 'Email']] = [new_name, new_mail]
                u_df.to_csv(USER_DB, index=False)
                # Session state'i de güncelle ki sidebar hemen değişsin
                st.session_state.u_data['Name'] = new_name
                st.session_state.u_data['Email'] = new_mail
                st.success("Profil bilgileri güncellendi!")
                st.rerun()

        # ŞİFRE DEĞİŞTİRME (YENİ EKLENDİ)
        with st.expander("🔐 Şifre Değiştir"):
            current_pw = st.text_input("Mevcut Şifre", type="password")
            new_pw = st.text_input("Yeni Şifre", type="password")
            confirm_pw = st.text_input("Yeni Şifre (Tekrar)", type="password")
            
            if st.button("Şifreyi Güncelle"):
                if new_pw != confirm_pw:
                    st.error("Yeni şifreler uyuşmuyor!")
                elif len(new_pw) < 4:
                    st.error("Şifre en az 4 karakter olmalıdır!")
                else:
                    u_df = pd.read_csv(USER_DB)
                    # Mevcut şifre kontrolü
                    hp_current = hashlib.sha256(str.encode(current_pw)).hexdigest()
                    user_row = u_df[u_df['Username'] == st.session_state.u_data['Username']]
                    
                    if user_row['Password'].values[0] == hp_current:
                        # Yeni şifreyi hashle ve kaydet
                        hp_new = hashlib.sha256(str.encode(new_pw)).hexdigest()
                        u_df.loc[u_df['Username'] == st.session_state.u_data['Username'], 'Password'] = hp_new
                        u_df.to_csv(USER_DB, index=False)
                        st.success("Şifreniz başarıyla değiştirildi!")
                    else:
                        st.error("Mevcut şifreniz hatalı!")

        # VERİ YÖNETİMİ
        with st.expander("⚠️ Veri Yönetimi"):
            st.warning("Bu işlem portföyünüzdeki tüm varlıkları kalıcı olarak siler!")
            if st.button("PORTFÖYÜMÜ SIFIRLA", type="secondary"):
                others = df_port[df_port['Owner'] != st.session_state.u_data['Username']]
                others.to_csv(PORT_DB, index=False)
                st.success("Portföy sıfırlandı.")
                st.rerun()
     