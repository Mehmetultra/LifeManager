import streamlit as st
from db_manager import Database, LEVELS, LEVELS_REV

# --- YAPILANDIRMA ---
st.set_page_config(page_title="LifeManager V8 Ultimate", page_icon="⚡", layout="wide")

# CSS ile senin koyu tema renklerine ve etiketlerine benzer stiller
st.markdown("""
<style>
    .stExpander { border: 1px solid #333; border-radius: 5px; }
    .badge { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; color: white; margin-right: 5px;}
    .imp-5 { background-color: #c0392b; } /* Çok Yüksek */
    .imp-4 { background-color: #e67e22; } /* Yüksek */
    .imp-3 { background-color: #f1c40f; color: black !important; } /* Orta */
    .imp-2 { background-color: #2ecc71; } /* Düşük */
    .imp-1 { background-color: #27ae60; } /* Çok Düşük */
</style>
""", unsafe_allow_html=True)

if 'db' not in st.session_state:
    st.session_state.db = Database()
db = st.session_state.db

# --- SIDEBAR (SOL PANEL) - FİLTRELEME & NAVİGASYON ---
with st.sidebar:
    st.title("⚡ Life Manager")
    page = st.radio("Menü", ["Dashboard", "Görev Yönetimi", "Notlar", "Haftalık Rutin"])
    
    st.markdown("---")
    
    # SENİN ORİJİNAL FİLTRELEME MANTIĞIN
    if page in ["Dashboard", "Görev Yönetimi"]:
        st.subheader("🔍 Gelişmiş Filtreleme")
        
        # Etiket Filtresi
        all_tags = [t[0] for t in db.get_all_task_tags()]
        sel_tags = st.multiselect("Etiketler", all_tags)
        
        # Önem Filtresi
        sel_imps = st.multiselect("Önem Seviyesi", list(LEVELS.keys()))
        
        # Çaba Filtresi
        sel_effs = st.multiselect("Çaba Seviyesi", list(LEVELS.keys()))
        
        # Sıralama
        sort_opt = st.selectbox("Sıralama", [
            'Önem (Yüksek -> Düşük)', 
            'Önem (Düşük -> Yüksek)', 
            'Çaba (Az -> Çok)', 
            'Tarih (Yeni -> Eski)'
        ])
        
        # Sıralama kodunu DB formatına çevir
        sort_map = {
            'Önem (Yüksek -> Düşük)': 'importance_desc',
            'Önem (Düşük -> Yüksek)': 'importance_asc',
            'Çaba (Az -> Çok)': 'effort_asc',
            'Tarih (Yeni -> Eski)': 'date'
        }
        current_sort = sort_map[sort_opt]

# --- HELPER: ROZET HTML OLUŞTURUCU ---
def render_badges(imp, eff, tag):
    imp_html = f'<span class="badge imp-{imp}">{LEVELS_REV[imp]}</span>'
    eff_html = f'<span class="badge" style="background-color: #555;">Çaba: {LEVELS_REV[eff]}</span>'
    tag_html = ""
    if tag:
        color = db.get_task_tag_color(tag)
        tag_html = f'<span class="badge" style="background-color: {color};">{tag}</span>'
    return f"{tag_html} {imp_html} {eff_html}"

# --- SAYFA 1: DASHBOARD (SENİN ACCORDION YAPIN) ---
if page == "Dashboard":
    st.header("📊 Genel Bakış (Dashboard)")
    
    folders = db.get_folders('todo')
    if not folders:
        st.info("Henüz hiç klasör yok.")
    
    for folder in folders:
        f_id, f_name, f_type, f_tag = folder
        
        # Filtreli görevleri getir
        tasks = db.get_todos(f_id, sort_by=current_sort, done_filter=0, tag_list=sel_tags, imp_list=sel_imps, eff_list=sel_effs)
        
        # Klasör başlığında görev sayısı
        count_badge = f"({len(tasks)})" if tasks else ""
        
        # Streamlit "Expander" = Senin "Accordion"
        with st.expander(f"📁 {f_name} {count_badge}", expanded=(len(tasks) > 0)):
            if not tasks:
                st.caption("Görüntülenecek görev yok.")
            
            for task in tasks:
                tid, _, txt, done, imp, eff, date, tag = task
                
                # Tek Satırlık Görev Kartı
                c1, c2, c3 = st.columns([0.05, 0.85, 0.1])
                
                if c1.checkbox("", key=f"dash_{tid}"):
                    db.toggle_todo(tid, 0)
                    st.rerun()
                
                # HTML ile Zengin İçerik (Badges)
                c2.markdown(f"**{txt}** <br> {render_badges(imp, eff, tag)}", unsafe_allow_html=True)
                
                if c3.button("🗑", key=f"del_dash_{tid}"):
                    db.delete_todo(tid)
                    st.rerun()

