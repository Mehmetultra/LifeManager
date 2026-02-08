import streamlit as st
from db_manager import Database, LEVELS, LEVELS_REV, DEFAULT_TAG_COLORS
import datetime

# --- YAPILANDIRMA ---
st.set_page_config(page_title="LifeManager V5.4", page_icon="⚡", layout="wide")

# --- DB BAŞLATMA ---
if 'db' not in st.session_state:
    st.session_state.db = Database()
db = st.session_state.db

# --- DİNAMİK RENK YÜKLEME ---
# Veritabanından seviye renklerini çekiyoruz
level_colors = db.get_level_colors() # {'imp': {1: '#...', ...}, 'eff': {...}}

# CSS Oluşturucu
css_dynamic = ""
for lvl, color in level_colors.get('imp', {}).items():
    # Orta seviye (3) için siyah yazı, diğerleri beyaz
    text_col = 'black' if lvl == 3 else 'white'
    css_dynamic += f".imp-{lvl} {{ background-color: {color}; color: {text_col} !important; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}\n"

for lvl, color in level_colors.get('eff', {}).items():
    # Çaba renkleri
    css_dynamic += f".eff-{lvl} {{ background-color: {color}; color: white !important; padding: 2px 6px; border-radius: 4px; font-size: 11px; }}\n"


# --- CSS: ULTIMATE DARK & DYNAMIC ---
st.markdown(f"""
<style>
    /* 1. KESİN ARKA PLAN */
    .stApp {{
        background-color: #202020 !important;
        color: #E3E3E3 !important;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: #191919 !important;
        border-right: 1px solid #333 !important;
    }}

    /* 2. DROPDOWN VE INPUT FIX */
    .stSelectbox div[data-baseweb="select"] > div, 
    .stMultiSelect div[data-baseweb="select"] > div {{
        background-color: #2b2b2b !important;
        border-color: #444 !important;
        color: #E3E3E3 !important;
    }}
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-testid="stSelectboxVirtualList"] {{
        background-color: #1e1e1e !important;
        border: 1px solid #555 !important;
    }}
    li[role="option"], div[role="option"], div[data-baseweb="option"] {{
        background-color: #1e1e1e !important;
        color: #E3E3E3 !important;
    }}
    li[role="option"]:hover, div[role="option"]:hover, li[aria-selected="true"] {{
        background-color: #3B8ED0 !important;
        color: white !important;
    }}
    div[data-baseweb="tag"] {{
        background-color: #3B8ED0 !important;
        color: white !important;
    }}
    
    /* 3. INPUTLAR */
    .stTextInput input, .stTextArea textarea {{
        background-color: #2b2b2b !important;
        color: #E3E3E3 !important;
        border: 1px solid #444 !important;
    }}
    ::placeholder {{ color: #888 !important; opacity: 1; }}

    /* 4. BUTONLAR */
    div.stButton > button {{
        background-color: #3d3d3d !important;
        color: #E3E3E3 !important;
        border: 1px solid #555 !important;
        border-radius: 6px !important;
    }}
    div.stButton > button:hover {{
        border-color: #3B8ED0 !important;
        color: #3B8ED0 !important;
    }}
    div.stButton > button[kind="primary"] {{
        background-color: #2E86DE !important;
        border-color: #2E86DE !important;
        color: white !important;
    }}

    /* 5. KART TASARIMI */
    div[data-testid="stBorderContainer"] {{
        background-color: #2b2b2b !important;
        border: 1px solid #3d3d3d !important;
        border-radius: 10px !important;
        padding: 15px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}

    /* 6. EXPANDER */
    .stExpander {{
        background-color: #2b2b2b !important;
        border: 1px solid #3d3d3d !important;
        border-radius: 8px !important;
    }}
    .streamlit-expanderHeader {{
        background-color: #2b2b2b !important;
        color: #E3E3E3 !important;
    }}
    
    /* Yazılar */
    h1, h2, h3, p, label, span {{ color: #E3E3E3 !important; }}

    /* 7. ETİKETLER */
    .custom-tag {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        color: white !important;
        margin-top: 5px;
    }}
    
    /* --- DİNAMİK RENKLER BURAYA GELİYOR --- */
    {css_dynamic}

</style>
""", unsafe_allow_html=True)

# --- STATE ---
if 'active_folder_id' not in st.session_state: st.session_state.active_folder_id = None
if 'editing_task_id' not in st.session_state: st.session_state.editing_task_id = None

