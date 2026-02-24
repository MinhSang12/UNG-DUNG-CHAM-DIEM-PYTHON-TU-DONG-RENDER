import os

# Dữ liệu Test Case chuẩn (Input -> Output)
TEST_DATA = {
    # 1. CƠ BẢN: Giai thừa
    "factorial": {
        "input_1.txt": "0", "output_1.txt": "1",
        "input_2.txt": "5", "output_2.txt": "120",
        "input_3.txt": "10", "output_3.txt": "3628800"
    },
    # 2. CƠ BẢN: Fibonacci
    "fibonacci": {
        "input_1.txt": "0", "output_1.txt": "0",
        "input_2.txt": "1", "output_2.txt": "1",
        "input_3.txt": "10", "output_3.txt": "55",
        "input_4.txt": "19", "output_4.txt": "4181"
    },
    # 3. CƠ BẢN: Số nguyên tố
    "prime": {
        "input_1.txt": "2", "output_1.txt": "True",
        "input_2.txt": "4", "output_2.txt": "False",
        "input_3.txt": "17", "output_3.txt": "True",
        "input_4.txt": "1", "output_4.txt": "False"
    },
    # 4. TRUNG CẤP: Sắp xếp (Sort)
    # Format: N \n Mảng
    "sort": {
        "input_1.txt": "5\n5 1 4 2 8",
        "output_1.txt": "1 2 4 5 8",
        "input_2.txt": "6\n10 9 8 7 6 5",
        "output_2.txt": "5 6 7 8 9 10",
        "input_3.txt": "1\n100",
        "output_3.txt": "100",
        "input_4.txt": "8\n-5 10 0 -2 5 1 3 -1",
        "output_4.txt": "-5 -2 -1 0 1 3 5 10"
    },
    # 5. TRUNG CẤP: Tìm kiếm (Search)
    # Format: N \n Mảng \n Target -> Output: Index (hoặc -1)
    "search": {
        "input_1.txt": "5\n1 3 5 7 9\n5",
        "output_1.txt": "2",
        "input_2.txt": "5\n1 3 5 7 9\n10",
        "output_2.txt": "-1",
        "input_3.txt": "1\n10\n10",
        "output_3.txt": "0"
    },
    # 6. NÂNG CAO: Quy hoạch động (Knapsack - Cái túi)
    # Format: Capacity \n N \n Weights \n Values -> Output: Max Value
    "knapsack": {
        "input_1.txt": "50\n3\n10 20 30\n60 100 120",
        "output_1.txt": "220",
        "input_2.txt": "10\n1\n20\n100",
        "output_2.txt": "0", # Không vừa
        "input_3.txt": "8\n4\n2 3 4 5\n3 4 5 6",
        "output_3.txt": "10" # Chọn vật 2 (3kg, val 4) + vật 4 (5kg, val 6) = 8kg, val 10
    },
    # 7. NÂNG CAO: Đồ thị (Graph - Shortest Path BFS)
    # Bài toán: Tìm khoảng cách ngắn nhất từ Start đến End
    # Format: Nodes Edges Start End \n u v (các cạnh)...
    "graph": {
        # Đồ thị: 0-1, 0-2, 1-2. Tìm đường từ 0 đến 2. Ngắn nhất là 0->2 (1 bước)
        "input_1.txt": "3 3 0 2\n0 1\n0 2\n1 2",
        "output_1.txt": "1",
        
        # Đồ thị đường thẳng: 0-1-2-3-4. Tìm 0 đến 4. (4 bước)
        "input_2.txt": "5 4 0 4\n0 1\n1 2\n2 3\n3 4",
        "output_2.txt": "4",
        
        # Không có đường đi: 0-1, 2-3. Tìm 0 đến 3. (-1)
        "input_3.txt": "4 2 0 3\n0 1\n2 3",
        "output_3.txt": "-1"
    },
    # 8. NÂNG CAO: Xử lý chuỗi (LCS - Longest Common Subsequence)
    # Format: String1 \n String2 -> Output: Length
    "lcs": {
        "input_1.txt": "abcde\nace", "output_1.txt": "3", # ace
        "input_2.txt": "abc\nabc", "output_2.txt": "3",
        "input_3.txt": "abc\ndef", "output_3.txt": "0"
    },
    # 9. NÂNG CAO: Ma trận (Number of Islands - Đếm số đảo)
    # Format: Rows Cols \n Matrix (0/1) -> Output: Count
    "matrix": {
        "input_1.txt": "4 5\n1 1 1 1 0\n1 1 0 1 0\n1 1 0 0 0\n0 0 0 0 0",
        "output_1.txt": "1",
        "input_2.txt": "4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1",
        "output_2.txt": "3"
    },
    # 10. CHUYÊN SÂU: Backtracking (N-Queens)
    # Format: N (kích thước bàn cờ) -> Output: Số lượng cách xếp
    "nqueen": {
        "input_1.txt": "4", "output_1.txt": "2",
        "input_2.txt": "1", "output_2.txt": "1",
        "input_3.txt": "8", "output_3.txt": "92"
    },
    # 11. CHUYÊN SÂU: Cây khung nhỏ nhất (MST - Kruskal/Prim)
    # Format: Nodes Edges \n u v w (weight) -> Output: Min Weight
    "mst": {
        # 0-1(1), 1-2(2), 0-2(3) -> Chọn 0-1 và 1-2 -> Tổng 3
        "input_1.txt": "3 3\n0 1 1\n1 2 2\n0 2 3",
        "output_1.txt": "3",
        # 0-1(10), 0-2(6), 0-3(5), 1-3(15), 2-3(4) -> Chọn 2-3(4), 0-3(5), 0-1(10) -> Sai.
        # MST: 2-3(4), 0-3(5), 0-1(10) -> Tổng 19? Check: 0-3(5), 3-2(4), 0-1(10). Total 19.
        "input_2.txt": "4 5\n0 1 10\n0 2 6\n0 3 5\n1 3 15\n2 3 4",
        "output_2.txt": "19"
    }
}

def create_testcases():
    # Xác định đường dẫn gốc (chính là thư mục chứa file này)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f" Đang tạo test cases tại: {base_dir}")

    total_files = 0
    for folder, files in TEST_DATA.items():
        folder_path = os.path.join(base_dir, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        for filename, content in files.items():
            file_path = os.path.join(folder_path, filename)
            # Ghi file với encoding utf-8 và newline chuẩn
            with open(file_path, "w", encoding="utf-8", newline='\n') as f:
                f.write(content.strip())
            total_files += 1
            
        print(f"   {folder}: Đã tạo {len(files)//2} test cases")

    print(f"\n HOÀN TẤT! Đã tạo tổng cộng {total_files} file trong thư mục hiện tại.")
    print(" Bây giờ bạn có thể nộp file code (ví dụ: 'bai_tap_graph.py', 'quick_sort.py') để chấm.")

if __name__ == "__main__":
    create_testcases()