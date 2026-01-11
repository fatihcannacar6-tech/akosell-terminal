import streamlit as st
import pandas as pd
import os
import hashlib
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import feedparser
from datetime import datetime

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="AKOSELL WMS", layout="wide", page_icon="🏛️")

# --- 2. CSS TASARIM (KURUMSAL TEMA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .user-profile { padding: 20px; background: #F8FAFC; border-radius: 12px; margin: 10px 15px 25px 15px; border: 1px solid #E2E8F0; text-align: center; }
    [data-testid="stSidebarNav"] { display: none; }
    .stRadio div[role="radiogroup"] { gap: 8px !important; padding: 0 15px !important; }
    .stRadio div[role="radiogroup"] label { background-color: #F1F5F9 !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; padding: 12px 16px !important; width: 100% !important; display: flex !important; align-items: center !important; transition: all 0.2s ease; cursor: pointer; }
    .stRadio div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { color: #1E293B !important; font-size: 14px !important; font-weight: 700 !important; margin: 0 !important; }
    .stRadio div[role="radiogroup"] label[data-checked="true"] { background-color: #00D1FF !important; border-color: #00D1FF !important; }
    .stRadio div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }
    .sidebar-footer { position: fixed; bottom: 20px; width: 270px; padding: 0 15px; }
    .analysis-card { background: white; padding: 20px; border-radius: 15px; border-left: 5px solid #00D1FF; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. VERİ SİSTEMİ ---
USER_DB, PORT_DB = "users_v13.csv", "portfolio_v13.csv"

def init_db():
    if not os.path.exists(USER_DB):
        admin_pw = hashlib.sha256(str.encode("admin123")).hexdigest()
        df = pd.DataFrame([["admin", admin_pw, "Admin", "admin@akosell.com", "Approved", "Admin"]], 
                          columns=["Username", "Password", "Name", "Email", "Status", "Role"])
        df.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "YF_Kod", "Maliyet", "Adet", "Kat"]).to_csv(PORT_DB, index=False)

init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- 4. GİRİŞ VE KAYIT PANELİ ---
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown("<br><h1 style='text-align:center;'>AKOSELL WMS</h1>", unsafe_allow_html=True)
        t_log, t_reg = st.tabs(["GİRİŞ", "KAYIT OL"])
        
        with t_log:
            u = st.text_input("Kullanıcı")
            p = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİR", use_container_width=True, type="primary"):
                users = pd.read_csv(USER_DB)
                hp = hashlib.sha256(str.encode(p)).hexdigest()
                match = users[(users['Username']==u) & (users['Password']==hp)]
                if not match.empty:
                    if match.iloc[0]['Status'] == "Approved":
                        st.session_state.logged_in = True
                        st.session_state.u_data = match.iloc[0].to_dict()
                        st.rerun()
                    else: st.error("Hesabınız onay bekliyor.")
                else: st.error("Hatalı bilgiler.")
        
        with t_reg:
            nu, nn, ne, npw = st.text_input("Kullanıcı Adı"), st.text_input("Ad Soyad"), st.text_input("E-posta"), st.text_input("Şifre", type="password")
            if st.button("KAYIT OL", use_container_width=True):
                users = pd.read_csv(USER_DB)
                if nu in users['Username'].values: st.warning("Bu kullanıcı adı alınmış.")
                else:
                    new_u = pd.DataFrame([[nu, hashlib.sha256(str.encode(npw)).hexdigest(), nn, ne, "Pending", "User"]], columns=users.columns)
                    pd.concat([users, new_u]).to_csv(USER_DB, index=False)
                    st.success("Kayıt talebi gönderildi. Admin onayı bekleniyor.")

else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        role_tag = "SİSTEM YÖNETİCİSİ" if st.session_state.u_data['Role'] == "Admin" else "YATIRIMCI"
        st.markdown(f"""<div class="user-profile"><small style="color:#64748B;">{role_tag}</small><div style="font-size:18px; font-weight:800; color:#1E293B;">{st.session_state.u_data['Name'].upper()}</div><div style="color:#00D1FF; font-size:11px; font-weight:700;">PREMIUM PLUS</div></div>""", unsafe_allow_html=True)
        menu_items = ["📊 DASHBOARD", "💼 PORTFÖYÜM", "📈 ANALİZLER", "📅 TAKVİM", "📰 HABERLER", "⚙️ AYARLAR"]
        if st.session_state.u_data['Role'] == "Admin": menu_items.append("🔐 ADMIN PANELİ")
        menu = st.radio("NAV", menu_items, label_visibility="collapsed")
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if st.button("ÇIKIŞ", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    df_port = pd.read_csv(PORT_DB)
    my_port = df_port[df_port['Owner'] == st.session_state.u_data['Username']]

    # --- 6. DASHBOARD ---
    if "DASHBOARD" in menu:
        st.title("📊 Stratejik Varlık Analizi")
        if not my_port.empty:
            with st.spinner('Piyasa verileri alınıyor...'):
                prices = []
                for _, r in my_port.iterrows():
                    sym = f"{r['Kod']}.IS" if r['Kat'] == "Hisse" else f"{r['Kod']}-USD"
                    try: prices.append(yf.Ticker(sym).history(period="1d")['Close'].iloc[-1])
                    except: prices.append(r['Maliyet'])
                my_port['Güncel'] = prices
                t_cost = (my_port['Maliyet'] * my_port['Adet']).sum()
                t_val = (my_port['Güncel'] * my_port['Adet']).sum()
                t_profit = t_val - t_cost

            c1, c2, c3 = st.columns(3)
            c1.metric("TOPLAM YATIRIM", f"₺{t_cost:,.2f}")
            c2.metric("NET KÂR / ZARAR", f"₺{t_profit:,.2f}", delta=f"{(t_profit/t_cost*100) if t_cost > 0 else 0:.2f}%")
            c3.metric("PORTFÖY DEĞERİ", f"₺{t_val:,.2f}")
            
            st.subheader("📈 Hızlı Grafik")
            sel_s = st.selectbox("Varlık Seç", my_port['Kod'].unique())
            sym_s = f"{sel_s}.IS" if my_port[my_port['Kod']==sel_s]['Kat'].iloc[0] == "Hisse" else f"{sel_s}-USD"
            h_data = yf.Ticker(sym_s).history(period="1mo")
            fig = go.Figure(data=[go.Candlestick(x=h_data.index, open=h_data['Open'], high=h_data['High'], low=h_data['Low'], close=h_data['Close'])])
            fig.update_layout(template="plotly_white", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Portföy boş.")

    # --- 7. ANALİZLER ---
    elif "ANALİZLER" in menu:
        st.title("📈 Portföy Analitiği")
        if not my_port.empty:
            my_port['Toplam Değer'] = my_port['Adet'] * my_port['Maliyet'] # Örnek hesaplama
            col1, col2 = st.columns(2)
            with col1:
                fig_pie = px.pie(my_port, values='Adet', names='Kod', hole=0.4, title="Varlık Dağılımı")
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                fig_bar = px.bar(my_port, x='Kod', y='Adet', color='Kat', title="Kategori Bazlı Dağılım")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            
        else: st.warning("Veri bulunamadı.")

    # --- 8. TAKVİM ---
    elif "TAKVİM" in menu:
        st.title("📅 Finansal Takvim")
        evs = [{"Tarih": "15 Ocak", "Olay": "Enflasyon Verisi", "Etki": "Kritik 🔥"}, 
               {"Tarih": "22 Ocak", "Olay": "Faiz Kararı", "Etki": "Yüksek 🚀"}]
        st.table(evs)

    # --- 9. HABERLER ---
    elif "HABERLER" in menu:
        st.title("📰 Canlı Haberler")
        feed = feedparser.parse("https://www.haberturk.com/rss/kategori/ekonomi.xml")
        for entry in feed.entries[:8]:
            with st.expander(entry.title):
                st.write(entry.published)
                st.markdown(f"[Habere Git]({entry.link})")

    # --- 10. ADMIN PANELİ ---
    elif "ADMIN PANELİ" in menu:
        st.title("🔐 Onay Sistemi")
        u_df = pd.read_csv(USER_DB)
        pend = u_df[u_df['Status'] == "Pending"]
        if not pend.empty:
            for i, r in pend.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['Name']}** (@{r['Username']})")
                if c2.button("ONAYLA", key=r['Username']):
                    u_df.loc[u_df['Username'] == r['Username'], 'Status'] = "Approved"
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
        else: st.write("Bekleyen yok.")

    # --- 11. PORTFÖYÜM ---
    elif "PORTFÖYÜM" in menu:
        st.title("💼 Portföy Yönetimi")
        t1, t2 = st.tabs(["EKLE", "YÖNET"])
        with t1:
            with st.form("add"):
                c1, c2, c3 = st.columns(3)
                k = c1.text_input("Kod").upper()
                m = c2.number_input("Maliyet")
                a = c3.number_input("Adet")
                cat = st.selectbox("Tür", ["Hisse", "Kripto", "Altın"])
                if st.form_submit_button("KAYDET"):
                    new = pd.DataFrame([[st.session_state.u_data['Username'], k, k, m, a, cat]], columns=df_port.columns)
                    pd.concat([df_port, new]).to_csv(PORT_DB, index=False)
                    st.rerun()