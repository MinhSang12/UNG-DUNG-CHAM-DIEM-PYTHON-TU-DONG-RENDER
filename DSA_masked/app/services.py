# app/services.py
import requests
from typing import Optional, Dict

# URL trỏ đến API bạn vừa khởi chạy ở trên
QUESTION_BANK_API_URL = "http://127.0.0.1:8001/api"

def fetch_problem_from_bank(topic_id: str) -> Optional[Dict]:
    if not topic_id: return None
    try:
        # Gọi đến endpoint /problems/{id} của bank_api.py
        response = requests.get(f"{QUESTION_BANK_API_URL}/problems/{topic_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ Không kết nối được API Ngân hàng bài tập: {e}")
    return None