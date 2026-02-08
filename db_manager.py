import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import random
import streamlit as st
import os
import time
from gspread.exceptions import APIError

# --- SABİTLER ---
SHEET_NAME = 'LifeManager_DB'
LEVELS = {'Çok Düşük': 1, 'Düşük': 2, 'Orta': 3, 'Yüksek': 4, 'Çok Yüksek': 5}
LEVELS_REV = {v: k for k, v in LEVELS.items()}
DEFAULT_TAG_COLORS = ['#E74C3C', '#8E44AD', '#3498DB', '#1ABC9C', '#F1C40F', '#E67E22', '#7F8C8D', '#2ECC71', '#34495E', '#D35400']

# --- RETRY DECORATOR (HATA YAKALAYICI) ---
def retry_api_call(func):
    """API hatası (429 Quota) verirse bekleyip tekrar dener."""
    def wrapper(*args, **kwargs):
        max_retries = 5
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                # 429: Too Many Requests (Kota Doldu)
                if e.response.status_code == 429:
                    wait_time = (2 ** i) + random.random() # 1s, 2.5s, 4.2s... artarak bekle
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(2)
                    continue
                raise e
        return func(*args, **kwargs)
    return wrapper

# --- CACHE (ÖNBELLEK) ---
# Client bağlantısını hafızada tutar
@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "secrets.json")
    
    if os.path.exists(json_path):
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    elif "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    else:
        st.error("HATA: 'secrets.json' bulunamadı!")
        st.stop()
        
    return gspread.authorize(creds)

# Veriyi hafızada tutar (600 saniye = 10 dakika boyunca Google'a gitmez)
@st.cache_data(ttl=600) 
def fetch_sheet_data(sheet_name, worksheet_name):
    client = get_gspread_client()
    try:
        # Retry mantığını burada manuel uyguluyoruz çünkü decorator cache ile bazen çakışır
        for i in range(5):
            try:
                sh = client.open(sheet_name)
                ws = sh.worksheet(worksheet_name)
                return pd.DataFrame(ws.get_all_records())
            except APIError as e:
                if e.response.status_code == 429:
                    time.sleep((2 ** i) + 1)
                    continue
                raise e
    except:
        return pd.DataFrame() # Hata olursa boş dön

