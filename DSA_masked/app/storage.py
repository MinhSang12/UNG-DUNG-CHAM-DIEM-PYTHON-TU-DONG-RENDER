import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

CSV_FILE = 'ket_qua_cham.csv'
MAX_HISTORY_ROWS = 2000  # Giới hạn cứng: Chỉ lưu tối đa 2000 dòng để file luôn nhẹ

def get_csv_file_path() -> Optional[str]:
    return CSV_FILE if os.path.exists(CSV_FILE) else None

def save_results_to_csv(results: List[Dict]):
    """Lưu kết quả chấm vào file CSV, giữ lại dữ liệu 15 ngày gần nhất"""
    try:
        rows_to_keep = []
        header = ['Thời gian', 'Tên file', 'Điểm số', 'Thuật toán', 'Trạng thái', 'Ghi chú']
        
        # Đọc dữ liệu cũ
        if os.path.exists(CSV_FILE):
            try:
                with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    h = next(reader, None)
                    if h: header = h
                    
                    limit_date = datetime.now() - timedelta(days=15)
                    for row in reader:
                        if row and len(row) > 0:
                            try:
                                row_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                                if row_time >= limit_date:
                                    rows_to_keep.append(row)
                            except ValueError:
                                continue
            except Exception: pass
        
        # CHỐT CHẶN AN TOÀN: Nếu lịch sử quá dài (>2000 dòng), cắt bớt phần cũ nhất
        if len(rows_to_keep) > MAX_HISTORY_ROWS:
            rows_to_keep = rows_to_keep[-MAX_HISTORY_ROWS:]

        # Thêm kết quả mới
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for r in results:
            rows_to_keep.append([
                now,
                r['filename'],
                r['total_score'],
                r['algorithms'],
                r['status'],
                "; ".join(r.get('notes', []))
            ])

        # Ghi lại toàn bộ file
        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows_to_keep)
            
        print(f" Đã lưu kết quả vào {CSV_FILE} (Lưu trữ 15 ngày)")
    except Exception as e:
        print(f" Lỗi lưu CSV: {e}")

def get_history_csv_data(limit: int = 50) -> List[Dict]:
    """Đọc lịch sử từ CSV"""
    results = []
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                results = list(reader)[::-1][:limit] # Lấy dòng mới nhất
        except Exception: pass
    return results