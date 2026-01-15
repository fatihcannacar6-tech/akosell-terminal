import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
import base64
from datetime import datetime, timedelta
import plotly.graph_objects as go
from fpdf import FPDF

# Scipy kontrolü (Optimizasyon için gerekli)
try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# --- 1. VERİTABANI VE ÖZEL GİRİŞ AYARLARI ---
USER_DB, PORT_DB = "users_v12.csv", "portfolio_v12.csv"

def init_db():
    if not os.path.exists(USER_DB):
        # Senin istediğin kullanıcı bilgilerini hashleyerek ekliyoruz
        u_name = "fatihcan"
        u_pass = "8826244"
        hp = hashlib.sha256(str.encode(u_pass)).hexdigest()
        
        users = pd.DataFrame([[u_name, hp, "Fatih Can", "fatihcan@autoflow.com"]], 
                             columns=["Username", "Password", "Name", "Email"])
        users.to_csv(USER_DB, index=False)
        
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. MODERN BEYAZ ARAYÜZ (CSS) ---
st.set_page_config(page_title="AutoFlow AI Terminal", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #FBFBFE; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .ai-card { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #4F46E5; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stMetric { background: white !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #F1F5F9 !important; }
    .user-profile { padding: 20px; background: #F8FAFC; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 20px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YARDIMCI FONKSİYONLAR ---
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
    df['Güncel Fiyat'] = prices
    df['Toplam Değer'] = df['Güncel Fiyat'] * df['Adet']
    df['Kâr/Zarar'] = df['Toplam Değer'] - (df['Maliyet'] * df['Adet'])
    return df

# --- 4. GİRİŞ PANELİ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<br><h1 style='text-align:center; color:#1E293B;'>AKOSELL WMS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;'>AutoFlow AI Terminal'e Hoş Geldiniz</p>", unsafe_allow_html=True)
        with st.container(border=True):
            user_input = st.text_input("Kullanıcı Adı")
            pass_input = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİRİŞ YAP", use_container_width=True, type="primary"):
                users = pd.read_csv(USER_DB)
                hp_input = hashlib.sha256(str.encode(pass_input)).hexdigest()
                
                # Giriş Kontrolü
                match = users[(users['Username']==user_input) & (users['Password']==hp_input)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.u_data = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        st.markdown(f"""<div class="user-profile"><small>SİSTEM YÖNETİCİSİ</small><br><b>{st.session_state.u_data['Name'].upper()}</b><br><span style="color:#4F46E5; font-size:11px; font-weight:bold;">PREMIUM PLUS</span></div>""", unsafe_allow_html=True)
        menu = st.radio("MENÜ", ["📊 DASHBOARD", "🤖 AI STRATEJİST", "⚖️ OPTİMİZASYON", "⏪ BACKTEST", "💼 PORTFÖYÜM", "⚙️ AYARLAR"])
        st.divider()
        if st.button("GÜVENLİ ÇIKIŞ", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # Veri Hazırlama
    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']] if not df_port.empty else pd.DataFrame()

    # --- 6. DASHBOARD ---
    if menu == "📊 DASHBOARD":
        st.title("📊 Portföy Dashboard")
        if not my_port.empty:
            with st.spinner("Piyasa verileri anlık olarak çekiliyor..."):
                proc_df = fetch_prices(my_port)
                c1, c2, c3 = st.columns(3)
                total_val = proc_df['Toplam Değer'].sum()
                total_cost = (proc_df['Maliyet'] * proc_df['Adet']).sum()
                total_profit = total_val - total_cost
                
                c1.metric("Toplam Değer", f"₺{total_val:,.2f}")
                c2.metric("Toplam Kâr / Zarar", f"₺{total_profit:,.2f}", delta=f"{(total_profit/total_cost*100):.2f}%" if total_cost > 0 else "0%")
                c3.metric("Varlık Sayısı", f"{len(proc_df)} Adet")
                
                st.dataframe(proc_df[["Kod", "Kat", "Adet", "Maliyet", "Güncel Fiyat", "Kâr/Zarar"]], use_container_width=True, hide_index=True)
        else:
            st.info("Portföyünüz henüz boş. Portföyüm sekmesinden varlık ekleyebilirsiniz.")

    # --- 7. AI STRATEJİST ---
    elif menu == "🤖 AI STRATEJİST":
        st.title("🤖 AutoFlow AI Analiz")
        if not my_port.empty:
            target = st.selectbox("Analiz Edilecek Varlık", my_port['Kod'].unique())
            ticker = f"{target}.IS" if my_port[my_port['Kod']==target]['Kat'].values[0]=="Hisse" else f"{target}-USD"
            hist = yf.Ticker(ticker).history(period="1mo")
            
            if not hist.empty:
                st.line_chart(hist['Close'])
                last_price = hist['Close'].iloc[-1]
                ma20 = hist['Close'].rolling(20).mean().iloc[-1]
                
                st.markdown(f"""
                <div class="ai-card">
                    <h3>AI Teknik Analiz Raporu: {target}</h3>
                    <p>Son Fiyat: <b>{last_price:.2f}</b> | Trend Ortalaması (20G): <b>{ma20:.2f}</b></p>
                    <p>AI Sinyali: <b>{"🟢 TREND POZİTİF - TUT" if last_price > ma20 else "🔴 TREND ZAYIF - DİKKAT"}</b></p>
                </div>
                """, unsafe_allow_html=True)
        else: st.warning("Analiz yapılacak varlık bulunamadı.")

    # --- 8. OPTİMİZASYON ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ Portföy Optimizasyonu")
        if SCIPY_AVAILABLE and len(my_port) >= 3:
            assets = my_port['Kod'].unique()
            data = pd.DataFrame()
            for a in assets:
                tk = f"{a}.IS" if my_port[my_port['Kod']==a]['Kat'].values[0]=="Hisse" else f"{a}-USD"
                data[a] = yf.Ticker(tk).history(period="1y")['Close']
            
            returns = data.pct_change().dropna()
            def get_vol(w): return np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
            
            res = minimize(get_vol, [1./len(assets)]*len(assets), bounds=[(0,1)]*len(assets), constraints=({'type':'eq','fun': lambda x: np.sum(x)-1}))
            
            fig = go.Figure(data=[go.Pie(labels=assets, values=res.x, hole=.3)])
            st.plotly_chart(fig)
            st.success("AI: En düşük risk için ideal varlık dağılımı yukarıdaki gibidir.")
        elif not SCIPY_AVAILABLE:
            st.error("Optimizasyon modülü (Scipy) yüklü değil.")
        else:
            st.warning("Optimizasyon için en az 3 farklı varlık eklemelisiniz.")

    # --- 9. BACKTEST ---
    elif menu == "⏪ BACKTEST":
        st.title("⏪ Portföy Backtest")
        bist = yf.Ticker("XU100.IS").history(period="1y")['Close']
        st.line_chart((bist / bist.iloc[0]) * 100)
        st.info("BIST100 Endeksinin son 1 yıllık performans grafiği.")

    # --- 10. PORTFÖY YÖNETİMİ ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Yönetimi")
        with st.form("ekle_v12"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Varlık Kodu (Örn: THYAO)").upper()
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            cat = c4.selectbox("Tür", ["Hisse", "Kripto", "Döviz", "Altın"])
            if st.form_submit_button("SİSTEME KAYDET"):
                new_row = pd.DataFrame([[st.session_state.u_data['Username'], k, m, a, cat]], 
                                       columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"])
                pd.concat([pd.read_csv(PORT_DB), new_row]).to_csv(PORT_DB, index=False)
                st.success(f"{k} Başarıyla eklendi!")
                st.rerun()
        
        st.divider()
        edited = st.data_editor(my_port, num_rows="dynamic", use_container_width=True)
        if st.button("DEĞİŞİKLİKLERİ KAYDET"):
            others = df_port[df_port['Owner'] != st.session_state.u_data['Username']]
            pd.concat([others, edited]).to_csv(PORT_DB, index=False)
            st.success("Portföy güncellendi!")
            st.rerun()

    # --- 11. AYARLAR ---
    elif menu == "⚙️ AYARLAR":
        st.title("⚙️ Terminal Ayarları")
        with st.expander("👤 Kullanıcı ve Şifre Bilgileri"):
            st.write(f"**Mevcut Kullanıcı:** {st.session_state.u_data['Username']}")
            new_p = st.text_input("Yeni Şifre", type="password")
            confirm = st.text_input("Yeni Şifre Tekrar", type="password")
            if st.button("Şifreyi Güncelle"):
                if new_p == confirm and len(new_p) > 3:
                    u_df = pd.read_csv(USER_DB)
                    hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                    u_df.loc[u_df['Username'] == st.session_state.u_data['Username'], 'Password'] = hp
                    u_df.to_csv(USER_DB, index=False)
                    st.success("Şifreniz güncellendi. Bir sonraki girişte yeni şifrenizi kullanın.")
                else: st.error("Şifreler uyuşmuyor veya çok kısa!")