# app/services.py
import requests
import os

# 1. URL của Microservice bạn đã deploy
QUESTION_BANK_API_URL = "https://api-dsa-python.onrender.com"

# 2. Lấy chìa khóa từ Environment của Render (phải đặt giống nhau ở cả 2 service)
MY_SECRET_KEY = os.getenv("MY_SECRET_KEY", "default-key")

def fetch_problem_from_bank(topic_id: str):
    if not topic_id: return None
    
    # 3. XÓA ĐUÔI .py ĐỂ KHỚP VỚI DATABASE
    clean_id = topic_id.replace(".py", "")
    
    try:
        # 4. GỬI KÈM CHÌA KHÓA TRONG HEADER
        headers = {"x-api-key": MY_SECRET_KEY}
        url = f"{QUESTION_BANK_API_URL}/problems/{clean_id}"
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return None
