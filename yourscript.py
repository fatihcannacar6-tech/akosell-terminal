import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
from datetime import datetime
import plotly.graph_objects as go
from scipy.optimize import minimize

# --- 1. VERİTABANI GÜVENLİĞİ ---
USER_DB, PORT_DB = "users_v14.csv", "portfolio_v14.csv"

def init_db():
    if not os.path.exists(USER_DB):
        hp = hashlib.sha256(str.encode("8826244")).hexdigest()
        users = pd.DataFrame([["fatihcan", hp, "Fatih Can", "Admin", "Active"]], 
                             columns=["Username", "Password", "Name", "Role", "Status"])
        users.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. AI ANALİZ MOTORU (Dashboard İçin) ---
def get_ai_advice(row):
    try:
        sym = f"{row['Kod']}.IS" if row['Kat'] == "Hisse" else f"{row['Kod']}-USD"
        data = yf.Ticker(sym).history(period="1mo")
        if data.empty: return "Veri Bekleniyor"
        
        last_close = data['Close'].iloc[-1]
        ma20 = data['Close'].rolling(20).mean().iloc[-1]
        
        if last_close > ma20: return "🟢 Güçlü Trend (AI: Tut)"
        else: return "🟡 Zayıf Trend (AI: İzle)"
    except:
        return "Analiz Yapılamadı"

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="AKOSELL WMS Terminal", layout="wide")
st.markdown("""<style> .ai-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; } </style>""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Giriş Ekranı (Daha Öncekiyle Aynı)
    st.title("AKOSELL WMS Giriş")
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        users = pd.read_csv(USER_DB)
        hp = hashlib.sha256(str.encode(p)).hexdigest()
        match = users[(users['Username']==u) & (users['Password']==hp)]
        if not match.empty and match.iloc[0]['Status'] == "Active":
            st.session_state.logged_in = True
            st.session_state.u_data = match.iloc[0].to_dict()
            st.rerun()
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("AutoFlow AI")
        menu = st.radio("MENÜ", ["📊 DASHBOARD", "🔍 PİYASA TAKİBİ", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "🔑 ADMIN PANELİ", "⚙️ AYARLAR"])
        if st.button("Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']]

    # --- 1. DASHBOARD (AI DESTEĞİ VE RAPORLAR EKLENDİ) ---
    if menu == "📊 DASHBOARD":
        st.title("📊 Yatırımcı Dashboard")
        
        if not my_port.empty:
            # AI Analizli Tablo Oluşturma
            with st.spinner("AI Portföyünüzü analiz ediyor..."):
                prices = []
                advices = []
                for _, r in my_port.iterrows():
                    sym = f"{r['Kod']}.IS" if r['Kat'] == "Hisse" else f"{r['Kod']}-USD"
                    p = yf.Ticker(sym).history(period="1d")['Close'].iloc[-1]
                    prices.append(p)
                    advices.append(get_ai_advice(r))
                
                my_port['Güncel Fiyat'] = prices
                my_port['AI Tavsiyesi'] = advices
                my_port['Değer'] = my_port['Güncel Fiyat'] * my_port['Adet']
                my_port['K/Z'] = my_port['Değer'] - (my_port['Maliyet'] * my_port['Adet'])

            # Özet Kartları
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Varlık", f"₺{my_port['Değer'].sum():,.2f}")
            c2.metric("Net Kâr/Zarar", f"₺{my_port['K/Z'].sum():,.2f}")
            c3.metric("AI Sağlık Skoru", "Pekiyi" if my_port['K/Z'].sum() > 0 else "Gözlem Altında")

            # AI Rapor Kartı
            st.markdown(f"""
            <div class="ai-card">
                <h4>🤖 AI Strateji Raporu</h4>
                <p>Şu an portföyünüzdeki <b>{len(my_port)}</b> varlıktan 
                <b>{len(my_port[my_port['AI Tavsiyesi'].str.contains('🟢')])}</b> tanesi yükseliş trendinde.</p>
                <small>Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}</small>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📋 Detaylı Varlık Raporu")
            st.dataframe(my_port[["Kod", "Adet", "Maliyet", "Güncel Fiyat", "K/Z", "AI Tavsiyesi"]], use_container_width=True)
            
            # Dağılım Grafiği
            st.plotly_chart(go.Figure(data=[go.Pie(labels=my_port['Kod'], values=my_port['Değer'])]))

        else:
            st.info("Henüz varlık eklemediniz. 'PORTFÖYÜM' sekmesinden ekleme yapın.")

    # --- 2. OPTİMİZASYON (DETAYLI ANALİZ) ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ AI Portföy Optimizasyonu")
        # (Daha önceki detaylı optimizasyon kodun buraya gelecek)
        st.write("Varlıklarınızı ekledikten sonra Sharpe Oranı ve Risk analizleri burada görünür.")

    # --- 3. AYARLAR (GÖZÜKMÜYORDU, EKLENDİ) ---
    elif menu == "⚙️ AYARLAR":
        st.title("⚙️ Sistem Ayarları")
        st.subheader("Hesap Bilgileri")
        st.write(f"Kullanıcı: **{st.session_state.u_data['Name']}**")
        st.write(f"Yetki: **{st.session_state.u_data['Role']}**")
        
        with st.expander("🔐 Şifre Değiştir"):
            new_p = st.text_input("Yeni Şifre", type="password")
            if st.button("Güncelle"):
                u_df = pd.read_csv(USER_DB)
                u_df.loc[u_df['Username'] == st.session_state.u_data['Username'], 'Password'] = hashlib.sha256(str.encode(new_p)).hexdigest()
                u_df.to_csv(USER_DB, index=False)
                st.success("Şifre başarıyla güncellendi.")

    # --- Diğer Sekmeler (Piyasa Takibi, Portföyüm, Admin Paneli) ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Ekleme")
        with st.form("varlik_ekle"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Sembol (Örn: THYAO, BTC)").upper()
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            kat = c4.selectbox("Tür", ["Hisse", "Kripto"])
            if st.form_submit_button("Portföye Ekle"):
                new_data = pd.DataFrame([[st.session_state.u_data['Username'], k, m, a, kat]], columns=df_port.columns)
                pd.concat([pd.read_csv(PORT_DB), new_data]).to_csv(PORT_DB, index=False)
                st.success("Eklendi! Dashboard'u kontrol edin.")
                st.rerun()