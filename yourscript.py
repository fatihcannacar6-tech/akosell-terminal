import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
from datetime import datetime
import plotly.graph_objects as go
from scipy.optimize import minimize
from fpdf import FPDF
import base64

# --- 1. VERİTABANI ---
USER_DB, PORT_DB = "users_v18.csv", "portfolio_v18.csv"

def init_db():
    if not os.path.exists(USER_DB):
        hp = hashlib.sha256(str.encode("8826244")).hexdigest()
        users = pd.DataFrame([["fatihcan", hp, "Fatih Can", "Admin", "Active"]], 
                             columns=["Username", "Password", "Name", "Role", "Status"])
        users.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. MOBİL UYUMLU BEYAZ ARAYÜZ ---
st.set_page_config(page_title="AutoFlow", layout="centered", page_icon="") # Mobil için 'centered' daha iyidir

st.markdown("""
    <style>
    /* Giriş alanlarını ve butonu küçültme */
    .stTextInput > div > div > input { padding: 8px !important; font-size: 14px !important; }
    div.stButton > button { width: 100% !important; border-radius: 8px !important; height: 45px !important; font-weight: 600 !important; }
    
    /* Mobil uyumlu kart tasarımı */
    .ai-card { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; font-size: 14px; }
    
    @media (max-width: 640px) {
        .main .block-container { padding: 1rem !important; }
        .stMetric { padding: 10px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YARDIMCI ARAÇLAR ---
def create_pdf(data_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "AutoFlow AI - Optimizasyon Raporu", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Tarih: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    
    # Tablo Başlıkları
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Varlik", 1, 0, "C", True)
    pdf.cell(50, 10, "Risk (%)", 1, 0, "C", True)
    pdf.cell(50, 10, "Risk Seviyesi", 1, 0, "C", True)
    pdf.cell(50, 10, "AI Sinyali", 1, 1, "C", True)
    
    for item in data_list:
        pdf.cell(40, 10, str(item['Varlık']), 1)
        pdf.cell(50, 10, str(item['Yıllık Risk (%)']), 1)
        pdf.cell(50, 10, str(item['Risk Seviyesi']), 1)
        pdf.cell(50, 10, str(item['AI Sinyali']), 1, 1)
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. GİRİŞ VE KAYIT ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 4, 1]) # Ekranın ortasında daha küçük toplu durur
    with center_col:
        st.title("AutoFlow")
        tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
        with tab1:
            u = st.text_input("Kullanıcı Adı", key="l_u")
            p = st.text_input("Şifre", type="password", key="l_p")
            if st.button("SİSTEME GİRİŞ", type="primary"):
                users = pd.read_csv(USER_DB)
                hp = hashlib.sha256(str.encode(p)).hexdigest()
                match = users[(users['Username']==u) & (users['Password']==hp)]
                if not match.empty:
                    if match.iloc[0]['Status'] == "Active":
                        st.session_state.logged_in = True
                        st.session_state.u_data = match.iloc[0].to_dict()
                        st.rerun()
                    else: st.warning("Admin onayı bekleniyor.")
                else: st.error("Hatalı giriş.")
        with tab2:
            new_u = st.text_input("Kullanıcı Adı Seç", key="r_u").lower()
            new_n = st.text_input("Ad Soyad", key="r_n")
            new_p = st.text_input("Şifre Belirle", type="password", key="r_p")
            if st.button("KAYIT OL"):
                users = pd.read_csv(USER_DB)
                if new_u in users['Username'].values: st.error("Bu ad alınmış.")
                else:
                    hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                    pd.DataFrame([[new_u, hp, new_n, "User", "Pending"]], columns=users.columns).to_csv(USER_DB, mode='a', header=False, index=False)
                    st.success("Talep gönderildi.")

else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        st.write(f"Hoş geldin, **{st.session_state.u_data.get('Name')}**")
        menu = st.radio("MENÜ", ["📊 DASHBOARD", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR", "🔑 ADMIN PANELİ"] if st.session_state.u_data.get('Role') == 'Admin' else ["📊 DASHBOARD", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR"])
        if st.button("Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data.get('Username')]

    # --- 6. OPTİMİZASYON & PDF RAPOR (İstediğin Bölüm) ---
    if menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ AI Optimizasyon")
        if len(my_port) >= 2:
            analysis_data = []
            for a in my_port['Kod'].unique():
                tk = f"{a}.IS" if my_port[my_port['Kod']==a]['Kat'].values[0]=="Hisse" else f"{a}-USD"
                h = yf.Ticker(tk).history(period="1y")['Close']
                vol = h.pct_change().std() * np.sqrt(252) * 100
                sig = "🟢 TUT" if h.iloc[-1] > h.rolling(20).mean().iloc[-1] else "🔴 SAT"
                analysis_data.append({"Varlık": a, "Yıllık Risk (%)": f"{vol:.2f}", "Risk Seviyesi": "Düşük" if vol < 25 else "Yüksek", "AI Sinyali": sig})
            
            st.table(analysis_data)
            
            # PDF BUTONU
            pdf_bytes = create_pdf(analysis_data)
            st.download_button(label="📄 ANALİZ RAPORUNU PDF İNDİR", data=pdf_bytes, file_name=f"AutoFlow_Rapor_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf", use_container_width=True)
            
        else: st.warning("Analiz için en az 2 varlık ekleyin.")

    # --- Diğer kısımlar (Dashboard, Portföyüm vb.) önceki ile aynı kalacak şekilde çalışır ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Ekle")
        with st.form("add"):
            k = st.text_input("Kod (THYAO)").upper()
            a = st.number_input("Adet", min_value=0.1)
            m = st.number_input("Maliyet", min_value=0.1)
            cat = st.selectbox("Tür", ["Hisse", "Kripto"])
            if st.form_submit_button("EKLE"):
                new = pd.DataFrame([[st.session_state.u_data['Username'], k, m, a, cat]], columns=df_port.columns)
                pd.concat([pd.read_csv(PORT_DB), new]).to_csv(PORT_DB, index=False)
                st.rerun()