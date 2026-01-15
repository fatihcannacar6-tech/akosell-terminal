import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import hashlib
import os
from datetime import datetime
import plotly.graph_objects as go
from scipy.optimize import minimize

# --- 1. VERİTABANI VE SİSTEM AYARLARI ---
# Sürüm çakışması olmaması için v16 olarak güncelledik
USER_DB, PORT_DB = "users_v16.csv", "portfolio_v16.csv"

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

# --- 2. MODERN BEYAZ ARAYÜZ (CSS) ---
st.set_page_config(page_title="AutoFlow AI Terminal", layout="wide", page_icon="🏛️")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #FBFBFE; }
    .ai-card { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #4F46E5; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stMetric { background: white !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #F1F5F9 !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
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
    df['Güncel'] = prices
    df['Değer'] = df['Güncel'] * df['Adet']
    df['Kâr/Zarar'] = df['Değer'] - (df['Maliyet'] * df['Adet'])
    return df

# --- 4. GİRİŞ PANELİ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
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
                else: st.warning("Hesabınız admin onayı bekliyor.")
            else: st.error("Hatalı bilgiler.")
    
    with tab2:
        new_u = st.text_input("Yeni Kullanıcı Adı").lower()
        new_n = st.text_input("Ad Soyad")
        new_p = st.text_input("Şifre", type="password")
        if st.button("KAYIT TALEBİ GÖNDER"):
            users = pd.read_csv(USER_DB)
            if new_u in users['Username'].values: st.error("Bu kullanıcı adı alınmış.")
            else:
                hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                new_user = pd.DataFrame([[new_u, hp, new_n, "User", "Pending"]], columns=users.columns)
                new_user.to_csv(USER_DB, mode='a', header=False, index=False)
                st.success("Talebiniz iletildi. Admin (fatihcan) onayı bekleniyor.")

else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        # Hata korumalı veri çekme (.get)
        u_name = st.session_state.u_data.get('Name', 'Kullanıcı')
        u_role = st.session_state.u_data.get('Role', 'User')
        
        st.markdown(f"### 🏛️ AKOSELL WMS\n**{u_name}**")
        nav = ["📊 DASHBOARD", "🔍 PİYASA TAKİBİ", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR"]
        if u_role == "Admin": nav.append("🔑 ADMIN PANELİ")
        
        menu = st.radio("MENÜ", nav)
        if st.button("Güvenli Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    # Ortak Veriler
    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data.get('Username')]

    # --- 6. DASHBOARD (DETAYLI RAPORLAR) ---
    if menu == "📊 DASHBOARD":
        st.title("📊 Portföy Detaylı Raporu")
        if not my_port.empty:
            with st.spinner("Veriler analiz ediliyor..."):
                proc_df = fetch_prices(my_port)
                total_val = proc_df['Değer'].sum()
                total_kz = proc_df['Kâr/Zarar'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Varlık", f"₺{total_val:,.2f}")
                c2.metric("Toplam Kâr/Zarar", f"₺{total_kz:,.2f}", delta=f"{(total_kz/(total_val-total_kz)*100):.2f}%" if (total_val-total_kz) != 0 else "0%")
                c3.metric("Aktif Varlık", f"{len(proc_df)} Kalem")

                st.markdown(f"""
                <div class="ai-card">
                    <h4>🤖 AI Strateji Notu</h4>
                    <p>Portföyünüzün sağlık durumu <b>%{(total_kz/total_val*100):.2f}</b> verimlilikle çalışıyor. 
                    En kârlı varlığınız: <b>{proc_df.loc[proc_df['Kâr/Zarar'].idxmax(), 'Kod']}</b>. 
                    Risk dağılımı için Optimizasyon sekmesini kontrol edin.</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader("📋 Güncel Pozisyon Raporu")
                st.dataframe(proc_df[["Kod", "Kat", "Adet", "Maliyet", "Güncel", "Kâr/Zarar"]], use_container_width=True, hide_index=True)
                st.plotly_chart(go.Figure(data=[go.Pie(labels=proc_df['Kod'], values=proc_df['Değer'], hole=.4)]))
        else: st.info("Raporlar için Portföyüm sekmesinden varlık ekleyin.")

    # --- 7. PİYASA TAKİBİ (ARAMA ÇUBUĞU) ---
    elif menu == "🔍 PİYASA TAKİBİ":
        st.title("🔍 Canlı Piyasa Takip")
        query = st.text_input("Sembol Ara (Örn: THYAO, BTC-USD, USDTRY=X)", "THYAO")
        symbol = f"{query}.IS" if len(query) <= 5 and "-" not in query and "=" not in query else query
        try:
            tk = yf.Ticker(symbol)
            hist = tk.history(period="1mo")
            if not hist.empty:
                c1, c2 = st.columns([1, 3])
                curr = hist['Close'].iloc[-1]
                diff = ((curr - hist['Close'].iloc[-2])/hist['Close'].iloc[-2])*100
                c1.metric(query.upper(), f"{curr:.2f}", f"{diff:.2f}%")
                st.line_chart(hist['Close'])
            else: st.error("Varlık bulunamadı.")
        except: st.error("Sembol hatası.")

    # --- 8. OPTİMİZASYON (DETAYLI ANALİZ) ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ AI Portföy Optimizasyonu")
        if len(my_port) >= 3:
            with st.spinner("Matematiksel modelleme yapılıyor..."):
                assets = my_port['Kod'].unique()
                data = pd.DataFrame()
                for a in assets:
                    tk = f"{a}.IS" if my_port[my_port['Kod']==a]['Kat'].values[0]=="Hisse" else f"{a}-USD"
                    data[a] = yf.Ticker(tk).history(period="1y")['Close']
                
                returns = data.pct_change().dropna()
                mean_ret = returns.mean() * 252
                cov_mat = returns.cov() * 252

                def get_stats(w):
                    p_ret = np.sum(mean_ret * w)
                    p_vol = np.sqrt(np.dot(w.T, np.dot(cov_mat, w)))
                    return p_ret, p_vol, (p_ret - 0.05) / p_vol # Sharpe

                res = minimize(lambda w: -get_stats(w)[2], [1./len(assets)]*len(assets), 
                               bounds=[(0,1)]*len(assets), constraints={'type':'eq','fun': lambda x: np.sum(x)-1})
                
                r, v, s = get_stats(res.x)
                st.markdown(f"""
                <div class="ai-card">
                    <h4>📊 Sharpe Oranı Optimizasyonu</h4>
                    <li>Beklenen Yıllık Getiri: <b>%{r*100:.2f}</b></li>
                    <li>Tahmini Risk (Volatilite): <b>%{v*100:.2f}</b></li>
                    <li>Verimlilik (Sharpe Skoru): <b>{s:.2f}</b></li>
                </div>
                """, unsafe_allow_html=True)
                
                st.plotly_chart(go.Figure(data=[go.Pie(labels=assets, values=res.x, hole=.3)]))
        else: st.warning("Analiz için en az 3 farklı varlık ekleyin.")

    # --- 9. ADMIN PANELİ (ONAY/RET) ---
    elif menu == "🔑 ADMIN PANELİ":
        st.title("🔑 Admin Kontrol Merkezi")
        u_df = pd.read_csv(USER_DB)
        pending = u_df[u_df['Status'] == "Pending"]
        
        if not pending.empty:
            st.subheader(f"Onay Bekleyen ({len(pending)}) Kullanıcı")
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
        else: st.info("Bekleyen onay talebi bulunmuyor.")
        
        st.divider()
        st.subheader("Tüm Kullanıcı Listesi")
        st.dataframe(u_df[["Username", "Name", "Role", "Status"]], use_container_width=True)

    # --- 10. PORTFÖYÜM ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Yönetimi")
        with st.form("add_v16"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Varlık Kodu (Örn: THYAO)").upper()
            a = c2.number_input("Adet", min_value=0.0)
            m = c3.number_input("Maliyet", min_value=0.0)
            cat = c4.selectbox("Tür", ["Hisse", "Kripto", "Altın", "Döviz"])
            if st.form_submit_button("Portföye Kaydet"):
                new = pd.DataFrame([[st.session_state.u_data.get('Username'), k, m, a, cat]], columns=df_port.columns)
                pd.concat([pd.read_csv(PORT_DB), new]).to_csv(PORT_DB, index=False)
                st.success(f"{k} Başarıyla eklendi!")
                st.rerun()
        
        st.divider()
        st.subheader("Mevcut Varlıklarım")
        edited = st.data_editor(my_port, num_rows="dynamic", use_container_width=True)
        if st.button("Değişiklikleri Kaydet"):
            others = df_port[df_port['Owner'] != st.session_state.u_data.get('Username')]
            pd.concat([others, edited]).to_csv(PORT_DB, index=False)
            st.success("Veritabanı güncellendi!")

    # --- 11. AYARLAR ---
    elif menu == "⚙️ AYARLAR":
        st.title("⚙️ Hesap Ayarları")
        st.write(f"Kullanıcı: **{u_name}** | Yetki: **{u_role}**")
        with st.expander("🔐 Şifre Değiştir"):
            new_p = st.text_input("Yeni Şifre", type="password")
            if st.button("Güncelle"):
                u_df = pd.read_csv(USER_DB)
                u_df.loc[u_df['Username'] == st.session_state.u_data.get('Username'), 'Password'] = hashlib.sha256(str.encode(new_p)).hexdigest()
                u_df.to_csv(USER_DB, index=False)
                st.success("Şifreniz güncellendi.")