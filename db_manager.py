import sqlite3
from datetime import datetime
import random

DB_NAME = 'lifemanager_db.sqlite'

# Seviye İsimleri (Sabit Kalır, Renkleri Değişir)
LEVELS = {'Çok Düşük': 1, 'Düşük': 2, 'Orta': 3, 'Yüksek': 4, 'Çok Yüksek': 5}
LEVELS_REV = {v: k for k, v in LEVELS.items()}
DEFAULT_TAG_COLORS = ['#E74C3C', '#8E44AD', '#3498DB', '#1ABC9C', '#F1C40F', '#E67E22', '#7F8C8D', '#2ECC71', '#34495E', '#D35400']

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.check_and_migrate_db()
        self.init_level_colors() # Renk tablosunu başlat

    def create_tables(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, tag TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS tags (name TEXT PRIMARY KEY, color TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS folder_tags (name TEXT PRIMARY KEY, color TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, folder_id INTEGER, task TEXT, is_done INTEGER, importance INTEGER, effort INTEGER, date TEXT, tag TEXT, FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, folder_id INTEGER, title TEXT, content TEXT, date TEXT, FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS weekly_schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, day_name TEXT, time_range TEXT, task TEXT, is_done INTEGER, last_completed_date TEXT)')
        # YENİ TABLO: Seviye Renkleri
        self.cursor.execute('CREATE TABLE IF NOT EXISTS level_colors (level_type TEXT, level_value INTEGER, color TEXT, PRIMARY KEY (level_type, level_value))')
        self.conn.commit()

    def check_and_migrate_db(self):
        try:
            self.cursor.execute('SELECT tag FROM todos LIMIT 1')
        except:
            try:
                self.cursor.execute('ALTER TABLE todos ADD COLUMN tag TEXT')
                self.conn.commit()
            except: pass
        try:
            self.cursor.execute('SELECT tag FROM folders LIMIT 1')
        except:
            try:
                self.cursor.execute('ALTER TABLE folders ADD COLUMN tag TEXT')
                self.conn.commit()
            except: pass

    # --- SEVİYE RENKLERİ YÖNETİMİ ---
    def init_level_colors(self):
        # Eğer tablo boşsa varsayılan renkleri doldur
        self.cursor.execute('SELECT count(*) FROM level_colors')
        if self.cursor.fetchone()[0] == 0:
            defaults = [
                # Önem (Importance) Varsayılanları
                ('imp', 5, '#c0392b'), ('imp', 4, '#e67e22'), ('imp', 3, '#f1c40f'), 
                ('imp', 2, '#2ecc71'), ('imp', 1, '#27ae60'),
                # Çaba (Effort) Varsayılanları (Hepsi gri tonları)
                ('eff', 5, '#444444'), ('eff', 4, '#444444'), ('eff', 3, '#444444'), 
                ('eff', 2, '#444444'), ('eff', 1, '#444444')
            ]
            self.cursor.executemany('INSERT INTO level_colors VALUES (?,?,?)', defaults)
            self.conn.commit()

    def get_level_colors(self):
        # Tüm renkleri çekip sözlük olarak döndür
        self.cursor.execute('SELECT level_type, level_value, color FROM level_colors')
        rows = self.cursor.fetchall()
        # Yapı: {'imp': {1: '#...', 5: '#...'}, 'eff': {...}}
        res = {'imp': {}, 'eff': {}}
        for r in rows:
            ltype, lval, col = r
            if ltype in res: res[ltype][lval] = col
        return res

    def update_level_color(self, ltype, lval, color):
        self.cursor.execute('UPDATE level_colors SET color=? WHERE level_type=? AND level_value=?', (color, ltype, lval))
        self.conn.commit()

    # --- KLASÖR İŞLEMLERİ ---
    def get_folders(self, f_type):
        self.cursor.execute('SELECT * FROM folders WHERE type=? ORDER BY id DESC', (f_type,))
        return self.cursor.fetchall()

    def add_folder(self, name, f_type, tag=''):
        if tag:
            self.cursor.execute('SELECT name FROM folder_tags WHERE name=?', (tag,))
            if not self.cursor.fetchone():
                self.add_or_update_folder_tag(tag, random.choice(DEFAULT_TAG_COLORS))
        self.cursor.execute('INSERT INTO folders (name, type, tag) VALUES (?, ?, ?)', (name, f_type, tag))
        self.conn.commit()

    def update_folder(self, folder_id, name, tag):
        if tag:
            self.cursor.execute('SELECT name FROM folder_tags WHERE name=?', (tag,))
            if not self.cursor.fetchone():
                self.add_or_update_folder_tag(tag, random.choice(DEFAULT_TAG_COLORS))
        self.cursor.execute('UPDATE folders SET name=?, tag=? WHERE id=?', (name, tag, folder_id))
        self.conn.commit()
    
    def delete_folder(self, folder_id):
        self.cursor.execute('DELETE FROM folders WHERE id=?', (folder_id,))
        self.cursor.execute('DELETE FROM todos WHERE folder_id=?', (folder_id,))
        self.cursor.execute('DELETE FROM notes WHERE folder_id=?', (folder_id,))
        self.conn.commit()

    # --- GÖREV (TODO) İŞLEMLERİ ---
    def get_todos(self, folder_id, sort_by='date', done_filter=None, tag_list=None, imp_list=None, eff_list=None):
        base_query = 'SELECT * FROM todos WHERE folder_id=?'
        params = [folder_id]
        
        if done_filter is not None:
            base_query += ' AND is_done=?'
            params.append(done_filter)
            
        if tag_list:
            placeholders = ','.join(('?' for _ in tag_list))
            base_query += f' AND tag IN ({placeholders})'
            params.extend(tag_list)
        if imp_list:
            imp_nums = [LEVELS[i] for i in imp_list]
            placeholders = ','.join(('?' for _ in imp_nums))
            base_query += f' AND importance IN ({placeholders})'
            params.extend(imp_nums)
        if eff_list:
            eff_nums = [LEVELS[e] for e in eff_list]
            placeholders = ','.join(('?' for _ in eff_nums))
            base_query += f' AND effort IN ({placeholders})'
            params.extend(eff_nums)

        if sort_by == 'importance_desc':
            query = base_query + ' ORDER BY importance DESC, id DESC'
        elif sort_by == 'importance_asc':
            query = base_query + ' ORDER BY importance ASC, id DESC'
        elif sort_by == 'effort_asc':
            query = base_query + ' ORDER BY effort ASC, id DESC'
        elif sort_by == 'effort_desc':
            query = base_query + ' ORDER BY effort DESC, id DESC'
        else:
            query = base_query + ' ORDER BY id DESC'
            
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def add_todo(self, folder_id, task, importance, effort, tag):
        date = datetime.now().strftime('%d %b, %H:%M')
        if tag:
            self.cursor.execute('SELECT name FROM tags WHERE name=?', (tag,))
            if not self.cursor.fetchone():
                self.add_or_update_task_tag(tag, random.choice(DEFAULT_TAG_COLORS))
        self.cursor.execute('INSERT INTO todos (folder_id, task, is_done, importance, effort, date, tag) VALUES (?, ?, 0, ?, ?, ?, ?)', (folder_id, task, importance, effort, date, tag))
        self.conn.commit()

    def update_todo(self, todo_id, task, importance, effort, tag):
        if tag:
            self.cursor.execute('SELECT name FROM tags WHERE name=?', (tag,))
            if not self.cursor.fetchone():
                self.add_or_update_task_tag(tag, random.choice(DEFAULT_TAG_COLORS))
        self.cursor.execute('UPDATE todos SET task=?, importance=?, effort=?, tag=? WHERE id=?', (task, importance, effort, tag, todo_id))
        self.conn.commit()

    def toggle_todo(self, todo_id, current_status):
        new_status = 1 if current_status == 0 else 0
        self.cursor.execute('UPDATE todos SET is_done=? WHERE id=?', (new_status, todo_id))
        self.conn.commit()
    
    def delete_todo(self, todo_id):
        self.cursor.execute('DELETE FROM todos WHERE id=?', (todo_id,))
        self.conn.commit()

    # --- NOT İŞLEMLERİ ---
    def get_notes(self, folder_id):
        self.cursor.execute('SELECT * FROM notes WHERE folder_id=? ORDER BY id DESC', (folder_id,))
        return self.cursor.fetchall()

    def add_note(self, folder_id, title, content):
        date = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute('INSERT INTO notes (folder_id, title, content, date) VALUES (?, ?, ?, ?)', (folder_id, title, content, date))
        self.conn.commit()

    def update_note(self, note_id, title, content):
        self.cursor.execute('UPDATE notes SET title=?, content=? WHERE id=?', (title, content, note_id))
        self.conn.commit()

    def delete_note(self, note_id):
        self.cursor.execute('DELETE FROM notes WHERE id=?', (note_id,))
        self.conn.commit()

    # --- RUTİN İŞLEMLERİ ---
    def get_weekly_tasks(self, day):
        today_str = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute('SELECT * FROM weekly_schedule WHERE day_name=? ORDER BY time_range ASC', (day,))
        tasks = self.cursor.fetchall()
        updated_tasks = []
        for task in tasks:
            t_id, t_day, t_time, t_text, t_done, t_last_date = task
            if t_done == 1 and t_last_date != today_str:
                self.cursor.execute('UPDATE weekly_schedule SET is_done=0, last_completed_date=\'\' WHERE id=?', (t_id,))
                task = (t_id, t_day, t_time, t_text, 0, '')
                self.conn.commit()
            updated_tasks.append(task)
        return updated_tasks

    def add_weekly_task(self, day, time, task):
        self.cursor.execute('INSERT INTO weekly_schedule (day_name, time_range, task, is_done, last_completed_date) VALUES (?, ?, ?, 0, \'\')', (day, time, task))
        self.conn.commit()

    def toggle_weekly_task(self, t_id, current_status):
        new_status = 1 if current_status == 0 else 0
        date_str = datetime.now().strftime('%Y-%m-%d') if new_status == 1 else ''
        self.cursor.execute('UPDATE weekly_schedule SET is_done=?, last_completed_date=? WHERE id=?', (new_status, date_str, t_id))
        self.conn.commit()

    def delete_weekly_task(self, t_id):
        self.cursor.execute('DELETE FROM weekly_schedule WHERE id=?', (t_id,))
        self.conn.commit()

    # --- ETİKET YÖNETİMİ ---
    def get_all_task_tags(self):
        self.cursor.execute('SELECT * FROM tags ORDER BY name ASC')
        return self.cursor.fetchall()
        
    def add_or_update_task_tag(self, name, color):
        self.cursor.execute('INSERT OR REPLACE INTO tags (name, color) VALUES (?, ?)', (name, color))
        self.conn.commit()

    def get_task_tag_color(self, tag_name):
        self.cursor.execute('SELECT color FROM tags WHERE name=?', (tag_name,))
        res = self.cursor.fetchone()
        return res[0] if res else '#9B59B6'

    def rename_task_tag(self, old_name, new_name):
        color = self.get_task_tag_color(old_name)
        try:
            self.cursor.execute('INSERT INTO tags (name, color) VALUES (?, ?)', (new_name, color))
            self.cursor.execute('UPDATE todos SET tag=? WHERE tag=?', (new_name, old_name))
            self.cursor.execute('DELETE FROM tags WHERE name=?', (old_name,))
            self.conn.commit()
            return True
        except: return False

    def delete_task_tag(self, tag_name):
        self.cursor.execute('DELETE FROM tags WHERE name=?', (tag_name,))
        self.cursor.execute('UPDATE todos SET tag=\'\' WHERE tag=?', (tag_name,))
        self.conn.commit()

    # Klasör Etiketleri
    def get_all_folder_tags(self):
        self.cursor.execute('SELECT * FROM folder_tags ORDER BY name ASC')
        return self.cursor.fetchall()

    def get_folder_tag_color(self, tag_name):
        self.cursor.execute('SELECT color FROM folder_tags WHERE name=?', (tag_name,))
        res = self.cursor.fetchone()
        return res[0] if res else '#34495E'

    def add_or_update_folder_tag(self, name, color):
        self.cursor.execute('INSERT OR REPLACE INTO folder_tags (name, color) VALUES (?, ?)', (name, color))
        self.conn.commit()

    def rename_folder_tag(self, old_name, new_name):
        color = self.get_folder_tag_color(old_name)
        try:
            self.cursor.execute('INSERT INTO folder_tags (name, color) VALUES (?, ?)', (new_name, color))
            self.cursor.execute('UPDATE folders SET tag=? WHERE tag=?', (new_name, old_name))
            self.cursor.execute('DELETE FROM folder_tags WHERE name=?', (old_name,))
            self.conn.commit()
            return True
        except: return False

    def delete_folder_tag(self, tag_name):
        self.cursor.execute('DELETE FROM folder_tags WHERE name=?', (tag_name,))
        self.cursor.execute('UPDATE folders SET tag=\'\' WHERE tag=?', (tag_name,))
        self.conn.commit()