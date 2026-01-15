import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'grading.db')

def view_history():
    if not os.path.exists(DB_PATH):
        print(" Chưa có file database (grading.db). Hãy chấm thử vài bài trước.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Lấy dữ liệu
    try:
        c.execute("SELECT id, timestamp, filename, total_score, status FROM history ORDER BY id DESC LIMIT 20")
        rows = c.fetchall()
        
        if not rows:
            print("📭 Database có file nhưng chưa có dữ liệu nào.")
            return

        print(f"{'ID':<5} | {'THỜI GIAN':<20} | {'TÊN FILE':<30} | {'ĐIỂM':<6} | {'TRẠNG THÁI'}")
        print("-" * 85)
        for r in rows:
            # Cắt ngắn tên file nếu quá dài để bảng không bị vỡ
            fname = (r[2][:27] + '..') if len(r[2]) > 29 else r[2]
            print(f"{r[0]:<5} | {r[1]:<20} | {fname:<30} | {r[3]:<6} | {r[4]}")
    except sqlite3.OperationalError:
        print(" Lỗi đọc bảng history. Database có thể bị hỏng hoặc chưa khởi tạo đúng.")
    finally:
        conn.close()

def clear_history():
    confirm = input("Bạn có chắc muốn XÓA TOÀN BỘ lịch sử chấm điểm? (y/n): ")
    if confirm.lower() == 'y':
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
                print("Đã xóa file database thành công. Hệ thống sẽ tự tạo mới khi chấm bài tiếp theo.")
            except PermissionError:
                print("Không thể xóa file. Hãy đảm bảo server hoặc phần mềm khác không đang mở file này.")
        else:
            print("⚠️ File database không tồn tại.")
    else:
        print("Đã hủy thao tác.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_history()
    else:
        view_history()
        print("\n Mẹo: Chạy 'python view_db.py clear' để xóa sạch lịch sử.")