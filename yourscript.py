import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# --- 1. KURUMSAL YAPILANDIRMA ---
st.set_page_config(page_title="AKOSELL WMS | Yönetim Terminali", layout="wide", page_icon="🏛️")

# Beyaz Tema CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #FFFFFF; color: #1E293B; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #F8FAFC !important; border-right: 1px solid #E2E8F0; }
    
    /* Kartlar */
    .metric-card {
        background: white; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 12px; font-weight: 600; color: #64748B; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: 700; color: #0F172A; margin-top: 5px; }
    
    /* Tablo Tasarımı */
    .stDataFrame { border-radius: 8px; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. VERİTABANI SİSTEMİ ---
DB_USERS = "wms_users.csv"
DB_PORTFOLIO = "wms_portfolio.csv"
DB_MARKET = "wms_market.csv"

def init_db():
    if not os.path.exists(DB_USERS):
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        pd.DataFrame([["admin", admin_pw, "Sistem Yöneticisi", "admin@akosell.com", "Approved", "Admin"]], 
                     columns=["Username", "Password", "Name", "Email", "Status", "Role"]).to_csv(DB_USERS, index=False)
    
    if not os.path.exists(DB_PORTFOLIO):
        pd.DataFrame(columns=["Owner", "Varlık", "Kategori", "Adet", "Maliyet"]).to_csv(DB_PORTFOLIO, index=False)
    
    if not os.path.exists(DB_MARKET):
        # Örnek piyasa verisi (Manuel takip için)
        pd.DataFrame([
            ["THYAO", 285.50, 1.2], ["EREGL", 42.10, -0.5], ["BTC", 1450000, 2.1], ["ALTIN", 2450, 0.3]
        ], columns=["Sembol", "Fiyat", "Değişim"]).to_csv(DB_MARKET, index=False)

init_db()

# --- 3. OTURUM KONTROLÜ ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    _, col, _ = st.columns([1, 0.8, 1])
    with col:
        st.markdown("<h2 style='text-align:center;'>AKOSELL <span style='font-weight:300'>WMS</span></h2>", unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Giriş Yap", "Kayıt Ol"])
        
        with tab_login:
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİRİŞ", use_container_width=True):
                users = pd.read_csv(DB_USERS)
                hp = hashlib.sha256(p.encode()).hexdigest()
                user_row = users[(users['Username']==u) & (users['Password']==hp)]
                if not user_row.empty:
                    if user_row.iloc[0]['Status'] == "Approved":
                        st.session_state.auth = True
                        st.session_state.u_data = user_row.iloc[0].to_dict()
                        st.rerun()
                    else: st.warning("Kaydınız onay bekliyor.")
                else: st.error("Hatalı bilgiler.")
        
        with tab_register:
            reg_u = st.text_input("Yeni Kullanıcı Adı")
            reg_n = st.text_input("Ad Soyad")
            reg_p = st.text_input("Şifre Belirle", type="password")
            if st.button("KAYIT TALEBİ GÖNDER", use_container_width=True):
                users = pd.read_csv(DB_USERS)
                if reg_u in users['Username'].values: st.error("Bu kullanıcı adı alınmış.")
                else:
                    new_user = pd.DataFrame([[reg_u, hashlib.sha256(reg_p.encode()).hexdigest(), reg_n, "", "Pending", "User"]], columns=users.columns)
                    pd.concat([users, new_user]).to_csv(DB_USERS, index=False)
                    st.success("Talebiniz iletildi. Admin onayı bekleniyor.")

else:
    # --- 4. SIDEBAR MENÜ ---
    with st.sidebar:
        st.markdown(f"### {st.session_state.u_data['Name']}\n`{st.session_state.u_data['Role']}`")
        st.divider()
        menu = st.radio("NAVİGASYON", ["📊 DASHBOARD", "💼 PORTFÖYÜM", "📈 PİYASA TAKİP", "📑 RAPORLAR", "⚙️ PROFİL AYARLARI", "🔐 ADMIN PANELİ" if st.session_state.u_data['Role'] == "Admin" else None])
        if st.button("GÜVENLİ ÇIKIŞ", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    # --- 5. DASHBOARD ---
    if menu == "📊 DASHBOARD":
        st.title("Yönetim Özeti")
        port = pd.read_csv(DB_PORTFOLIO)
        my_port = port[port['Owner'] == st.session_state.u_data['Username']]
        market = pd.read_csv(DB_MARKET)
        
        if not my_port.empty:
            # Basit Fiyat Eşleştirme
            merged = my_port.merge(market, left_on="Varlık", right_on="Sembol", how="left")
            merged['Fiyat'] = merged['Fiyat'].fillna(merged['Maliyet']) # Fiyat yoksa maliyet kullan
            merged['Güncel Değer'] = merged['Fiyat'] * merged['Adet']
            merged['K/Z'] = merged['Güncel Değer'] - (merged['Maliyet'] * merged['Adet'])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card"><div class="metric-label">Toplam Varlık</div><div class="metric-value">₺{merged["Güncel Değer"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="metric-label">Net K/Z</div><div class="metric-value">₺{merged["K/Z"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="metric-label">Varlık Sayısı</div><div class="metric-value">{len(my_port)}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card"><div class="metric-label">Portföy Sağlığı</div><div class="metric-value">STABİL</div></div>', unsafe_allow_html=True)
            
            st.divider()
            
            col_l, col_r = st.columns([2, 1])
            with col_l:
                st.subheader("Varlık Dağılımı")
                fig = px.pie(merged, values='Güncel Değer', names='Varlık', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                st.subheader("Performans")
                st.dataframe(merged[['Varlık', 'K/Z']], use_container_width=True, hide_index=True)
        else:
            st.info("Portföyünüz henüz boş.")

    # --- 6. PORTFÖYÜM ---
    elif menu == "💼 PORTFÖYÜM":
        st.title("Varlık Yönetimi")
        port = pd.read_csv(DB_PORTFOLIO)
        my_port = port[port['Owner'] == st.session_state.u_data['Username']]
        
        tab_add, tab_manage = st.tabs(["YENİ VARLIK", "DÜZENLE / SİL"])
        with tab_add:
            with st.form("add_form"):
                v = st.text_input("Varlık Kodu (Örn: THYAO, BTC)").upper()
                k = st.selectbox("Kategori", ["Hisse", "Kripto", "Emtia", "Döviz"])
                a = st.number_input("Adet", min_value=0.0)
                m = st.number_input("Birim Maliyet")
                if st.form_submit_button("KAYDET"):
                    new_data = pd.DataFrame([[st.session_state.u_data['Username'], v, k, a, m]], columns=port.columns)
                    pd.concat([port, new_data]).to_csv(DB_PORTFOLIO, index=False)
                    st.success("Kaydedildi."); st.rerun()
        
        with tab_manage:
            edited = st.data_editor(my_port.drop(columns=["Owner"]), use_container_width=True, num_rows="dynamic")
            if st.button("DEĞİŞİKLİKLERİ ONAYLA"):
                others = port[port['Owner'] != st.session_state.u_data['Username']]
                edited['Owner'] = st.session_state.u_data['Username']
                pd.concat([others, edited]).to_csv(DB_PORTFOLIO, index=False)
                st.rerun()

    # --- 7. PİYASA TAKİP ---
    elif menu == "📈 PİYASA TAKİP":
        st.title("Piyasa İzleme Listesi")
        market = pd.read_csv(DB_MARKET)
        
        if st.session_state.u_data['Role'] == "Admin":
            st.subheader("Veri Güncelle (Admin)")
            edited_market = st.data_editor(market, use_container_width=True, num_rows="dynamic")
            if st.button("FİYATLARI GÜNCELLE"):
                edited_market.to_csv(DB_MARKET, index=False); st.rerun()
        else:
            st.dataframe(market, use_container_width=True, hide_index=True)

    # --- 8. RAPORLAR ---
    elif menu == "📑 RAPORLAR":
        st.title("Finansal Raporlama")
        st.write("Mevcut portföy durumunuzu Excel veya CSV olarak dışa aktarabilirsiniz.")
        port = pd.read_csv(DB_PORTFOLIO)
        my_port = port[port['Owner'] == st.session_state.u_data['Username']]
        
        st.download_button("EXCEL OLARAK İNDİR (CSV)", my_port.to_csv(), "akosell_rapor.csv", "text/csv")
        st.markdown("""
        ### Rapor Özeti
        * Varlık çeşitliliği analizi
        * Maliyet bazlı performans dökümü
        * Dönemsel getiri projeksiyonu
        """)

    # --- 9. PROFİL AYARLARI (ŞİFRE DEĞİŞTİRME) ---
    elif menu == "⚙️ PROFİL AYARLARI":
        st.title("Güvenlik ve Profil")
        st.write(f"Kullanıcı: **{st.session_state.u_data['Username']}**")
        
        with st.form("pass_form"):
            new_name = st.text_input("Ad Soyad Güncelle", value=st.session_state.u_data['Name'])
            old_p = st.text_input("Mevcut Şifre", type="password")
            new_p = st.text_input("Yeni Şifre", type="password")
            if st.form_submit_button("BİLGİLERİ GÜNCELLE"):
                users = pd.read_csv(DB_USERS)
                idx = users[users['Username'] == st.session_state.u_data['Username']].index[0]
                
                if hashlib.sha256(old_p.encode()).hexdigest() == users.at[idx, 'Password']:
                    users.at[idx, 'Name'] = new_name
                    if new_p: users.at[idx, 'Password'] = hashlib.sha256(new_p.encode()).hexdigest()
                    users.to_csv(DB_USERS, index=False)
                    st.success("Başarıyla güncellendi.")
                else: st.error("Mevcut şifre hatalı.")

    # --- 10. ADMIN PANELİ (ONAY/RET) ---
    elif menu == "🔐 ADMIN PANELİ":
        st.title("Sistem Yönetimi")
        users = pd.read_csv(DB_USERS)
        
        st.subheader("Bekleyen Kayıt Talepleri")
        pending = users[users['Status'] == "Pending"]
        
        if not pending.empty:
            for i, row in pending.iterrows():
                c1, c2, c3 = st.columns([2,1,1])
                c1.write(f"**{row['Name']}** (@{row['Username']})")
                if c2.button("✅ ONAYLA", key=f"app_{i}"):
                    users.at[i, 'Status'] = "Approved"
                    users.to_csv(DB_USERS, index=False); st.rerun()
                if c3.button("❌ REDDET", key=f"rej_{i}"):
                    users = users.drop(i)
                    users.to_csv(DB_USERS, index=False); st.rerun()
        else:
            st.info("Onay bekleyen kullanıcı bulunmuyor.")
        
        st.divider()
        st.subheader("Sistemdeki Tüm Kullanıcılar")
        st.dataframe(users[['Username', 'Name', 'Status', 'Role']], use_container_width=True)