import streamlit as st
import pandas as pd
from db_manager import Database, LEVELS

# Sayfa Ayarları (Telefonda uygulama gibi görünsün)
st.set_page_config(page_title="AyTech LifeOS", page_icon="⚡", layout="wide")

# Veritabanını Başlat
if 'db' not in st.session_state:
    st.session_state.db = Database()

db = st.session_state.db

# --- Kenar Çubuğu (Sidebar) ---
st.sidebar.title("⚡ Life Manager")
page = st.sidebar.radio("Menü", ["Dashboard", "Görevler", "Notlar", "Haftalık Rutin"])

# --- Helper Fonksiyonlar ---
def get_level_name(value):
    return {v: k for k, v in LEVELS.items()}.get(value, "Bilinmiyor")

# --- Sayfa: GÖREVLER ---
if page == "Görevler":
    st.header("📂 Görev Klasörleri")

    # Klasör Seçimi
    folders = db.get_folders('todo')
    folder_options = {f[1]: f[0] for f in folders} # {İsim: ID} sözlüğü
    
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_folder_name = st.selectbox("Klasör Seç:", list(folder_options.keys()) if folders else [])
    with col2:
        # Yeni Klasör Ekleme
        with st.popover("Yeni Klasör"):
            new_folder_name = st.text_input("Klasör Adı")
            if st.button("Oluştur"):
                db.add_folder(new_folder_name, 'todo')
                st.rerun()

    if selected_folder_name:
        folder_id = folder_options[selected_folder_name]
        
        # --- Hızlı Görev Ekleme (Input Lag Çözümü) ---
        st.divider()
        with st.form("new_task_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            task_txt = c1.text_input("Yeni Görev", placeholder="Aklındakini boşalt...")
            imp = c2.selectbox("Önem", list(LEVELS.keys()), index=2)
            eff = c3.selectbox("Çaba", list(LEVELS.keys()), index=1)
            submitted = c4.form_submit_button("Ekle 🚀")
            
            if submitted and task_txt:
                db.add_todo(folder_id, task_txt, LEVELS[imp], LEVELS[eff], "Genel")
                st.rerun()

        # --- Görev Listesi ---
        st.subheader("Yapılacaklar")
        todos = db.get_todos(folder_id, done_filter=0)
        
        if not todos:
            st.info("Her şey temiz! 🎉")
        
        for todo in todos:
            # todo: (id, folder_id, task, is_done, importance, effort, date, tag)
            tid, txt, imp, eff = todo[0], todo[2], todo[4], todo[5]
            
            # Kart Görünümü
            with st.container(border=True):
                c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                done = c1.checkbox("", key=f"check_{tid}", value=False)
                if done:
                    db.toggle_todo(tid, 0)
                    st.rerun()
                
                c2.markdown(f"**{txt}**")
                
                # Rozetler (Badge)
                imp_color = "red" if imp >= 4 else "orange" if imp == 3 else "green"
                c2.caption(f":{imp_color}[Önem: {get_level_name(imp)}] • Çaba: {get_level_name(eff)}")
                
                if c3.button("Sil", key=f"del_{tid}"):
                    db.delete_todo(tid)
                    st.rerun()

# --- Diğer Sayfalar (Şablon) ---
elif page == "Dashboard":
    st.title("📊 Genel Bakış")
    st.write("Buraya o 'Accordion' yapısını ve istatistikleri getireceğiz.")
    
    # Metrikler
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Görev", "42", "+5")
    col2.metric("Tamamlanan", "12", "28%")
    col3.metric("Kalan İş", "30", "-2")