# --- SAYFA 2: DETAYLI GÖREV YÖNETİMİ ---
elif page == "Görev Yönetimi":
    st.header("✅ Görev Yönetimi")
    
    folders = db.get_folders('todo')
    f_dict = {f[1]: f[0] for f in folders}
    
    col_f1, col_f2 = st.columns([3, 1])
    active_folder_name = col_f1.selectbox("Aktif Klasör", list(f_dict.keys()) if f_dict else [])
    
    with col_f2:
        with st.popover("Klasör Oluştur"):
            nf_name = st.text_input("Klasör Adı")
            if st.button("Oluştur"):
                db.add_folder(nf_name, 'todo')
                st.rerun()

    if active_folder_name:
        fid = f_dict[active_folder_name]
        
        # --- INPUT MATRIX (Veri Girişi) ---
        st.markdown("### ⚡ Hızlı Ekle")
        with st.form("add_task", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
            new_task = c1.text_input("Görev", placeholder="Ne yapılması gerekiyor?")
            
            # Etiket Seçimi (Veritabanından)
            db_tags = [t[0] for t in db.get_all_task_tags()]
            new_tag = c2.selectbox("Etiket", [""] + db_tags)
            
            new_imp = c3.select_slider("Önem", options=list(LEVELS.keys()), value="Orta")
            new_eff = c4.select_slider("Çaba", options=list(LEVELS.keys()), value="Düşük")
            
            if st.form_submit_button("Listeye Ekle", use_container_width=True):
                if new_task:
                    # Yeni etiket yazıldıysa onu da kaydet
                    if new_tag and new_tag not in db_tags:
                        db.add_or_update_task_tag(new_tag, "#3498DB") 
                    
                    db.add_todo(fid, new_task, LEVELS[new_imp], LEVELS[new_eff], new_tag)
                    st.rerun()

        # --- LİSTE GÖRÜNÜMÜ ---
        tab1, tab2 = st.tabs(["Yapılacaklar", "Tamamlananlar"])
        
        with tab1:
            todos = db.get_todos(fid, sort_by=current_sort, done_filter=0, tag_list=sel_tags, imp_list=sel_imps, eff_list=sel_effs)
            for task in todos:
                tid, _, txt, done, imp, eff, date, tag = task
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.05, 0.85, 0.1])
                    if c1.checkbox("", key=f"list_{tid}"):
                        db.toggle_todo(tid, 0)
                        st.rerun()
                    c2.markdown(f"**{txt}**")
                    c2.markdown(render_badges(imp, eff, tag), unsafe_allow_html=True)
                    if c3.button("Sil", key=f"del_list_{tid}"):
                        db.delete_todo(tid)
                        st.rerun()
                        
        with tab2:
            dones = db.get_todos(fid, done_filter=1)
            for task in dones:
                tid, _, txt, _, _, _, date, _ = task
                st.markdown(f"~~{txt}~~ *({date})*")
                if st.button("Geri Al", key=f"undo_{tid}"):
                    db.toggle_todo(tid, 1)
                    st.rerun()

# --- ŞİMDİLİK BU KADAR ---
else:
    st.info("Notlar ve Haftalık Rutin modülleri bir sonraki güncellemede eklenecek. Önce Dashboard'u test et.")