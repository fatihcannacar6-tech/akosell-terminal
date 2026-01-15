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
USER_DB, PORT_DB = "users_v15_final.csv", "portfolio_v15_final.csv"

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

# --- 2. MODERN ARAYÜZ ---
st.set_page_config(page_title="AKOSELL WMS Terminal", layout="wide", page_icon="🏛️")
st.markdown("""<style> .ai-report-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; } .stMetric { background: white !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; } </style>""", unsafe_allow_html=True)

# --- 3. GİRİŞ VE KAYIT SİSTEMİ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Talebi"])
    with tab1:
        u = st.text_input("Kullanıcı Adı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        if st.button("TERMİNALE GİRİŞ", use_container_width=True, type="primary"):
            users = pd.read_csv(USER_DB)
            hp = hashlib.sha256(str.encode(p)).hexdigest()
            match = users[(users['Username']==u) & (users['Password']==hp)]
            if not match.empty:
                if match.iloc[0]['Status'] == "Active":
                    st.session_state.logged_in = True
                    st.session_state.u_data = match.iloc[0].to_dict()
                    st.rerun()
                else: st.warning("Hesabınız admin onayı bekliyor.")
            else: st.error("Hatalı bilgiler.")
    
    with tab2:
        new_u = st.text_input("Yeni Kullanıcı Adı").lower()
        new_n = st.text_input("Ad Soyad")
        new_p = st.text_input("Şifre", type="password")
        if st.button("KAYIT TALEBİ GÖNDER"):
            users = pd.read_csv(USER_DB)
            if new_u in users['Username'].values: st.error("Kullanıcı adı mevcut.")
            else:
                hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                new_user = pd.DataFrame([[new_u, hp, new_n, "User", "Pending"]], columns=users.columns)
                new_user.to_csv(USER_DB, mode='a', header=False, index=False)
                st.success("Talep gönderildi!")

else:
    # --- 4. SIDEBAR (HATA DÜZELTİLMİŞ KISIM) ---
    with st.sidebar:
        # get() kullanarak Role veya Name anahtarı yoksa hata vermesini engelliyoruz
        user_name = st.session_state.u_data.get('Name', 'Kullanıcı')
        user_role = st.session_state.u_data.get('Role', 'User')
        
        st.markdown(f"### 🏛️ AKOSELL WMS\n**{user_name}**")
        nav = ["📊 DASHBOARD", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR"]
        
        if user_role == "Admin":
            nav.append("🔑 ADMIN PANELİ")
            
        menu = st.radio("MENÜ", nav)
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    # Veri Yükleme
    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data.get('Username')]

    # --- 5. DASHBOARD & RAPORLAR ---
    if menu == "📊 DASHBOARD":
        st.title("📊 Portföy Detaylı Analiz Raporu")
        if not my_port.empty:
            # Buraya önceki fiyat çekme ve raporlama kodları gelecek
            st.dataframe(my_port)
            st.info("AI Raporu ve fiyatlar için varlıklarınıza göz atın.")
        else:
            st.info("Varlık bulunamadı. Lütfen 'PORTFÖYÜM' sekmesinden ekleme yapın.")

    # --- 6. ADMIN PANELİ ---
    elif menu == "🔑 ADMIN PANELİ":
        st.title("🔑 Admin Onay/Ret Paneli")
        u_df = pd.read_csv(USER_DB)
        pending = u_df[u_df['Status'] == "Pending"]
        if not pending.empty:
            for i, row in pending.iterrows():
                c1, c2, c3 = st.columns([2,1,1])
                c1.write(f"**{row['Name']}** (@{row['Username']})")
                if c2.button("✅ ONAY", key=f"ok_{row['Username']}"):
                    u_df.loc[u_df['Username'] == row['Username'], 'Status'] = "Active"
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
                if c3.button("❌ RET", key=f"no_{row['Username']}"):
                    u_df = u_df[u_df['Username'] != row['Username']]
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
        else: st.info("Bekleyen onay yok.")
        
    # --- 7. PORTFÖYÜM ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Yönetimi")
        with st.form("add_v15"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Kod").upper()
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            cat = c4.selectbox("Tür", ["Hisse", "Kripto", "Altın"])
            if st.form_submit_button("Sisteme Kaydet"):
                new = pd.DataFrame([[st.session_state.u_data['Username'], k, m, a, cat]], columns=df_port.columns)
                pd.concat([pd.read_csv(PORT_DB), new]).to_csv(PORT_DB, index=False)
                st.rerun()