import sqlite3
import os
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = os.path.join(BASE_DIR, 'grading.db')

def init_db():
    """Khởi tạo database và bảng history nếu chưa có"""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      filename TEXT,
                      total_score REAL,
                      algorithms TEXT,
                      status TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

def save_results(results: List[Dict]):
    """Lưu danh sách kết quả chấm vào database"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            for r in results:
                c.execute("INSERT INTO history (filename, total_score, algorithms, status) VALUES (?, ?, ?, ?)",
                          (r['filename'], r['total_score'], r['algorithms'], r['status']))
            
            # Xóa lịch sử cũ hơn 15 ngày
            c.execute("DELETE FROM history WHERE timestamp < datetime('now', '-15 days')")
    except Exception as e:
        print(f"Lỗi lưu DB: {e}")

def get_recent_history(limit: int = 50) -> List[Dict]:
    """Lấy danh sách lịch sử gần nhất"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))
        data = [dict(row) for row in c.fetchall()]
    return data
