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
import io

# --- 1. VERİTABANI SİSTEMİ ---
USER_DB, PORT_DB = "users_v17.csv", "portfolio_v17.csv"

def init_db():
    if not os.path.exists(USER_DB):
        hp = hashlib.sha256(str.encode("8826244")).hexdigest()
        users = pd.DataFrame([["fatihcan", hp, "Fatih Can", "Admin", "Active"]], 
                             columns=["Username", "Password", "Name", "Role", "Status"])
        users.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. MODER VE MOBİL UYUMLU ARAYÜZ ---
st.set_page_config(page_title="AutoFlow Terminal", layout="wide", page_icon="🏛️")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #F8FAFC; }
    
    .login-box {
        max-width: 420px;
        margin: auto;
        padding: 30px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    
    .stMetric { background: white !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #F1F5F9 !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    div.stButton > button { width: 100% !important; border-radius: 10px; height: 45px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. YARDIMCI FONKSİYONLAR ---
def tr_fix(text):
    chars = {"İ": "I", "ı": "i", "Ş": "S", "ş": "s", "Ğ": "G", "ğ": "g", "Ü": "U", "ü": "u", "Ö": "O", "ö": "o", "Ç": "C", "ç": "c"}
    for tr, eng in chars.items():
        text = text.replace(tr, eng)
    return text

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
    df['Maliyet_Toplami'] = df['Maliyet'] * df['Adet'] # Dashboard için eklendi
    df['Kâr/Zarar'] = df['Değer'] - df['Maliyet_Toplami']
    return df

# --- 4. GİRİŞ VE KAYIT PANELİ ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.write("##") 
    _, col_mid, _ = st.columns([1, 1.2, 1])
    with col_mid:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>AutoFlow</h2>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
        with tab1:
            u = st.text_input("Kullanıcı Adı", key="login_u")
            p = st.text_input("Şifre", type="password", key="login_p")
            if st.button("GİRİŞ YAP", type="primary"):
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
            new_u = st.text_input("Kullanıcı Adı Belirle", key="reg_u").lower()
            new_n = st.text_input("Ad Soyad", key="reg_n")
            new_p = st.text_input("Yeni Şifre Oluştur", type="password", key="reg_p")
            if st.button("KAYIT TALEBİ GÖNDER"):
                users = pd.read_csv(USER_DB)
                if new_u in users['Username'].values: st.error("Kullanıcı adı mevcut.")
                else:
                    hp = hashlib.sha256(str.encode(new_p)).hexdigest()
                    new_user = pd.DataFrame([[new_u, hp, new_n, "User", "Pending"]], columns=users.columns)
                    new_user.to_csv(USER_DB, mode='a', header=False, index=False)
                    st.success("Talep gönderildi.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        u_name = st.session_state.u_data.get('Name', 'Kullanıcı')
        u_role = st.session_state.u_data.get('Role', 'User')
        st.markdown(f"### AutoFlow\n**{u_name}**")
        nav = ["📊 DASHBOARD", "⚖️ OPTİMİZASYON", "💼 PORTFÖYÜM", "⚙️ AYARLAR"]
        if u_role == "Admin": nav.append("🔑 ADMIN PANELİ")
        menu = st.radio("MENÜ", nav)
        if st.button("Güvenli Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data.get('Username')]

     # --- 7. DASHBOARD ---
    if "DASHBOARD" in menu:
        st.title("📊 DASHBOARD")
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

    # --- 7. AI OPTİMİZASYON & PDF RAPORU ---
    elif menu == "⚖️ OPTİMİZASYON":
        st.title("⚖️ AI Risk & Optimizasyon Analizi")
        if len(my_port) >= 2:
            assets = my_port['Kod'].unique()
            data = pd.DataFrame()
            analysis_results = []
            with st.spinner("AI Analiz yapıyor..."):
                for a in assets:
                    tk = f"{a}.IS" if my_port[my_port['Kod']==a]['Kat'].values[0]=="Hisse" else f"{a}-USD"
                    hist = yf.Ticker(tk).history(period="1y")['Close']
                    data[a] = hist
                    vol = hist.pct_change().std() * np.sqrt(252) * 100
                    ma20 = hist.rolling(20).mean().iloc[-1]
                    last = hist.iloc[-1]
                    risk_cat = "Düşük" if vol < 25 else ("Orta" if vol < 45 else "Yüksek")
                    
                    # GÜNCELLEME: Renkli Sinyaller
                    if last > ma20:
                        signal = "🟢 AL / TUT"
                    else:
                        signal = "🔴 SAT / İZLE"
                        
                    analysis_results.append({"Varlık": a, "Risk (%)": f"{vol:.2f}", "Risk Seviyesi": risk_cat, "Sinyal": signal})

            res_df = pd.DataFrame(analysis_results)
            st.subheader("📋 Hisse Bazlı AI Sinyalleri")
            st.table(res_df) # Renkleri doğrudan tablo içinde gösterir

            def export_pdf(df):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(190, 10, tr_fix("AutoFlow AI Analiz Raporu"), ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(40, 10, tr_fix("Varlik"), 1)
                pdf.cell(40, 10, tr_fix("Risk %"), 1)
                pdf.cell(50, 10, tr_fix("Risk Seviyesi"), 1)
                pdf.cell(60, 10, tr_fix("Sinyal"), 1)
                pdf.ln()
                pdf.set_font("Arial", '', 12)
                for i, row in df.iterrows():
                    pdf.cell(40, 10, tr_fix(str(row['Varlık'])), 1)
                    pdf.cell(40, 10, tr_fix(str(row['Risk (%)'])), 1)
                    pdf.cell(50, 10, tr_fix(str(row['Risk Seviyesi'])), 1)
                    pdf.cell(60, 10, tr_fix(str(row['Sinyal'])), 1)
                    pdf.ln()
                return pdf.output(dest='S').encode('latin-1', 'ignore')

            try:
                pdf_bytes = export_pdf(res_df)
                st.download_button("📄 ANALİZ RAPORUNU PDF İNDİR", data=pdf_bytes, file_name="AI_Analiz.pdf", mime="application/pdf")
            except:
                st.error("PDF oluşturulurken bir hata oluştu.")

            st.divider()
            st.subheader("🎯 İdeal Portföy Dağılımı")
            returns = data.pct_change().dropna()
            def get_vol(w): return np.sqrt(np.dot(w.T, np.dot(returns.cov() * 252, w)))
            res = minimize(get_vol, [1./len(assets)]*len(assets), bounds=[(0,1)]*len(assets), constraints={'type':'eq','fun': lambda x: np.sum(x)-1})
            st.plotly_chart(go.Figure(data=[go.Pie(labels=assets, values=res.x, hole=.3)]))
        else: st.warning("En az 2 farklı varlık ekleyin.")

    # --- 8. ADMIN PANELİ ---
    elif menu == "🔑 ADMIN PANELİ":
        st.title("🔑 Admin Onay Sistemi")
        u_df = pd.read_csv(USER_DB)
        pending = u_df[u_df['Status'] == "Pending"]
        if not pending.empty:
            for i, row in pending.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{row['Name']}** (@{row['Username']})")
                if col2.button("✅ ONAYLA", key=f"ok_{row['Username']}"):
                    u_df.loc[u_df['Username'] == row['Username'], 'Status'] = "Active"
                    u_df.to_csv(USER_DB, index=False); st.rerun()
                if col3.button("❌ REDDET", key=f"no_{row['Username']}"):
                    u_df = u_df[u_df['Username'] != row['Username']]
                    u_df.to_csv(USER_DB, index=False); st.rerun()
        else: st.info("Bekleyen onay yok.")

    # --- 9. PORTFÖYÜM ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("💼 Varlık Yönetimi")
        with st.expander("➕ Yeni Varlık Ekle", expanded=False):
            with st.form("add_asset"):
                c1, c2, c3, c4 = st.columns(4)
                k = c1.text_input("Sembol (Örn: THYAO)").upper()
                a = c2.number_input("Adet", min_value=0.0)
                m = c3.number_input("Maliyet", min_value=0.0)
                cat = c4.selectbox("Tür", ["Hisse", "Kripto", "Altın"])
                if st.form_submit_button("Sisteme Kaydet"):
                    new = pd.DataFrame([[st.session_state.u_data.get('Username'), k, m, a, cat]], columns=df_port.columns)
                    pd.concat([pd.read_csv(PORT_DB), new]).to_csv(PORT_DB, index=False)
                    st.rerun()

        st.divider()
        st.subheader("📝 Mevcut Varlıkları Düzenle")
        if not my_port.empty:
            with st.form("edit_portfolio"):
                updated_rows = []
                for idx, row in my_port.iterrows():
                    col_k, col_a, col_m, col_t, col_s = st.columns([1.5, 2, 2, 1.5, 1])
                    col_k.markdown(f"**{row['Kod']}**")
                    col_t.write(row['Kat'])
                    new_adet = col_a.number_input("Adet", value=float(row['Adet']), key=f"adet_{idx}")
                    new_maliyet = col_m.number_input("Maliyet", value=float(row['Maliyet']), key=f"mal_{idx}")
                    to_delete = col_s.checkbox("Sil", key=f"del_{idx}")
                    if not to_delete:
                        updated_rows.append({"Owner": row['Owner'], "Kod": row['Kod'], "Maliyet": new_maliyet, "Adet": new_adet, "Kat": row['Kat']})

                if st.form_submit_button("💾 TÜM DEĞİŞİKLİKLERİ KAYDET", type="primary"):
                    full_df = pd.read_csv(PORT_DB)
                    others_df = full_df[full_df['Owner'] != st.session_state.u_data.get('Username')]
                    new_mine_df = pd.DataFrame(updated_rows)
                    pd.concat([others_df, new_mine_df]).to_csv(PORT_DB, index=False)
                    st.success("Güncellendi!")
                    st.rerun()
        else: st.info("Portföy boş.")

    # --- 10. AYARLAR ---
    elif menu == "⚙️ AYARLAR":
        st.title("⚙️ Hesap Ayarları")
        with st.expander("Şifre Değiştir"):
            new_p = st.text_input("Yeni Şifre", type="password")
            if st.button("Güncelle"):
                u_df = pd.read_csv(USER_DB)
                u_df.loc[u_df['Username'] == st.session_state.u_data.get('Username'), 'Password'] = hashlib.sha256(str.encode(new_p)).hexdigest()
                u_df.to_csv(USER_DB, index=False); st.success("Şifre güncellendi.")