# --- NAVİGASYON ---
def open_folder(f_id, f_name, f_type):
    st.session_state.active_folder_id = f_id
    st.session_state.active_folder_name = f_name
    st.session_state.active_folder_type = f_type
    st.session_state.editing_task_id = None 

def close_folder():
    st.session_state.active_folder_id = None
    st.session_state.editing_task_id = None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚡ Life Manager")
    selected_page = st.radio("Menü", ["Dashboard", "Görevler", "Notlar", "Haftalık Rutin", "Ayarlar"])
    
    if 'current_page' not in st.session_state: st.session_state.current_page = selected_page
    if st.session_state.current_page != selected_page:
        close_folder()
        st.session_state.current_page = selected_page

    st.markdown("---")
    
    if selected_page in ["Dashboard", "Görevler"]:
        st.markdown("#### 🔍 Filtreleme")
        all_tags = [t[0] for t in db.get_all_task_tags()]
        sel_tags = st.multiselect("Etiketler", all_tags)
        sel_imps = st.multiselect("Önem", list(LEVELS.keys()))
        sel_effs = st.multiselect("Çaba", list(LEVELS.keys()))
        
        sort_opt = st.selectbox("Sıralama", ['Önem (Yüksek -> Düşük)', 'Önem (Düşük -> Yüksek)', 'Çaba (Az -> Çok)', 'Tarih (Yeni -> Eski)'])
        sort_map = {'Önem (Yüksek -> Düşük)': 'importance_desc', 'Önem (Düşük -> Yüksek)': 'importance_asc', 'Çaba (Az -> Çok)': 'effort_asc', 'Tarih (Yeni -> Eski)': 'date'}
        current_sort = sort_map[sort_opt]
    else:
        sel_tags, sel_imps, sel_effs, current_sort = [], [], [], 'date'

# --- HTML HELPER (Dinamik CSS classları kullanıyor) ---
def render_badges(imp, eff, tag):
    # Artık renkleri DB'den gelen CSS classları yönetiyor (imp-1, eff-2 vb.)
    imp_html = f'<span class="imp-{imp}">{LEVELS_REV[imp]}</span>'
    eff_html = f'<span class="eff-{eff}">Çaba: {LEVELS_REV[eff]}</span>'
    tag_html = ""
    if tag:
        color = db.get_task_tag_color(tag)
        tag_html = f'<span style="background-color: {color}; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; color: white !important;">{tag}</span>'
    return f"{tag_html} {imp_html} {eff_html}"

# ==============================================================================
# SAYFA: DASHBOARD
# ==============================================================================
if selected_page == "Dashboard":
    st.markdown("## 📊 Genel Bakış")
    folders = db.get_folders('todo')
    has_task = False
    
    for folder in folders:
        f_id, f_name, f_type, f_tag = folder
        tasks = db.get_todos(f_id, sort_by=current_sort, done_filter=0, tag_list=sel_tags, imp_list=sel_imps, eff_list=sel_effs)
        
        if tasks:
            has_task = True
            with st.expander(f"📁 {f_name} ({len(tasks)})", expanded=True):
                if f_tag:
                    tc = db.get_folder_tag_color(f_tag)
                    st.markdown(f"<div style='height: 3px; width: 100%; background-color: {tc}; border-radius: 2px; margin-bottom: 8px;'></div>", unsafe_allow_html=True)
                
                for task in tasks:
                    tid, _, txt, done, imp, eff, date, tag = task
                    c1, c2, c3 = st.columns([0.05, 0.85, 0.1])
                    if c1.checkbox("", key=f"d_{tid}"): db.toggle_todo(tid, 0); st.rerun()
                    c2.markdown(f"<div style='font-size:15px; margin-bottom:4px; color: #E3E3E3;'>{txt}</div>{render_badges(imp, eff, tag)}", unsafe_allow_html=True)
                    if c3.button("🗑", key=f"dd_{tid}"): db.delete_todo(tid); st.rerun()
    if not has_task: st.info("Yapılacak iş yok.")

