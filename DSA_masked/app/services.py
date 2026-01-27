# app/services.py
import requests
from typing import Optional, Dict
import os

# URL trỏ đến API bạn vừa khởi chạy ở trên
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") 
if RENDER_EXTERNAL_URL:
    # URL trên Render (đã mount /db-api trong main.py)
    QUESTION_BANK_API_URL = f"{RENDER_EXTERNAL_URL}/db-api"
else:
    # URL khi chạy ở máy cá nhân
    QUESTION_BANK_API_URL = "http://127.0.0.1:8000/db-api"

def fetch_problem_from_bank(topic_id: str) -> Optional[Dict]:
    if not topic_id: return None
    try:
        # Gọi đến endpoint /problems/{id} của bank_api.py
        response = requests.get(f"{QUESTION_BANK_API_URL}/problems/{topic_id}", timeout=5)
        print(f"📡 Đang gọi API tại: {response}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ Không kết nối được API Ngân hàng bài tập: {e}")
    return None