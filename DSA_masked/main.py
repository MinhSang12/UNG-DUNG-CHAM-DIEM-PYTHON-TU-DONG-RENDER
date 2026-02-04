import asyncio
import io
import os
import sys
import time
import zipfile
from typing import List
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from app.grader import AIGrader
from app.storage import save_results_to_csv, get_history_csv_data, get_csv_file_path

from fastapi.responses import FileResponse
from fastapi import Request


# --- CẤU HÌNH ĐƯỜNG DẪN ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import rarfile
except ImportError:
    rarfile = None

app = FastAPI(
    title="DSA AutoGrader API",
    description="Hệ thống chấm điểm AI chủ đạo tích hợp phân tích kỹ thuật AST.",
    version="3.0"
)


# --- CẤU HÌNH CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KHỞI TẠO ---
# Sử dụng AIGrader làm engine duy nhất
grader = AIGrader()
ai_semaphore = asyncio.Semaphore(50)

# CẬP NHẬT: Chỉ còn một luồng chấm điểm AI duy nhất (AST đã chạy song song bên trong)
async def grade_with_limit(code, filename, topic=None):
    async with ai_semaphore:
        # Gọi hàm grade_auto đã được tối ưu để lấy tiêu chí từ ngân hàng bài tập làm ưu tiên số 1
        return await grader.grade_auto(code, filename, topic=topic)

@app.on_event("startup")
async def startup_check():
    print("\n--- HỆ THỐNG KHỞI ĐỘNG (LUỒNG CHẤM AI THỐNG NHẤT) ---")

@app.post("/grade", summary="Chấm điểm AI chuyên sâu")
async def grade_lightning(
    request: Request, # Thêm tham số request vào đây
    files: List[UploadFile] = File(...), 
    topic: str = Form(None),
    student_name: str = Form("Ẩn danh")
):
    start_total = time.time()
    results = []
    grading_tasks = []
    
    print(f"--- Bắt đầu chấm {len(files)} file cho: {student_name} (Chủ đề: {topic}) ---")

    for file in files:
        filename_lower = file.filename.lower()
        
        # 1. Xử lý file .py lẻ
        if filename_lower.endswith('.py'):
            content = await file.read()
            code = content.decode('utf-8', errors='ignore')
            grading_tasks.append(grade_with_limit(code, file.filename, topic))

        # 2. Xử lý file nén (.zip/.rar)
        elif filename_lower.endswith(('.zip', '.rar')):
            try:
                content = await file.read()
                # Tận dụng logic xử lý file nén cũ của bạn nhưng chỉ gọi grade_with_limit duy nhất
                if filename_lower.endswith('.zip'):
                    z = zipfile.ZipFile(io.BytesIO(content))
                    for member in z.namelist():
                        if not member.endswith('/') and member.lower().endswith('.py'):
                            with z.open(member) as f:
                                code = f.read().decode('utf-8', errors='ignore')
                                grading_tasks.append(grade_with_limit(code, f"{file.filename}/{member}", topic))
                elif filename_lower.endswith('.rar') and rarfile:
                    with rarfile.RarFile(io.BytesIO(content)) as rf:
                        for member in rf.namelist():
                            if member.lower().endswith('.py'):
                                code = rf.read(member).decode('utf-8', errors='ignore')
                                grading_tasks.append(grade_with_limit(code, f"{file.filename}/{member}", topic))
            except Exception as e:
                results.append({'filename': file.filename, 'status': 'WA', 'error': f'Lỗi đọc tệp nén: {str(e)}'})

    # --- THỰC THI CHẤM ĐIỂM AI ---
    if grading_tasks:
        # Kiểm tra nếu người dùng đã ngắt kết nối trước khi bắt đầu gather
        if await request.is_disconnected():
            print("🛑 Người dùng đã hủy, dừng tiến trình!")
            return {"status": "cancelled"}
            
        graded_results = await asyncio.gather(*grading_tasks)
        results.extend(graded_results)

    # --- KIỂM TRA ĐẠO VĂN (Sử dụng vân tay AST do AI thu thập song song) ---
    for i in range(len(results)):
        if 'fingerprint' not in results[i]: continue
        for j in range(i + 1, len(results)):
            if 'fingerprint' not in results[j]: continue
            fp1, fp2 = results[i]['fingerprint'], results[j]['fingerprint']
            similarity = len(fp1 & fp2) / len(fp1 | fp2) if (fp1 | fp2) else 0
            if similarity > 0.8:
                results[i]['status'] = results[j]['status'] = 'FLAG'
                results[i]['notes'].append(f"Nghi vấn đạo văn: Giống {results[j]['filename']} {similarity:.0%}")

    # Chuẩn bị dữ liệu cuối cùng cho báo cáo CSV
    for r in results: 
        r.pop('fingerprint', None)
        r['filename'] = f"{student_name} | {r['filename']}"

    save_results_to_csv(results)
    total_time = time.time() - start_total
    
    return {
        "results": results,
        "summary": {
            "total_files": len(results),
            "avg_score": round(sum(r.get('total_score', 0) for r in results) / len(results), 1) if results else 0,
            "total_time": f"{total_time*1000:.0f}ms"
        }
    }

@app.get("/download-csv")
async def download_csv():
    path = get_csv_file_path()
    return FileResponse(path, media_type='text/csv', filename='ket_qua_dsa.csv') if path else HTMLResponse("Trống", 404)

@app.get("/api/history")
async def get_history_csv():
    return get_history_csv_data()

# main.py - Sửa lại hàm home

@app.get("/", response_class=HTMLResponse)
async def home():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "app", "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse("❌ Không thấy index.html", status_code=404)

@app.get("/results", response_class=HTMLResponse)
async def results_page():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "app", "results.html") # Đảm bảo bạn để file results.html trong thư mục app
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse("❌ Không thấy results.html", status_code=404)
