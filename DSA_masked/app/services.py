# app/services.py
import requests
from typing import Optional, Dict
import os

# 1. CẤU HÌNH LIÊN KẾT MICROSERVICE
# Lấy URL của Web Service GetAPI riêng biệt trên Render
QUESTION_BANK_API_URL = os.getenv("BANK_API_URL", "http://127.0.0.1:8001")

# Lấy chìa khóa bí mật để được quyền truy cập vào API
MY_SECRET_KEY = os.getenv("MY_SECRET_KEY", "default-key")

def fetch_problem_from_bank(topic_id: str) -> Optional[Dict]:
    if not topic_id:
        return None
    
    try:
        # 2. THIẾT LẬP HEADER BẢO MẬT
        # Gửi kèm chìa khóa để Microservice GetAPI xác nhận quyền truy cập
        headers = {
            "x-api-key": MY_SECRET_KEY 
        }

        # 3. GỌI API QUA INTERNET
        # Thay vì gọi local, giờ đây nó gọi tới URL của Microservice
        url = f"{QUESTION_BANK_API_URL}/problems/{topic_id}"
        
        print(f"🚀 Đang gọi Microservice tại: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("❌ Lỗi: Sai API Key, không thể lấy dữ liệu!")
        else:
            print(f"⚠️ API trả về lỗi: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Không kết nối được API Ngân hàng bài tập: {e}")
    
    return None