# ==============================================================================
# SAYFA: GÖREVLER
# ==============================================================================
elif selected_page == "Görevler":
    if st.session_state.active_folder_id is None:
        c1, c2 = st.columns([0.8, 0.2])
        c1.markdown("## 📂 Görev Klasörleri")
        with c2:
            with st.popover("+ Yeni Klasör"):
                nf_name = st.text_input("Klasör Adı")
                ftags = [t[0] for t in db.get_all_folder_tags()]
                nf_tag = st.selectbox("Etiket", [""] + ftags)
                if st.button("Oluştur", type="primary"): db.add_folder(nf_name, 'todo', nf_tag); st.rerun()

        folders = db.get_folders('todo')
        cols = st.columns(4)
        for i, folder in enumerate(folders):
            f_id, f_name, f_type, f_tag = folder
            with cols[i % 4]:
                with st.container(border=True):
                    tag_html = ""
                    if f_tag:
                        tc = db.get_folder_tag_color(f_tag)
                        tag_html = f'<div class="custom-tag" style="background-color: {tc};">{f_tag}</div>'
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px;">
                        <div style="font-size: 32px; margin-bottom: 5px;">📁</div>
                        <div style="font-weight: 600; font-size: 16px; margin-bottom: 5px; color: #fff;">{f_name}</div>
                        {tag_html}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2 = st.columns([3, 1])
                    if b1.button("Aç", key=f"op_{f_id}", use_container_width=True, type="primary"):
                        open_folder(f_id, f_name, 'todo')
                        st.rerun()
                    
                    with b2.popover("⚙️"):
                        st.markdown("###### Ayarlar")
                        new_fn = st.text_input("İsim", value=f_name, key=f"edn_{f_id}")
                        ftags = [t[0] for t in db.get_all_folder_tags()]
                        idx = ftags.index(f_tag) + 1 if f_tag in ftags else 0
                        new_ft = st.selectbox("Etiket", [""] + ftags, index=idx, key=f"edt_{f_id}")
                        if st.button("Kaydet", key=f"sv_{f_id}"):
                            db.update_folder(f_id, new_fn, new_ft)
                            st.rerun()
                        st.divider()
                        if st.button("🗑 Sil", key=f"del_f_{f_id}", type="primary"):
                            db.delete_folder(f_id)
                            st.rerun()

    else:
        fid = st.session_state.active_folder_id
        c_back, c_tit = st.columns([0.1, 0.9])
        if c_back.button("🔙"): close_folder(); st.rerun()
        c_tit.markdown(f"## 📂 {st.session_state.active_folder_name}")

        edit_mode = st.session_state.editing_task_id is not None
        default_vals = {"txt": "", "imp": "Orta", "eff": "Düşük", "tag": ""}
        if edit_mode:
            todos = db.get_todos(fid)
            for t in todos:
                if t[0] == st.session_state.editing_task_id:
                    default_vals = {"txt": t[2], "imp": LEVELS_REV[t[4]], "eff": LEVELS_REV[t[5]], "tag": t[7]}
                    st.info(f"✏️ Düzenleniyor: {t[2]}")
                    break

        with st.container(border=True):
            with st.form("task_form", clear_on_submit=not edit_mode):
                c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
                nt = c1.text_input("Görev", value=default_vals["txt"])
                db_tags = [t[0] for t in db.get_all_task_tags()]
                tidx = db_tags.index(default_vals["tag"]) + 1 if default_vals["tag"] in db_tags else 0
                ntag = c2.selectbox("Etiket", [""] + db_tags, index=tidx)
                nimp = c3.select_slider("Önem", options=list(LEVELS.keys()), value=default_vals["imp"])
                neff = c3.select_slider("Çaba", options=list(LEVELS.keys()), value=default_vals["eff"])
                
                submitted = st.form_submit_button("Kaydet" if edit_mode else "Ekle", type="primary", use_container_width=True)
                if submitted and nt:
                    if ntag and ntag not in db_tags: db.add_or_update_task_tag(ntag, "#3498DB")
                    if edit_mode:
                        db.update_todo(st.session_state.editing_task_id, nt, LEVELS[nimp], LEVELS[neff], ntag)
                        st.session_state.editing_task_id = None
                    else:
                        db.add_todo(fid, nt, LEVELS[nimp], LEVELS[neff], ntag)
                    st.rerun()
        if edit_mode and st.button("İptal"): st.session_state.editing_task_id = None; st.rerun()

        t1, t2 = st.tabs(["Yapılacaklar", "Tamamlananlar"])
        with t1:
            todos = db.get_todos(fid, sort_by=current_sort, done_filter=0, tag_list=sel_tags, imp_list=sel_imps, eff_list=sel_effs)
            for task in todos:
                tid, _, txt, done, imp, eff, date, tag = task
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.05, 0.75, 0.2])
                    if c1.checkbox("", key=f"L_{tid}"): db.toggle_todo(tid, 0); st.rerun()
                    c2.markdown(f"<div style='font-weight:500; font-size:15px; color:#E3E3E3;'>{txt}</div>{render_badges(imp, eff, tag)}", unsafe_allow_html=True)
                    b1, b2 = c3.columns(2)
                    if b1.button("✏️", key=f"E_{tid}"): st.session_state.editing_task_id = tid; st.rerun()
                    if b2.button("🗑", key=f"D_{tid}"): db.delete_todo(tid); st.rerun()
        with t2:
            dones = db.get_todos(fid, done_filter=1)
            for task in dones:
                tid, _, txt, _, _, _, date, _ = task
                st.markdown(f"<span style='text-decoration:line-through; color:#888'>{txt}</span> <small>({date})</small>", unsafe_allow_html=True)
                if st.button("Geri Al", key=f"U_{tid}"): db.toggle_todo(tid, 1); st.rerun()

