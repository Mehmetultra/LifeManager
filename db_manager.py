import sqlite3
from datetime import datetime
import random

DB_NAME = 'lifemanager_db.sqlite'
DEFAULT_TAG_COLORS = ['#E74C3C', '#8E44AD', '#3498DB', '#1ABC9C', '#F1C40F', '#E67E22', '#7F8C8D', '#2ECC71', '#34495E', '#D35400']
LEVELS = {'Çok Düşük': 1, 'Düşük': 2, 'Orta': 3, 'Yüksek': 4, 'Çok Yüksek': 5}

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, tag TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS tags (name TEXT PRIMARY KEY, color TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS folder_tags (name TEXT PRIMARY KEY, color TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, folder_id INTEGER, task TEXT, is_done INTEGER, importance INTEGER, effort INTEGER, date TEXT, tag TEXT, FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, folder_id INTEGER, title TEXT, content TEXT, date TEXT, FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS weekly_schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, day_name TEXT, time_range TEXT, task TEXT, is_done INTEGER, last_completed_date TEXT)')
        self.conn.commit()

    def get_folders(self, f_type):
        self.cursor.execute('SELECT * FROM folders WHERE type=? ORDER BY id DESC', (f_type,))
        return self.cursor.fetchall()

    def add_folder(self, name, f_type, tag=''):
        self.cursor.execute('INSERT INTO folders (name, type, tag) VALUES (?, ?, ?)', (name, f_type, tag))
        self.conn.commit()

    def get_todos(self, folder_id, done_filter=None):
        query = 'SELECT * FROM todos WHERE folder_id=?'
        params = [folder_id]
        if done_filter is not None:
            query += ' AND is_done=?'
            params.append(done_filter)
        query += ' ORDER BY importance DESC' # Varsayılan sıralama
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def add_todo(self, folder_id, task, importance, effort, tag):
        date = datetime.now().strftime('%d %b, %H:%M')
        self.cursor.execute('INSERT INTO todos (folder_id, task, is_done, importance, effort, date, tag) VALUES (?, ?, 0, ?, ?, ?, ?)', (folder_id, task, importance, effort, date, tag))
        self.conn.commit()

    def toggle_todo(self, todo_id, current_status):
        new_status = 1 if current_status == 0 else 0
        self.cursor.execute('UPDATE todos SET is_done=? WHERE id=?', (new_status, todo_id))
        self.conn.commit()
    
    def delete_todo(self, todo_id):
        self.cursor.execute('DELETE FROM todos WHERE id=?', (todo_id,))
        self.conn.commit()
        
    # Not: Diğer tüm fonksiyonların buraya eklendiğini varsayıyorum.
    # Şimdilik Streamlit demosu için bunlar yeterli.