import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
import base64
from datetime import datetime, timedelta
from scipy.optimize import minimize
import plotly.graph_objects as go
from fpdf import FPDF

# --- 1. SİSTEM AYARLARI & DATABASE ---
USER_DB, PORT_DB = "users_v12.csv", "portfolio_v12.csv"

def init_db():
    if not os.path.exists(USER_DB):
        pd.DataFrame(columns=["Username", "Password", "Name", "Email"]).to_csv(USER_DB, index=False)
        # Varsayılan admin hesabı oluştur (Şifre: admin123)
        hp = hashlib.sha256(str.encode("admin123")).hexdigest()
        admin = pd.DataFrame([["admin", hp, "Sistem Yoneticisi", "admin@autoflow.com"]], columns=["Username", "Password", "Name", "Email"])
        admin.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. MODERN UI (WHITE INTERFACE) ---
st.set_page_config(page_title="AutoFlow AI Terminal", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .ai-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
    .user-profile { padding: 15px; background: #F1F5F9; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YARDIMCI FONKSİYONLAR (PDF, ANALİZ, OPTİMİZASYON) ---

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'AutoFlow AI - Yatirimci Raporu', 0, 1, 'C')

def get_pdf_download_link(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Rapor Tarihi: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    for i, row in df.iterrows():
        pdf.cell(0, 10, f"{row['Kod']} - Adet: {row['Adet']} - Maliyet: {row['Maliyet']} - Kar/Zarar: {row['Kâr/Zarar']:.2f}", 0, 1)
    return pdf.output(dest='S').encode('latin-1')

def fetch_prices(df):
    if df.empty: return df
    df = df.copy()
    prices = []
    for _, r in df.iterrows():
        sym = f"{r['Kod']}.IS" if r['Kat'] == "Hisse" else (f"{r['Kod']}-USD" if r['Kat'] == "Kripto" else r['Kod'])
        try: prices.append(yf.Ticker(sym).history(period="1d")['Close'].iloc[-1])
        except: prices.append(r['Maliyet'])
    df['Güncel Fiyat'] = prices
    df['Toplam Değer'] = df['Güncel Fiyat'] * df['Adet']
    df['Kâr/Zarar'] = df['Toplam Değer'] - (df['Maliyet'] * df['Adet'])
    return df

# --- 4. GİRİŞ KONTROLÜ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<h1 style='text-align:center;'>AKOSELL WMS</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Kullanıcı")
            p = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİRİŞ", use_container_width=True):
                users = pd.read_csv(USER_DB)
                hp = hashlib.sha256(str.encode(p)).hexdigest()
                if not users[(users['Username']==u) & (users['Password']==hp)].empty:
                    st.session_state.logged_in = True
                    st.session_state.u_data = users[users['Username']==u].iloc[0].to_dict()
                    st.rerun()
                else: st.error("Hatalı Giriş!")
else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        st.markdown(f'<div class="user-profile"><b>{st.session_state.u_data["Name"]}</b><br><small>Premium Member</small></div>', unsafe_allow_html=True)
        menu = st.radio("NAVIGASYON", ["📊 DASHBOARD", "🤖 AI STRATEJİST", "⚖️ OPTİMİZASYON", "⏪ BACKTEST", "💼 PORTFÖY", "⚙️ AYARLAR"])
        if st.button("GÜVENLİ ÇIKIŞ"):
            st.session_state.logged_in = False
            st.rerun()

    # Veri Yükleme
    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']] if not df_port.empty else pd.DataFrame()

    # --- 6. DASHBOARD ---
    if menu == "📊 DASHBOARD":
        st.title("Finansal Dashboard")
        if not my_port.empty:
            processed_df = fetch_prices(my_port)
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Portföy", f"₺{processed_df['Toplam Değer'].sum():,.2f}")
            c2.metric("Günlük Kar/Zarar", f"₺{processed_df['Kâr/Zarar'].sum():,.2f}")
            c3.metric("Aktif Varlık", len(processed_df))
            
            st.dataframe(processed_df, use_container_width=True)
            
            if st.button("📄 PDF RAPORU İNDİR"):
                pdf_bytes = get_pdf_download_link(processed_df)
                st.download_button("Dosyayı Kaydet", pdf_bytes, file_name="AutoFlow_Rapor.pdf")
        else:
            st.info("Portföyünüz boş.")

    # --- 7. AI STRATEJİST & SİNYALLER ---
    elif menu == "🤖 AI STRATEJİST":
        st.title("AI Teknik Analiz Motoru")
        if not my_port.empty:
            target = st.selectbox("Analiz Edilecek Varlık", my_port['Kod'].unique())
            hist = yf.Ticker(f"{target}.IS").history(period="1mo")
            
            st.line_chart(hist['Close'])
            
            # Basit Sinyal Mantığı
            last_price = hist['Close'].iloc[-1]
            ma20 = hist['Close'].rolling(20).mean().iloc[-1]
            
            st.markdown(f"""
            <div class="ai-card">
                <h3>AI Teknik Görünüm: {target}</h3>
                <p>Fiyat: <b>{last_price:.2f}</b> | 20 Günlük Ort: <b>{ma20:.2f}</b></p>
                <p>Durum: {"🟢 TREND YUKARI - ALIM GÜÇLÜ" if last_price > ma20 else "🔴 TREND AŞAĞI - BEKLE"} </p>
            </div>
            """, unsafe_allow_html=True)
            
    # --- 8. OPTİMİZASYON (MARKOWITZ) ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("Portföy Optimizasyonu")
        if len(my_port) >= 3:
            assets = my_port['Kod'].unique()
            data = pd.DataFrame()
            for a in assets:
                data[a] = yf.Ticker(f"{a}.IS").history(period="1y")['Close']
            
            returns = data.pct_change().dropna()
            def get_vol(w): return np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
            
            res = minimize(get_vol, [1./len(assets)]*len(assets), bounds=[(0,1)]*len(assets), constraints={'type':'eq','fun': lambda x: np.sum(x)-1})
            
            st.write("AI Önerilen Ağırlık Dağılımı:")
            for i, a in enumerate(assets):
                st.write(f"**{a}:** %{res.x[i]*100:.1f}")
            
            st.plotly_chart(go.Figure(data=[go.Pie(labels=assets, values=res.x)]))
        else:
            st.warning("En az 3 varlık gerekli.")

    # --- 9. BACKTEST ---
    elif menu == "⏪ BACKTEST":
        st.title("Geçmiş Performans Analizi")
        if not my_port.empty:
            bist = yf.Ticker("XU100.IS").history(period="1y")['Close']
            bist_norm = (bist / bist.iloc[0]) * 100
            st.line_chart(bist_norm)
            st.info("Portföyünüzün son 1 yıllık endeks kıyaslaması yukarıdadır.")

    # --- 10. PORTFÖY YÖNETİMİ ---
    elif menu == "💼 PORTFÖY":
        st.title("Varlık Yönetimi")
        with st.form("add_asset"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Kod (Örn: THYAO)")
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            t = c4.selectbox("Tür", ["Hisse", "Kripto", "Döviz"])
            if st.form_submit_button("Ekle"):
                new_data = pd.DataFrame([[st.session_state.u_data['Username'], k.upper(), m, a, t]], columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"])
                pd.concat([pd.read_csv(PORT_DB), new_data]).to_csv(PORT_DB, index=False)
                st.rerun()
        
        st.subheader("Mevcut Varlıklar")
        edited_df = st.data_editor(my_port, num_rows="dynamic")
        if st.button("Değişiklikleri Kaydet"):
            other_users = df_port[df_port['Owner'] != st.session_state.u_data['Username']]
            pd.concat([other_users, edited_df]).to_csv(PORT_DB, index=False)
            st.success("Güncellendi!")

    # --- 11. AYARLAR ---
    elif menu == "⚙️ AYARLAR":
        st.title("Profil ve Şifre")
        with st.expander("Şifre Değiştir"):
            new_p = st.text_input("Yeni Şifre", type="password")
            if st.button("Güncelle"):
                u_df = pd.read_csv(USER_DB)
                hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                u_df.loc[u_df['Username'] == st.session_state.u_data['Username'], 'Password'] = hp
                u_df.to_csv(USER_DB, index=False)
                st.success("Şifre değişti!")