# ==============================================================================
# SAYFA: NOTLAR
# ==============================================================================
elif selected_page == "Notlar":
    if st.session_state.active_folder_id is None:
        c1, c2 = st.columns([0.8, 0.2])
        c1.markdown("## 📝 Not Defterleri")
        with c2:
            with st.popover("+ Yeni Defter"):
                nf_name = st.text_input("Ad")
                if st.button("Oluştur", type="primary"): db.add_folder(nf_name, 'note'); st.rerun()
        
        folders = db.get_folders('note')
        cols = st.columns(4)
        for i, folder in enumerate(folders):
            f_id, f_name, f_type, f_tag = folder
            with cols[i % 4]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px;">
                        <div style="font-size: 30px; margin-bottom: 5px;">📒</div>
                        <div style="font-weight: bold; font-size: 16px; color: #fff;">{f_name}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    b1, b2 = st.columns([3, 1])
                    if b1.button("Aç", key=f"nop_{f_id}", use_container_width=True, type="primary"): open_folder(f_id, f_name, 'note'); st.rerun()
                    with b2.popover("⚙️"):
                        nn = st.text_input("İsim", value=f_name, key=f"ned_{f_id}")
                        if st.button("Güncelle", key=f"nup_{f_id}"): db.update_folder(f_id, nn, ""); st.rerun()
                        st.divider()
                        if st.button("Sil", key=f"ndel_{f_id}", type="primary"): db.delete_folder(f_id); st.rerun()
    else:
        c_back, c_tit = st.columns([0.1, 0.9])
        if c_back.button("🔙"): close_folder(); st.rerun()
        c_tit.markdown(f"## 📒 {st.session_state.active_folder_name}")
        
        fid = st.session_state.active_folder_id
        col_list, col_editor = st.columns([1, 2])
        
        with col_list:
            if st.button("+ Yeni Not", use_container_width=True, type="primary"):
                st.session_state.active_note_id = None
                st.session_state.note_title_input = ""
                st.session_state.note_content_input = ""
            
            notes = db.get_notes(fid)
            for note in notes:
                nid, _, title, content, date = note
                if st.button(f"{title}\n{date}", key=f"sn_{nid}", use_container_width=True):
                    st.session_state.active_note_id = nid
                    st.session_state.note_title_input = title
                    st.session_state.note_content_input = content

        with col_editor:
            curr_nid = st.session_state.get('active_note_id', None)
            curr_title = st.session_state.get('note_title_input', '')
            curr_content = st.session_state.get('note_content_input', '')
            
            with st.container(border=True):
                st.markdown(f"### {'Yeni Not' if curr_nid is None else 'Düzenle'}")
                with st.form("note_form"):
                    nt = st.text_input("Başlık", value=curr_title)
                    nc = st.text_area("İçerik", value=curr_content, height=500)
                    if st.form_submit_button("Kaydet", type="primary"):
                        if curr_nid: db.update_note(curr_nid, nt, nc)
                        else: db.add_note(fid, nt, nc)
                        st.success("Kaydedildi"); st.rerun()
                if curr_nid and st.button("🗑 Notu Sil"):
                    db.delete_note(curr_nid)
                    st.session_state.active_note_id = None
                    st.session_state.note_title_input = ""
                    st.session_state.note_content_input = ""
                    st.rerun()

