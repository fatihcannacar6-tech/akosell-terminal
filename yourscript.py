import streamlit as st
import pandas as pd
import os
import hashlib
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

# --- 1. VERİ SİSTEMİ ---
USER_DB, PORT_DB = "users_final.csv", "portfolio_final.csv"

def init_db():
    if not os.path.exists(USER_DB):
        # Varsayılan Admin Hesabı: admin / admin123
        admin_pw = hashlib.sha256(str.encode("admin123")).hexdigest()
        df = pd.DataFrame([["admin", admin_pw, "AKOSELL", "Approved", "Admin"]], 
                          columns=["Username", "Password", "Name", "Status", "Role"])
        df.to_csv(USER_DB, index=False)
    if not os.path.exists(PORT_DB):
        pd.DataFrame(columns=["Owner", "Kod", "Kat", "Adet", "Maliyet"]).to_csv(PORT_DB, index=False)

init_db()

# --- 2. HIZLI VERİ ÇEKME ---
@st.cache_data(ttl=300)
def get_price(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d")
        return round(data['Close'].iloc[-1], 2) if not data.empty else 0
    except: return 0

# --- 3. PROFESYONEL BEYAZ UI ---
st.set_page_config(page_title="AKOSELL WMS", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #F8FAFC !important; border-right: 1px solid #E2E8F0; }
    
    /* Metrik Kartları */
    .m-label { color: #64748B; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .m-value { color: #1E293B; font-size: 32px; font-weight: 700; margin-bottom: 2px; }
    .m-delta { font-size: 14px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #F0FDF4; color: #10B981; display: inline-block; }
    
    /* Profil Alanı (Fotoğrafsız) */
    .user-box {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
        padding: 15px; text-align: center; margin-bottom: 25px;
    }
    .user-initial {
        width: 50px; height: 50px; background: #2563EB; color: white;
        display: flex; align-items: center; justify-content: center;
        border-radius: 50%; font-size: 20px; font-weight: 700; margin: 0 auto 10px auto;
    }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- 4. GİRİŞ VE TALEPLER ---
if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h1 style='text-align:center; color:#1E293B; margin-top:50px;'>AKOSELL</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["GİRİŞ", "KAYIT TALEBİ"])
        with t1:
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.button("Sisteme Giriş", use_container_width=True):
                users = pd.read_csv(USER_DB)
                hp = hashlib.sha256(str.encode(p)).hexdigest()
                user = users[(users['Username']==u) & (users['Password']==hp)]
                if not user.empty:
                    if user.iloc[0]['Status'] == "Approved":
                        st.session_state.logged_in = True
                        st.session_state.u_data = user.iloc[0].to_dict()
                        st.rerun()
                    else: st.warning("Erişim onayınız henüz verilmedi.")
                else: st.error("Bilgiler hatalı.")
        with t2:
            nu = st.text_input("Yeni Kullanıcı Adı")
            nn = st.text_input("Ad Soyad")
            np = st.text_input("Yeni Şifre", type="password")
            if st.button("Kayıt Ol", use_container_width=True):
                u_df = pd.read_csv(USER_DB)
                if nu in u_df['Username'].values: st.error("Bu kullanıcı adı alınmış.")
                else:
                    new_u = pd.DataFrame([[nu, hashlib.sha256(str.encode(np)).hexdigest(), nn, "Pending", "User"]], columns=u_df.columns)
                    pd.concat([u_df, new_u]).to_csv(USER_DB, index=False)
                    st.success("Talebiniz yöneticiye iletildi.")

else:
    # --- 5. SIDEBAR ---
    with st.sidebar:
        initial = st.session_state.u_data['Name'][0].upper()
        st.markdown(f"""
            <div class="user-box">
                <div class="user-initial">{initial}</div>
                <div style="font-weight:700; color:#1E293B;">{st.session_state.u_data['Name'].upper()}</div>
                <div style="color:#2563EB; font-size:10px; font-weight:700; margin-top:4px;">SİSTEM YÖNETİCİSİ</div>
            </div>
        """, unsafe_allow_html=True)
        
        m_items = ["📊 DASHBOARD", "💼 PORTFÖYÜM", "📈 ANALİZLER", "📅 TAKVİM", "📰 HABERLER", "⚙️ AYARLAR"]
        if st.session_state.u_data['Role'] == "Admin": m_items.append("🔐 YÖNETİCİ PANELİ")
        menu = st.radio("NAV", m_items, label_visibility="collapsed")
        
        st.markdown("<br>"*3, unsafe_allow_html=True)
        if st.button("ÇIKIŞ", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    p_df = pd.read_csv(PORT_DB)
    my_p = p_df[p_df['Owner'] == st.session_state.u_data['Username']]

    # --- 6. DASHBOARD (RESİMDEKİ ANALİZ DÜZENİ) ---
    if "DASHBOARD" in menu:
        st.markdown("<h2 style='color:#1E293B;'>📊 Stratejik Varlık Analizi</h2>", unsafe_allow_html=True)
        if not my_p.empty:
            prices, total_val = [], 0
            for _, r in my_p.iterrows():
                sym = f"{r['Kod']}.IS" if r['Kat'] == "Hisse" else f"{r['Kod']}-USD"
                p = get_price(sym)
                prices.append(p)
                total_val += (p * r['Adet'])
            
            total_cost = (my_p['Maliyet'] * my_p['Adet']).sum()
            profit = total_val - total_cost
            perc = (profit/total_cost*100) if total_cost > 0 else 0

            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='m-label'>TOPLAM YATIRIM</div><div class='m-value'>₺{total_cost:,.2f}</div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='m-label'>NET KÂR / ZARAR</div><div class='m-value'>₺{profit:,.2f}</div><div class='m-delta'>↑ {perc:,.2f}%</div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='m-label'>PORTFÖY DEĞERİ</div><div class='m-value'>₺{total_val:,.2f}</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            my_p['Güncel Fiyat'] = prices
            my_p['Kâr/Zarar'] = (my_p['Güncel Fiyat'] - my_p['Maliyet']) * my_p['Adet']
            st.dataframe(my_p.drop(columns=['Owner']), use_container_width=True, hide_index=True)
        else: st.info("Başlamak için Portföyüm sekmesinden varlık ekleyin.")

    # --- 7. ANALİZLER (RESİMDEKİ GRAFİKLER) ---
    elif "ANALİZLER" in menu:
        st.title("📈 Analiz")
        if not my_p.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig_pie = px.pie(my_p, values='Adet', names='Kod', hole=0.5, title="Varlık Dağılımı")
                fig_pie.update_layout(showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                fig_bar = px.bar(my_p, x='Kod', y='Adet', color='Kat', title="Kategori Kıyaslaması")
                st.plotly_chart(fig_bar, use_container_width=True)
        else: st.warning("Analiz edilecek veri yok.")

    # --- 8. YÖNETİCİ PANELİ (TALEP SİSTEMİ) ---
    elif "YÖNETİCİ PANELİ" in menu:
        st.title("🔐 Kayıt Talepleri")
        u_df = pd.read_csv(USER_DB)
        pending = u_df[u_df['Status'] == "Pending"]
        
        if not pending.empty:
            for i, r in pending.iterrows():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**{r['Name']}** (@{r['Username']})")
                if c2.button("✅ ONAYLA", key=f"ok_{r['Username']}"):
                    u_df.loc[u_df['Username'] == r['Username'], 'Status'] = "Approved"
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
                if c3.button("❌ REDDET", key=f"no_{r['Username']}"):
                    u_df = u_df[u_df['Username'] != r['Username']]
                    u_df.to_csv(USER_DB, index=False)
                    st.rerun()
        else: st.info("Bekleyen onay talebi bulunmuyor.")

    # --- 9. AYARLAR (SADE VE NET) ---
    elif "AYARLAR" in menu:
        st.title("⚙️ Ayarlar")
        u_df = pd.read_csv(USER_DB)
        
        with st.expander("👤 Kullanıcı Bilgilerini Güncelle"):
            new_un = st.text_input("Kullanıcı Adı Değiştir", value=st.session_state.u_data['Username'])
            new_pw = st.text_input("Yeni Şifre (Değiştirmek istemiyorsanız boş bırakın)", type="password")
            if st.button("Bilgileri Kaydet"):
                idx = u_df[u_df['Username'] == st.session_state.u_data['Username']].index
                u_df.loc[idx, 'Username'] = new_un
                if new_pw:
                    u_df.loc[idx, 'Password'] = hashlib.sha256(str.encode(new_pw)).hexdigest()
                u_df.to_csv(USER_DB, index=False)
                st.success("Bilgiler güncellendi, lütfen tekrar giriş yapın.")
                st.session_state.logged_in = False
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ TÜM VERİLERİ SIFIRLA", use_container_width=True):
            p_all = pd.read_csv(PORT_DB)
            p_all = p_all[p_all['Owner'] != st.session_state.u_data['Username']]
            p_all.to_csv(PORT_DB, index=False)
            st.warning("Varlık verileriniz tamamen temizlendi.")
            st.rerun()

    # --- PORTFÖYÜM ---
    elif "PORTFÖYÜM" in menu:
        st.title("💼 Varlık Yönetimi")
        with st.form("add_varlik"):
            c1, c2, c3, c4 = st.columns(4)
            k = c1.text_input("Varlık Kodu (Örn: THYAO, BTC)")
            kt = c2.selectbox("Kategori", ["Hisse", "Kripto"])
            a = c3.number_input("Adet", min_value=1)
            m = c4.number_input("Maliyet (Birim)")
            if st.form_submit_button("Portföye Ekle"):
                new_row = pd.DataFrame([[st.session_state.u_data['Username'], k.upper(), kt, a, m]], columns=p_df.columns)
                pd.concat([p_df, new_row]).to_csv(PORT_DB, index=False)
                st.success("Varlık listeye eklendi.")
                st.rerun()