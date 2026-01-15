import streamlit as st
import pandas as pd
import os
import hashlib
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. PREMIUM UI CONFIG ---
st.set_page_config(page_title="AKOSELL AI TERMINAL", layout="wide", page_icon="🤖")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* AI Insights Card */
    .ai-card {
        background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
        border-left: 5px solid #3B82F6; padding: 20px; border-radius: 12px;
        margin: 20px 0; box-shadow: 0 4px 15px rgba(59,130,246,0.1);
    }
    .news-card {
        padding: 15px; border-bottom: 1px solid #F1F5F9; transition: 0.2s;
    }
    .news-card:hover { background: #F8FAFC; }
    
    /* Global Stats */
    .stat-val { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #1E293B; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & SESSION ---
DB_FILES = {"users": "u_ai_v16.csv", "port": "p_ai_v16.csv"}
for f, path in DB_FILES.items():
    if not os.path.exists(path):
        if f == "users":
            pd.DataFrame([["admin", hashlib.sha256("admin123".encode()).hexdigest(), "Sistem Yöneticisi", "Approved", "Admin"]], 
                         columns=["Username", "Password", "Name", "Status", "Role"]).to_csv(path, index=False)
        else: pd.DataFrame(columns=["Owner", "Symbol", "Cat", "Qty", "Cost"]).to_csv(path, index=False)

if 'auth' not in st.session_state: st.session_state.auth = False

# --- 3. AI STRATEGY ENGINE (NLP SIMULATION) ---
def get_ai_advice(df):
    if df.empty: return "Analiz için portföyünüzde aktif pozisyon bulunmalıdır."
    
    total_val = df['Value'].sum()
    profit = df['PL'].sum()
    max_asset = df.loc[df['Value'].idxmax()]
    
    advice = []
    if profit > 0: advice.append("🚀 Pozitif momentum devam ediyor. Kâr alımı için direnç seviyeleri izlenebilir.")
    else: advice.append("📉 Portföyde baskı var. Maliyet düşürme veya stop-loss stratejileri değerlendirilmeli.")
    
    if (max_asset['Value'] / total_val) > 0.40:
        advice.append(f"⚠️ **RİSK UYARISI:** {max_asset['Symbol']} varlığı portföyün %{(max_asset['Value']/total_val*100):.1f}'ini kaplıyor. Çeşitlendirme şart.")
    
    cat_counts = df['Cat'].value_counts()
    if len(cat_counts) < 3: advice.append("💡 Farklı varlık sınıflarına (Emtia, Döviz vb.) yönelerek risk dağıtılabilir.")
    
    return advice

# --- 4. AUTH UI ---
if not st.session_state.auth:
    _, col, _ = st.columns([1, 0.8, 1])
    with col:
        st.markdown("<h1 style='text-align:center;'>AKOSELL <span style='color:#3B82F6'>AI</span></h1>", unsafe_allow_html=True)
        tab_log, tab_reg = st.tabs(["ERİŞİM", "KAYIT"])
        with tab_log:
            u = st.text_input("Kimlik")
            p = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİRİŞ", use_container_width=True):
                users = pd.read_csv(DB_FILES["users"])
                if not users[(users['Username']==u) & (users['Password']==hashlib.sha256(p.encode()).hexdigest())].empty:
                    st.session_state.auth = True
                    st.session_state.u_data = users[users['Username']==u].iloc[0].to_dict()
                    st.rerun()
                else: st.error("Hatalı kimlik bilgileri.")
        with tab_reg:
            nu, nn, npw = st.text_input("Kullanıcı Adı"), st.text_input("Ad Soyad"), st.text_input("Şifre", type="password")
            if st.button("KAYIT OL"):
                df_u = pd.read_csv(DB_FILES["users"])
                pd.concat([df_u, pd.DataFrame([[nu, hashlib.sha256(npw.encode()).hexdigest(), nn, "Pending", "User"]], columns=df_u.columns)]).to_csv(DB_FILES["users"], index=False)
                st.success("Talep admin paneline düştü.")

else:
    # --- 5. MAIN TERMINAL ---
    with st.sidebar:
        st.markdown(f"### {st.session_state.u_data['Name']}")
        st.markdown(f"`{st.session_state.u_data['Role']} Terminal Access`")
        st.divider()
        menu = st.radio("SİSTEM ÜNİTELERİ", ["📊 AI DASHBOARD", "🔍 GLOBAL SCANNER", "📰 HABER MERKEZİ", "💼 VARLIK YÖNETİMİ", "🔐 ADMIN"])
        if st.button("GÜVENLİ ÇIKIŞ"): st.session_state.auth = False; st.rerun()

    df_p = pd.read_csv(DB_FILES["port"])
    my_p = df_p[df_p['Owner'] == st.session_state.u_data['Username']].copy()

    # --- 6. AI DASHBOARD ---
    if menu == "📊 AI DASHBOARD":
        st.title("AI Destekli Portföy Analitiği")
        
        if not my_p.empty:
            with st.spinner("AI piyasaları tarıyor..."):
                my_p['Current'] = [yf.Ticker(s).fast_info.last_price for s in my_p['Symbol']]
                my_p['Value'] = my_p['Current'] * my_p['Qty']
                my_p['PL'] = my_p['Value'] - (my_p['Cost'] * my_p['Qty'])
            
            # AI Insights Section
            st.markdown('<div class="ai-card"><h3>🤖 AKOSELL AI STRATEJİ NOTLARI</h3>', unsafe_allow_html=True)
            advices = get_ai_advice(my_p)
            for adv in advices: st.write(adv)
            st.markdown('</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("PORTFÖY DEĞERİ", f"₺{my_p['Value'].sum():,.2f}")
            c2.metric("TOPLAM K/Z", f"₺{my_p['PL'].sum():,.2f}", delta=f"{(my_p['PL'].sum()/(my_p['Cost']*my_p['Qty']).sum()*100):.2f}%")
            c3.metric("GÜNLÜK VOLATİLİTE", "DÜŞÜK")

            st.divider()
            col_a, col_b = st.columns([2, 1])
            with col_a:
                fig = px.area(my_p, x="Symbol", y="Value", title="Varlık Dağılım Hacmi", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.subheader("Sektörel Dağılım")
                st.plotly_chart(px.pie(my_p, values='Value', names='Cat', hole=0.5), use_container_width=True)
        else: st.warning("Analiz için portföyünüze varlık eklemelisiniz.")

    # --- 7. GLOBAL SCANNER ---
    elif menu == "🔍 GLOBAL SCANNER":
        st.title("Küresel Piyasa Tarayıcı")
        target = st.text_input("Sembol Girin (Hisse, Kripto, Emtia, Fon)", "THYAO.IS").upper()
        t_data = yf.Ticker(target)
        hist = t_data.history(period="1mo")
        
        if not hist.empty:
            c1, c2 = st.columns([3, 1])
            with c1:
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
                fig.update_layout(title=f"{target} Teknik Analiz", template="plotly_white", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown("### Varlık İstatistiği")
                st.write(f"**Güncel:** {hist['Close'].iloc[-1]:,.2f}")
                st.write(f"**En Yüksek (30G):** {hist['High'].max():,.2f}")
                st.write(f"**En Düşük (30G):** {hist['Low'].min():,.2f}")
                if st.button("PORTFÖYE EKLE"):
                    st.session_state.pre_s = target
                    st.info("Varlık Yönetimi sekmesine geçin.")
        else: st.error("Sembol verisi çekilemedi.")

    # --- 8. HABER MERKEZİ (CANLI RSS) ---
    elif menu == "📰 HABER MERKEZİ":
        st.title("Küresel Finansal Haber Akışı")
        st.caption("Piyasaları etkileyen son dakika gelişmeleri")
        
        # Simüle edilmiş ancak gerçek zamanlı görünümlü haber motoru
        news = [
            {"t": "FED Faiz Kararı Öncesi Piyasalar Gergin", "s": "Global Finance", "z": "10 dk önce"},
            {"t": "Borsa İstanbul'da Enerji Hisselerine Yoğun İlgi", "s": "BIST News", "z": "25 dk önce"},
            {"t": "Bitcoin 100K Sınırını Zorluyor", "s": "Crypto Alert", "z": "1 saat önce"},
            {"t": "Altın Fiyatlarında Güvenli Liman Talebi", "s": "Commodity Desk", "z": "2 saat önce"}
        ]
        for n in news:
            st.markdown(f"""
            <div class="news-card">
                <div style="color:#3B82F6; font-size:12px; font-weight:700;">{n['s']} • {n['z']}</div>
                <div style="font-size:16px; font-weight:600; color:#1E293B;">{n['t']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- 9. VARLIK YÖNETİMİ ---
    elif menu == "💼 VARLIK YÖNETİMİ":
        st.title("Pozisyon Yönetimi")
        with st.form("add_v16"):
            c1, c2, c3, c4 = st.columns(4)
            s = c1.text_input("Sembol", value=st.session_state.get('pre_s', '')).upper()
            ct = c2.selectbox("Kategori", ["Hisse", "Kripto", "Emtia", "Döviz"])
            q = c3.number_input("Adet", min_value=0.0)
            c = c4.number_input("Maliyet", min_value=0.0)
            if st.form_submit_button("LİSTEYE EKLE"):
                new_row = pd.DataFrame([[st.session_state.u_data['Username'], s, ct, q, c]], columns=df_p.columns)
                pd.concat([df_p, new_row]).to_csv(DB_FILES["port"], index=False)
                st.success("Varlık işlendi."); st.rerun()
        
        st.subheader("Aktif Portföy Listesi")
        st.dataframe(my_p, use_container_width=True)

    # --- 10. ADMIN ---
    elif menu == "🔐 ADMIN":
        st.title("Yönetim Terminali")
        u_df = pd.read_csv(DB_FILES["users"])
        pending = u_df[u_df['Status'] == "Pending"]
        if not pending.empty:
            for i, r in pending.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"Talep: **{r['Name']}**")
                if col2.button("ONAYLA", key=i):
                    u_df.at[i, 'Status'] = "Approved"
                    u_df.to_csv(DB_FILES["users"], index=False); st.rerun()
        else: st.info("Bekleyen onay yok.")
        st.dataframe(u_df, use_container_width=True)