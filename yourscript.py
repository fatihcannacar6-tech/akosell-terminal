import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
from datetime import datetime
import plotly.graph_objects as go
from scipy.optimize import minimize

# --- 1. VERİTABANI OLUŞTURMA SİSTEMİ (KRİTİK GÜNCELLEME) ---
USER_DB, PORT_DB = "users_v13.csv", "portfolio_v13.csv"

def init_db():
    # Kullanıcı Veritabanı Kontrolü
    if not os.path.exists(USER_DB):
        try:
            hp = hashlib.sha256(str.encode("8826244")).hexdigest()
            users = pd.DataFrame([["fatihcan", hp, "Fatih Can", "Admin", "Active"]], 
                                 columns=["Username", "Password", "Name", "Role", "Status"])
            users.to_csv(USER_DB, index=False)
            st.toast("Kullanıcı veritabanı başarıyla oluşturuldu!")
        except Exception as e:
            st.error(f"CSV oluşturma hatası (User): {e}")

    # Portföy Veritabanı Kontrolü
    if not os.path.exists(PORT_DB):
        try:
            pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)
            st.toast("Portföy veritabanı başarıyla oluşturuldu!")
        except Exception as e:
            st.error(f"CSV oluşturma hatası (Portfolio): {e}")

init_db()

# --- 2. MODERN BEYAZ ARAYÜZ ---
st.set_page_config(page_title="AutoFlow AI Terminal", layout="wide", page_icon="🏛️")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
    .ai-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .stMetric { background: white !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. GİRİŞ VE KAYIT PANELİ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    with tab1:
        with st.container(border=True):
            st.subheader("AKOSELL WMS Giriş")
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.button("Sisteme Giriş", use_container_width=True, type="primary"):
                if os.path.exists(USER_DB):
                    users = pd.read_csv(USER_DB)
                    hp = hashlib.sha256(str.encode(p)).hexdigest()
                    user_match = users[(users['Username']==u) & (users['Password']==hp)]
                    if not user_match.empty:
                        if user_match.iloc[0]['Status'] == "Active":
                            st.session_state.logged_in = True
                            st.session_state.u_data = user_match.iloc[0].to_dict()
                            st.rerun()
                        else: st.warning("Hesabınız henüz onaylanmamış.")
                    else: st.error("Hatalı kullanıcı adı veya şifre.")
                else: st.error("Veritabanı dosyası bulunamadı! Lütfen sayfayı yenileyin.")
    
    with tab2:
        with st.container(border=True):
            new_u = st.text_input("Yeni Kullanıcı Adı").lower()
            new_n = st.text_input("Ad Soyad")
            new_p = st.text_input("Yeni Şifre", type="password")
            if st.button("Kayıt Ol", use_container_width=True):
                users = pd.read_csv(USER_DB)
                if new_u in users['Username'].values: st.error("Kullanıcı adı mevcut.")
                else:
                    hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                    new_user = pd.DataFrame([[new_u, hp, new_n, "User", "Pending"]], columns=users.columns)
                    new_user.to_csv(USER_DB, mode='a', header=False, index=False)
                    st.success("Kayıt başarılı! Admin onayı bekleniyor.")

else:
    # --- 4. SIDEBAR VE NAVİGASYON ---
    with st.sidebar:
        st.markdown(f"### 🏛️ AutoFlow AI\n**{st.session_state.u_data.get('Name')}**")
        nav_options = ["📊 DASHBOARD", "🔍 PİYASA TAKİBİ", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR"]
        
        if st.session_state.u_data.get('Role') == "Admin":
            nav_options.append("🔑 ADMIN PANELİ")
            
        menu = st.radio("MENÜ", nav_options)
        st.divider()
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    # Veri Yükleme
    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']]

    # --- 5. PİYASA TAKİBİ ---
    if menu == "🔍 PİYASA TAKİBİ":
        st.title("🔍 Canlı Piyasa Arama")
        search = st.text_input("Varlık Kodu (Örn: THYAO, BTC-USD)", "THYAO")
        symbol = f"{search}.IS" if len(search) <= 5 and "-" not in search else search
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1mo")
            if not data.empty:
                st.metric(f"{search.upper()} Güncel", f"{data['Close'].iloc[-1]:.2f}")
                st.line_chart(data['Close'])
            else: st.error("Varlık bulunamadı.")
        except: st.error("Hata!")

    # --- 6. OPTİMİZASYON (DETAYLI) ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ Portföy Optimizasyonu")
        if len(my_port) >= 3:
            assets = my_port['Kod'].unique()
            prices = pd.DataFrame()
            for a in assets:
                tk = f"{a}.IS" if my_port[my_port['Kod']==a]['Kat'].values[0]=="Hisse" else f"{a}-USD"
                prices[a] = yf.Ticker(tk).history(period="1y")['Close']
            
            returns = prices.pct_change().dropna()
            mean_ret = returns.mean() * 252
            cov_mat = returns.cov() * 252

            def get_stats(w):
                p_ret = np.sum(mean_ret * w)
                p_vol = np.sqrt(np.dot(w.T, np.dot(cov_mat, w)))
                return p_ret, p_vol, (p_ret - 0.05) / p_vol

            res = minimize(lambda w: -get_stats(w)[2], [1./len(assets)]*len(assets), 
                           bounds=[(0,1)]*len(assets), constraints={'type':'eq','fun': lambda x: np.sum(x)-1})
            
            r, v, s = get_stats(res.x)
            st.markdown(f"""
            <div class="ai-card">
                <h4>📊 Optimizasyon Analizi</h4>
                <li>Yıllık Getiri Beklentisi: <b>%{r*100:.2f}</b></li>
                <li>Tahmini Risk: <b>%{v*100:.2f}</b></li>
                <li>Sharpe Skoru: <b>{s:.2f}</b></li>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(go.Figure(data=[go.Pie(labels=assets, values=res.x, hole=.3)]))
            
        else:
            st.warning("Optimizasyon için en az 3 farklı varlık ekleyin.")

    # --- 7. ADMIN PANELİ ---
    elif menu == "🔑 ADMIN PANELİ":
        st.title("🔑 Kayıt Onay Paneli")
        u_df = pd.read_csv(USER_DB)
        pending = u_df[u_df['Status'] == "Pending"]
        
        if not pending.empty:
            for i, row in pending.iterrows():
                c1, c2, c3 = st.columns([2,1,1])
                c1.write(f"**{row['Name']}** (@{row['Username']})")
                if c2.button("Onayla", key=f"y_{row['Username']}"):
                    u_df.loc[u_df['Username'] == row['Username'], 'Status'] = "Active"
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
                if c3.button("Reddet", key=f"n_{row['Username']}"):
                    u_df = u_df[u_df['Username'] != row['Username']]
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
        else:
            st.info("Bekleyen onay yok.")

    # --- 8. PORTFÖYÜM ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Portföy Yönetimi")
        with st.form("add"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Kod").upper()
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            cat = c4.selectbox("Tür", ["Hisse", "Kripto", "Döviz"])
            if st.form_submit_button("Ekle"):
                new = pd.DataFrame([[st.session_state.u_data['Username'], k, m, a, cat]], columns=df_port.columns)
                pd.concat([pd.read_csv(PORT_DB), new]).to_csv(PORT_DB, index=False)
                st.rerun()
        st.dataframe(my_port, use_container_width=True)