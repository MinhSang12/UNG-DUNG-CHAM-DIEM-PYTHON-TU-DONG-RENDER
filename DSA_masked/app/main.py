from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from typing import List
from app.grader import AIGrader
from app.storage import save_results_to_csv, get_history_csv_data, get_csv_file_path
import time
import io
import zipfile
import os
import asyncio
try:
    import rarfile
except ImportError:
    rarfile = None

app = FastAPI(title="Hệ thống chấm điểm Python tự động")

# Cấu hình CORS: Cho phép các hệ thống bên ngoài (như Firebase Web App) gọi vào API này
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong thực tế, bạn nên thay "*" bằng domain cụ thể của Firebase App để bảo mật hơn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo AI Grader (Bạn nhớ set biến môi trường GEMINI_API_KEY nhé)
grader = AIGrader()

# GIỚI HẠN CONCURRENT REQUEST: Chỉ cho phép 2 request AI chạy cùng lúc để tránh lỗi 429
ai_semaphore = asyncio.Semaphore(2)

async def grade_with_limit(code, filename):
    async with ai_semaphore:
        return await grader.grade_with_ai(code, filename)

@app.on_event("startup")
async def startup_check():
    print("\n--- HỆ THỐNG KHỞI ĐỘNG ---")

@app.post("/grade")
async def grade_lightning(files: List[UploadFile] = File(...)):
    start_total = time.time()
    results = []
    grading_tasks = []
    print(f"--- Bắt đầu chấm {len(files)} file ---")

    for file in files:
        filename_lower = file.filename.lower()
        # Single .py file
        if filename_lower.endswith('.py'):
            content = await file.read()
            code = content.decode('utf-8', errors='ignore')
            # Đẩy vào thread pool để chạy song song
            grading_tasks.append(grade_with_limit(code, file.filename))

        # ZIP archive: extract contained .py files and grade them
        elif filename_lower.endswith('.zip'):
            try:
                content = await file.read()
                z = zipfile.ZipFile(io.BytesIO(content))
                for member in z.namelist():
                    # skip directories
                    if member.endswith('/'):
                        continue
                    if member.lower().endswith('.py'):
                        with z.open(member) as f:
                            try:
                                code_bytes = f.read()
                                code = code_bytes.decode('utf-8', errors='ignore')
                            except Exception:
                                code = ''
                            display_name = os.path.basename(member) or member
                            grading_tasks.append(grade_with_limit(code, display_name))
            except zipfile.BadZipFile:
                # return a safe error entry so front-end can display a row
                results.append({
                    'filename': file.filename,
                    'total_score': 0,
                    'breakdown': {'pep8': 0, 'dsa': 0, 'complexity': 0, 'tests': 0},
                    'algorithms': '',
                    'runtime': '0ms',
                    'status': 'WA',
                    'error': 'Tệp ZIP không hợp lệ'
                })

        # RAR archive
        elif filename_lower.endswith('.rar'):
            if rarfile is None:
                results.append({
                    'filename': file.filename, 'total_score': 0, 'breakdown': {'pep8': 0, 'dsa': 0, 'complexity': 0, 'tests': 0},
                    'algorithms': '', 'runtime': '0ms', 'status': 'WA', 'notes': ['Server chưa cài thư viện "rarfile" (pip install rarfile)'], 'error': 'Thiếu thư viện'
                })
            else:
                try:
                    content = await file.read()
                    with rarfile.RarFile(io.BytesIO(content)) as rf:
                        for member in rf.namelist():
                            if member.lower().endswith('.py'):
                                try:
                                    code = rf.read(member).decode('utf-8', errors='ignore')
                                    display_name = os.path.basename(member) or member
                                    grading_tasks.append(grade_with_limit(code, display_name))
                                except: pass
                except Exception as e:
                    results.append({
                        'filename': file.filename, 'total_score': 0, 'breakdown': {'pep8': 0, 'dsa': 0, 'complexity': 0, 'tests': 0},
                        'algorithms': '', 'runtime': '0ms', 'status': 'WA', 'notes': [f'Lỗi đọc RAR: {str(e)}'], 'error': 'Lỗi file RAR'
                    })

    # Chạy tất cả các task chấm điểm song song
    if grading_tasks:
        print(f"Đang gửi {len(grading_tasks)} request lên AI song song...")
        graded_results = await asyncio.gather(*grading_tasks)
        results.extend(graded_results)

    # PLAGIARISM DETECTION (So sánh chéo các bài nộp)
    for i in range(len(results)):
        if 'fingerprint' not in results[i]: continue
        for j in range(i + 1, len(results)):
            if 'fingerprint' not in results[j]: continue
            
            fp1, fp2 = results[i]['fingerprint'], results[j]['fingerprint']
            if not fp1 or not fp2: continue
            
            # Jaccard Similarity: (Giao / Hợp)
            similarity = len(fp1 & fp2) / len(fp1 | fp2)
            if similarity > 0.8: # Ngưỡng 80%
                results[i]['status'] = 'FLAG'
                results[i]['notes'].append(f"Giống {results[j]['filename']} ({similarity:.0%})")
                results[j]['status'] = 'FLAG'
                results[j]['notes'].append(f"Giống {results[i]['filename']} ({similarity:.0%})")

    # Cleanup fingerprints (không gửi về frontend)
    for r in results: r.pop('fingerprint', None)

    # LƯU KẾT QUẢ VÀO FILE CSV (Sử dụng module storage)
    save_results_to_csv(results)

    total_time = time.time() - start_total
    print(f"--- Hoàn tất trong {total_time:.2f}s ---")

    total_files = len(results)
    avg_score = round(sum(r.get('total_score', 0) for r in results) / total_files, 1) if total_files else 0

    return {
        "results": results,
        "summary": {
            "total_files": total_files,
            "avg_score": avg_score,
            "total_time": f"{total_time*1000:.0f}ms",
            "speed": f"{total_files/(total_time+0.001):.1f} tệp/s"
        }
    }

@app.get("/download-csv")
async def download_csv():
    path = get_csv_file_path()
    if path:
        return FileResponse(path, media_type='text/csv', filename='ket_qua_cham.csv')
    return HTMLResponse("Chưa có dữ liệu chấm điểm nào.", status_code=404)

@app.get("/api/history")
async def get_history_csv():
    return get_history_csv_data()

@app.get("/", response_class=HTMLResponse)
async def home():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