# ==============================================================================
# SAYFA: HAFTALIK RUTİN
# ==============================================================================
elif selected_page == "Haftalık Rutin":
    st.markdown("## 📅 Haftalık Rutinler")
    days = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    tabs = st.tabs(days)
    
    for i, day in enumerate(days):
        with tabs[i]:
            with st.container(border=True):
                with st.form(f"rout_{day}", clear_on_submit=True):
                    c1, c2, c3 = st.columns([1, 3, 1])
                    rt = c1.text_input("Saat")
                    rx = c2.text_input("Rutin")
                    if c3.form_submit_button("Ekle", type="primary"): db.add_weekly_task(day, rt, rx); st.rerun()
            
            tasks = db.get_weekly_tasks(day)
            for t in tasks:
                t_id, _, t_time, t_text, t_done, _ = t
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.05, 0.85, 0.1])
                    check = c1.checkbox("", value=bool(t_done), key=f"wr_{t_id}")
                    if check != bool(t_done): db.toggle_weekly_task(t_id, check); st.rerun()
                    style = "text-decoration: line-through; color: #888;" if t_done else "color: #E3E3E3; font-weight: bold;"
                    c2.markdown(f"<span style='{style}'>[{t_time}] {t_text}</span>", unsafe_allow_html=True)
                    if c3.button("🗑", key=f"wd_{t_id}"): db.delete_weekly_task(t_id); st.rerun()

# ==============================================================================
# SAYFA: AYARLAR
# ==============================================================================
elif selected_page == "Ayarlar":
    st.markdown("## ⚙️ Ayarlar")
    t1, t2, t3 = st.tabs(["Görev Etiketleri", "Klasör Etiketleri", "Derece Renkleri"])
    
    # GÖREV ETİKETLERİ
    with t1:
        tags = db.get_all_task_tags()
        for tag in tags:
            tname, tcolor = tag
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.1, 0.3, 0.3, 0.3])
                c1.color_picker("", value=tcolor, key=f"cp_t_{tname}", disabled=True)
                c2.markdown(f"**{tname}**")
                with c3.popover("Düzenle"):
                    nc = st.color_picker("Renk", value=tcolor, key=f"ncpt_{tname}")
                    if st.button("Kaydet", key=f"svt_{tname}"): db.add_or_update_task_tag(tname, nc); st.rerun()
                if c4.button("Sil", key=f"dt_{tname}"): db.delete_task_tag(tname); st.rerun()

    # KLASÖR ETİKETLERİ
    with t2:
        ftags = db.get_all_folder_tags()
        for tag in ftags:
            tname, tcolor = tag
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.1, 0.3, 0.3, 0.3])
                c1.color_picker("", value=tcolor, key=f"cp_f_{tname}", disabled=True)
                c2.markdown(f"**{tname}**")
                with c3.popover("Düzenle"):
                    nc = st.color_picker("Renk", value=tcolor, key=f"ncpf_{tname}")
                    if st.button("Kaydet", key=f"svf_{tname}"): db.add_or_update_folder_tag(tname, nc); st.rerun()
                if c4.button("Sil", key=f"df_{tname}"): db.delete_folder_tag(tname); st.rerun()

    # YENİ: DERECE RENKLERİ
    with t3:
        st.markdown("#### Önem Seviyesi Renkleri")
        l_colors = db.get_level_colors()
        imps = l_colors.get('imp', {})
        # Büyükten küçüğe sırala (5'ten 1'e)
        for level in range(5, 0, -1):
            col_val = imps.get(level, '#888888')
            lvl_name = LEVELS_REV[level]
            c1, c2 = st.columns([0.2, 0.8])
            new_c = c1.color_picker(lvl_name, value=col_val, key=f"lvl_imp_{level}")
            c2.markdown(f"**{lvl_name}**")
            if new_c != col_val:
                db.update_level_color('imp', level, new_c)
                st.rerun()
        
        st.divider()
        st.markdown("#### Çaba Seviyesi Renkleri")
        effs = l_colors.get('eff', {})
        for level in range(1, 6):
            col_val = effs.get(level, '#444444')
            lvl_name = LEVELS_REV[level]
            c1, c2 = st.columns([0.2, 0.8])
            new_c = c1.color_picker(lvl_name, value=col_val, key=f"lvl_eff_{level}")
            c2.markdown(f"**{lvl_name}**")
            if new_c != col_val:
                db.update_level_color('eff', level, new_c)
                st.rerun()