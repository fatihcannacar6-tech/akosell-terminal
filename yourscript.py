import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
from datetime import datetime
import plotly.graph_objects as go
try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# --- 1. VERİTABANI VE SİSTEM AYARLARI ---
USER_DB, PORT_DB = "users_v15.csv", "portfolio_v15.csv"

def init_db():
    if not os.path.exists(USER_DB):
        # Admin: fatihcan / 8826244 (Status: Active)
        hp = hashlib.sha256(str.encode("8826244")).hexdigest()
        users = pd.DataFrame([["fatihcan", hp, "Fatih Can", "Admin", "Active"]], 
                             columns=["Username", "Password", "Name", "Role", "Status"])
        users.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. MODERN BEYAZ ARAYÜZ ---
st.set_page_config(page_title="AKOSELL WMS Terminal", layout="wide", page_icon="🏛️")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #F8FAFC; }
    .ai-report-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .stMetric { background: white !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONKSİYONLAR ---
def fetch_prices(df):
    if df.empty: return df
    df = df.copy()
    prices = []
    for _, r in df.iterrows():
        sym = f"{r['Kod']}.IS" if r['Kat'] == "Hisse" else (f"{r['Kod']}-USD" if r['Kat'] == "Kripto" else r['Kod'])
        try:
            data = yf.Ticker(sym).history(period="1d")
            prices.append(data['Close'].iloc[-1] if not data.empty else r['Maliyet'])
        except: prices.append(r['Maliyet'])
    df['Güncel'] = prices
    df['Değer'] = df['Güncel'] * df['Adet']
    df['KarZarar'] = df['Değer'] - (df['Maliyet'] * df['Adet'])
    return df

# --- 4. GİRİŞ VE KAYIT SİSTEMİ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Talebi"])
    with tab1:
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        if st.button("TERMİNALE GİRİŞ", use_container_width=True, type="primary"):
            users = pd.read_csv(USER_DB)
            hp = hashlib.sha256(str.encode(p)).hexdigest()
            match = users[(users['Username']==u) & (users['Password']==hp)]
            if not match.empty:
                if match.iloc[0]['Status'] == "Active":
                    st.session_state.logged_in = True
                    st.session_state.u_data = match.iloc[0].to_dict()
                    st.rerun()
                else: st.warning("Hesabınız henüz onaylanmadı. Lütfen Admin ile iletişime geçin.")
            else: st.error("Hatalı bilgiler.")
    
    with tab2:
        new_u = st.text_input("Yeni Kullanıcı Adı").lower()
        new_n = st.text_input("Ad Soyad")
        new_p = st.text_input("Şifre Belirleyin", type="password")
        if st.button("KAYIT TALEBİ GÖNDER", use_container_width=True):
            users = pd.read_csv(USER_DB)
            if new_u in users['Username'].values: st.error("Bu kullanıcı adı alınmış.")
            else:
                hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                new_user = pd.DataFrame([[new_u, hp, new_n, "User", "Pending"]], columns=users.columns)
                new_user.to_csv(USER_DB, mode='a', header=False, index=False)
                st.success("Talebiniz iletildi. Admin onayı bekleniyor.")

else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 🏛️ AKOSELL WMS\n**{st.session_state.u_data['Name']}**")
        nav = ["📊 DASHBOARD", "🤖 AI STRATEJİST", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR"]
        if st.session_state.u_data['Role'] == "Admin": nav.append("🔑 ADMIN PANELİ")
        menu = st.radio("MENÜ", nav)
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']]

    # --- 6. DASHBOARD (DETAYLI RAPORLAR) ---
    if menu == "📊 DASHBOARD":
        st.title("📊 Portföy Detaylı Analiz Raporu")
        if not my_port.empty:
            with st.spinner("Raporlar hazırlanıyor..."):
                proc_df = fetch_prices(my_port)
                total_val = proc_df['Değer'].sum()
                total_prof = proc_df['KarZarar'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Varlık", f"₺{total_val:,.2f}")
                c2.metric("Net Kâr/Zarar", f"₺{total_prof:,.2f}", delta=f"{(total_prof/(total_val-total_prof)*100):.2f}%")
                c3.metric("Varlık Dağılımı", f"{len(proc_df)} Kalem")

                # AI ÖZET RAPORU
                st.markdown(f"""
                <div class="ai-report-card">
                    <h4>🤖 AI Portföy Sağlık Raporu</h4>
                    <p>Mevcut piyasa verilerine göre portföyünüzün toplam kârlılık oranı <b>%{(total_prof/(total_val-total_prof)*100):.2f}</b> seviyesindedir. 
                    En yüksek verim sağlayan varlığınız: <b>{proc_df.loc[proc_df['KarZarar'].idxmax(), 'Kod']}</b>.</p>
                </div>
                """, unsafe_allow_html=True)

                st.subheader("📋 Güncel Pozisyon Detayları")
                st.dataframe(proc_df[["Kod", "Kat", "Adet", "Maliyet", "Güncel", "KarZarar"]], use_container_width=True, hide_index=True)
                
                st.plotly_chart(go.Figure(data=[go.Pie(labels=proc_df['Kod'], values=proc_df['Değer'], hole=.4)]))
        else: st.info("Rapor oluşturmak için varlık ekleyin.")

    # --- 7. ADMIN PANELİ (ONAY/RET) ---
    elif menu == "🔑 ADMIN PANELİ":
        st.title("🔑 Onay Bekleyen Kayıtlar")
        u_df = pd.read_csv(USER_DB)
        pending = u_df[u_df['Status'] == "Pending"]
        if not pending.empty:
            for i, row in pending.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{row['Name']}** (@{row['Username']})")
                if col2.button("✅ ONAYLA", key=f"ok_{row['Username']}"):
                    u_df.loc[u_df['Username'] == row['Username'], 'Status'] = "Active"
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
                if col3.button("❌ REDDET", key=f"no_{row['Username']}"):
                    u_df = u_df[u_df['Username'] != row['Username']]
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
        else: st.info("Onay bekleyen yeni talep bulunmamaktadır.")

    # --- 8. OPTİMİZASYON ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ AI Portföy Optimizasyonu")
        if SCIPY_AVAILABLE and len(my_port) >= 3:
            assets = my_port['Kod'].unique()
            data = pd.DataFrame()
            for a in assets:
                tk = f"{a}.IS" if my_port[my_port['Kod']==a]['Kat'].values[0]=="Hisse" else f"{a}-USD"
                data[a] = yf.Ticker(tk).history(period="1y")['Close']
            
            returns = data.pct_change().dropna()
            def get_vol(w): return np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
            res = minimize(get_vol, [1./len(assets)]*len(assets), bounds=[(0,1)]*len(assets), constraints={'type':'eq','fun': lambda x: np.sum(x)-1})
            
            st.plotly_chart(go.Figure(data=[go.Pie(labels=assets, values=res.x, hole=.3)]))
            st.success("Bu dağılım, yıllık volatilite verilerine göre en düşük riskli sepeti temsil eder.")
        else: st.warning("Analiz için en az 3 farklı varlık eklemelisiniz.")

    # --- 9. PORTFÖYÜM ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Yönetimi")
        with st.form("ekle"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Varlık Kodu (Örn: THYAO)").upper()
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            cat = c4.selectbox("Tür", ["Hisse", "Kripto", "Altın"])
            if st.form_submit_button("SİSTEME KAYDET"):
                new_row = pd.DataFrame([[st.session_state.u_data['Username'], k, m, a, cat]], columns=df_port.columns)
                pd.concat([pd.read_csv(PORT_DB), new_row]).to_csv(PORT_DB, index=False)
                st.success("Eklendi!")
                st.rerun()
        st.divider()
        st.subheader("Mevcut Varlıklar")
        st.dataframe(my_port, use_container_width=True)

    # --- 10. AYARLAR ---
    elif menu == "⚙️ AYARLAR":
        st.title("⚙️ Hesap Ayarları")
        new_p = st.text_input("Yeni Şifre", type="password")
        if st.button("Şifreyi Güncelle"):
            u_df = pd.read_csv(USER_DB)
            u_df.loc[u_df['Username'] == st.session_state.u_data['Username'], 'Password'] = hashlib.sha256(str.encode(new_p)).hexdigest()
            u_df.to_csv(USER_DB, index=False)
            st.success("Şifre güncellendi.")