# --- DATABASE SINIFI ---
class Database:
    def __init__(self):
        # __init__ içinde API çağrısı YAPMIYORUZ. Hız için.
        self.client = get_gspread_client()

    def _get_sheet_obj(self):
        return self.client.open(SHEET_NAME)

    def _clear_cache(self):
        """Yazma işlemi yapıldığında önbelleği temizle"""
        fetch_sheet_data.clear()

    # --- OKUMA (Hepsi Cache Kullanır) ---
    def _get_df(self, worksheet_name):
        return fetch_sheet_data(SHEET_NAME, worksheet_name)

    # --- YAZMA (Hepsi Retry Kullanır) ---
    @retry_api_call
    def _add_row(self, worksheet_name, row_data):
        sh = self._get_sheet_obj()
        ws = sh.worksheet(worksheet_name)
        try:
            ids = ws.col_values(1)[1:] 
            new_id = max([int(x) for x in ids if str(x).isdigit()] or [0]) + 1
        except: new_id = 1
        
        ws.append_row([new_id] + row_data)
        self._clear_cache() # Önemli: Yazdıktan sonra cache'i temizle
        return new_id

    @retry_api_call
    def _update_cell(self, worksheet_name, row_id, col_name, new_value):
        sh = self._get_sheet_obj()
        ws = sh.worksheet(worksheet_name)
        headers = ws.row_values(1)
        try:
            col_idx = headers.index(col_name) + 1
            cell = ws.find(str(row_id), in_column=1)
            ws.update_cell(cell.row, col_idx, new_value)
            self._clear_cache()
        except: pass

    @retry_api_call
    def _delete_row(self, worksheet_name, row_id):
        sh = self._get_sheet_obj()
        ws = sh.worksheet(worksheet_name)
        try:
            cell = ws.find(str(row_id), in_column=1)
            ws.delete_rows(cell.row)
            self._clear_cache()
        except: pass

    # --- RENKLER ---
    def get_level_colors(self):
        df = self._get_df('level_colors')
        if df.empty:
             return {'imp': {5:'#c0392b',4:'#e67e22',3:'#f1c40f',2:'#2ecc71',1:'#27ae60'}, 'eff': {i: '#444444' for i in range(1,6)}}
        
        res = {'imp': {}, 'eff': {}}
        for _, row in df.iterrows():
            res.setdefault(row['level_type'], {})[row['level_value']] = row['color']
        return res

    def update_level_color(self, ltype, lval, color):
        sh = self._get_sheet_obj()
        ws = sh.worksheet('level_colors')
        data = ws.get_all_values()
        found = False
        for i, row in enumerate(data[1:], start=2):
            if len(row) >= 2 and row[0] == ltype and str(row[1]) == str(lval):
                ws.update_cell(i, 3, color)
                found = True; break
        if not found: ws.append_row([ltype, lval, color])
        self._clear_cache()

    # --- KLASÖRLER ---
    def get_folders(self, f_type):
        df = self._get_df('folders')
        if df.empty: return []
        filtered = df[df['type'] == f_type].sort_values(by='id', ascending=False)
        return list(filtered[['id', 'name', 'type', 'tag']].itertuples(index=False, name=None))

    def add_folder(self, name, f_type, tag=''):
        if tag: self.add_or_update_folder_tag(tag, random.choice(DEFAULT_TAG_COLORS), True)
        self._add_row('folders', [name, f_type, tag])

    def update_folder(self, folder_id, name, tag):
        self._update_cell('folders', folder_id, 'name', name)
        self._update_cell('folders', folder_id, 'tag', tag)

    def delete_folder(self, folder_id):
        self._delete_row('folders', folder_id)

    # --- GÖREVLER ---
    def get_todos(self, folder_id, sort_by='date', done_filter=None, tag_list=None, imp_list=None, eff_list=None):
        df = self._get_df('todos')
        if df.empty: return []
        
        df = df[df['folder_id'] == folder_id]
        if done_filter is not None: df = df[df['is_done'] == done_filter]
        if tag_list: df = df[df['tag'].isin(tag_list)]
        if imp_list: df = df[df['importance'].isin([LEVELS[i] for i in imp_list])]
        if eff_list: df = df[df['effort'].isin([LEVELS[e] for e in eff_list])]
        
        sort_config = {
            'importance_desc': (['importance', 'id'], [False, False]),
            'importance_asc': (['importance', 'id'], [True, False]),
            'effort_asc': (['effort', 'id'], [True, False]),
            'effort_desc': (['effort', 'id'], [False, False]),
            'date': ('id', False)
        }
        by, asc = sort_config.get(sort_by, ('id', False))
        df = df.sort_values(by=by, ascending=asc)
        return list(df[['id', 'folder_id', 'task', 'is_done', 'importance', 'effort', 'date', 'tag']].itertuples(index=False, name=None))

    def add_todo(self, folder_id, task, importance, effort, tag):
        date = datetime.now().strftime('%d %b, %H:%M')
        if tag: self.add_or_update_task_tag(tag, random.choice(DEFAULT_TAG_COLORS), True)
        self._add_row('todos', [folder_id, task, 0, importance, effort, date, tag])

    def update_todo(self, todo_id, task, importance, effort, tag):
        # Batch update (Hücre aralığı güncelleme) yerine tek tek ama güvenli
        self._update_cell('todos', todo_id, 'task', task)
        self._update_cell('todos', todo_id, 'importance', importance)
        self._update_cell('todos', todo_id, 'effort', effort)
        self._update_cell('todos', todo_id, 'tag', tag)

    def toggle_todo(self, todo_id, current_status):
        self._update_cell('todos', todo_id, 'is_done', 1 if int(current_status)==0 else 0)

    def delete_todo(self, todo_id):
        self._delete_row('todos', todo_id)

    # --- NOTLAR ---
    def get_notes(self, folder_id):
        df = self._get_df('notes')
        if df.empty: return []
        df = df[df['folder_id'] == folder_id].sort_values(by='id', ascending=False)
        return list(df[['id', 'folder_id', 'title', 'content', 'date']].itertuples(index=False, name=None))

    def add_note(self, folder_id, title, content):
        date = datetime.now().strftime('%Y-%m-%d')
        self._add_row('notes', [folder_id, title, content, date])

    def update_note(self, note_id, title, content):
        self._update_cell('notes', note_id, 'title', title)
        self._update_cell('notes', note_id, 'content', content)

    def delete_note(self, note_id):
        self._delete_row('notes', note_id)

    # --- RUTİN ---
    def get_weekly_tasks(self, day):
        df = self._get_df('weekly_schedule')
        if df.empty: return []
        today = datetime.now().strftime('%Y-%m-%d')
        res = []
        for row in df[df['day_name'] == day].sort_values(by='time_range').itertuples(index=False, name=None):
            if row[4] == 1 and str(row[5]) != today:
                self._update_cell('weekly_schedule', row[0], 'is_done', 0)
                self._update_cell('weekly_schedule', row[0], 'last_completed_date', '')
                res.append((row[0], row[1], row[2], row[3], 0, ''))
            else: res.append(row)
        return res

    def add_weekly_task(self, day, time, task):
        self._add_row('weekly_schedule', [day, time, task, 0, ''])

    def toggle_weekly_task(self, t_id, current_status):
        new = 1 if int(current_status)==0 else 0
        self._update_cell('weekly_schedule', t_id, 'is_done', new)
        self._update_cell('weekly_schedule', t_id, 'last_completed_date', datetime.now().strftime('%Y-%m-%d') if new else '')

    def delete_weekly_task(self, t_id):
        self._delete_row('weekly_schedule', t_id)

    # --- ETİKETLER ---
    def get_all_task_tags(self):
        df = self._get_df('tags')
        return [] if df.empty else list(df[['name', 'color']].sort_values(by='name').itertuples(index=False, name=None))

    def get_task_tag_color(self, tag_name):
        df = self._get_df('tags')
        try:
            res = df[df['name'] == tag_name]['color']
            return res.values[0] if not res.empty else '#9B59B6'
        except: return '#9B59B6'

    def add_or_update_task_tag(self, name, color, check_exist=False):
        sh = self._get_sheet_obj()
        ws = sh.worksheet('tags')
        try:
            cell = ws.find(name, in_column=1)
            if not check_exist: 
                ws.update_cell(cell.row, 2, color)
                self._clear_cache()
        except:
            ws.append_row([name, color])
            self._clear_cache()

    def delete_task_tag(self, tag_name):
        sh = self._get_sheet_obj()
        ws = sh.worksheet('tags')
        try: 
            ws.delete_rows(ws.find(tag_name, in_column=1).row)
            self._clear_cache()
        except: pass

    # KLASÖR ETİKETLERİ
    def get_all_folder_tags(self):
        df = self._get_df('folder_tags')
        return [] if df.empty else list(df[['name', 'color']].sort_values(by='name').itertuples(index=False, name=None))

    def get_folder_tag_color(self, tag_name):
        df = self._get_df('folder_tags')
        try:
            res = df[df['name'] == tag_name]['color']
            return res.values[0] if not res.empty else '#34495E'
        except: return '#34495E'

    def add_or_update_folder_tag(self, name, color, check_exist=False):
        sh = self._get_sheet_obj()
        ws = sh.worksheet('folder_tags')
        try:
            cell = ws.find(name, in_column=1)
            if not check_exist: 
                ws.update_cell(cell.row, 2, color)
                self._clear_cache()
        except:
            ws.append_row([name, color])
            self._clear_cache()

    def delete_folder_tag(self, tag_name):
        sh = self._get_sheet_obj()
        ws = sh.worksheet('folder_tags')
        try: 
            ws.delete_rows(ws.find(tag_name, in_column=1).row)
            self._clear_cache()
        except: pass