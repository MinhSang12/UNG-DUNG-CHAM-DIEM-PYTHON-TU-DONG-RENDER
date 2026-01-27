from fastapi import FastAPI, HTTPException
import pymssql
from typing import Dict, List
import json
import uvicorn

app = FastAPI(title="DSA Question Bank API")

def get_db_connection():
    return pymssql.connect(
        server='118.69.126.49',
        user='userPersonalizedSystem',
        password='123456789',
        database='Data_PersonalizedSystem'
    )

@app.get("/problems/{ma_bai_tap}")
async def get_problem_details(ma_bai_tap: str):
    """
    Lấy dữ liệu từ bảng BAITAP để AI có cơ sở chấm điểm
    """
    
    try:
        clean_id = ma_bai_tap.replace(".py", "")
        conn = get_db_connection()
        cursor = conn.cursor(as_dict=True)
            # 1. Truy vấn lấy dữ liệu từ bảng BAITAP
        query = """
                SELECT TenBaiTap, MoTa, YeuCau, TieuChiChamDiem 
                FROM BAITAP 
                WHERE MaBaiTap = %s
            """
        cursor.execute(query, (clean_id,))
        row = cursor.fetchone()
            
        if not row:
                raise HTTPException(status_code=404, detail="Không tìm thấy mã bài tập này")
            
            # 2. Xử lý cột TieuChiChamDiem (Dạng JSON trong DB)
        raw_rubric = row['TieuChiChamDiem']
        formatted_rubric = "Chấm theo tiêu chuẩn DSA chung."
        test_cases = [{"input": "5", "expected": "120"}] # Mặc định dự phòng
            
        if raw_rubric:
                try:
                    rubric_obj = json.loads(raw_rubric)
                    # Lấy danh sách tiêu chí từ mảng "tieu chi" trong JSON
                    criteria_list = rubric_obj.get("tieu chi", [])
                    if criteria_list:
                        formatted_rubric = ". ".join(criteria_list)
                    
                    # Nếu bạn đã gộp Test Cases vào cột này (Hướng xử lý khi không tạo được bảng)
                    if "test_cases" in rubric_obj:
                        test_cases = rubric_obj["test_cases"]
                except Exception as e:
                    print(f"⚠️ Lỗi parse JSON tiêu chí: {e}")
                    formatted_rubric = raw_rubric # Nếu không phải JSON thì lấy text thuần

            # 3. Trả về cấu trúc JSON chuẩn cho bộ Grader
        return {
                "id": ma_bai_tap,
                "title": row['TenBaiTap'],
                "description": row['MoTa'],
                "requirements": row['YeuCau'],     # Yêu cầu đề bài thực tế
                "rubric": formatted_rubric,      # Tiêu chí đã được làm sạch để AI đọc
                "time_limit": 2.0,
                "test_cases": test_cases         # Bộ test để máy chạy thực tế
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

if __name__ == "__main__":
    # Chạy API tại cổng 8001 như services.py yêu cầu
    uvicorn.run(app, host="127.0.0.1", port=8001)