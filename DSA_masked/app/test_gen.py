import os
import glob
from typing import List, Dict

# Xác định đường dẫn thư mục testcases (nằm ngang hàng với thư mục app)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTCASE_ROOT = os.path.join(BASE_DIR, 'testcases')

def get_test_cases(filename: str, topic: str = None) -> List[Dict]:
    """
    Sinh test case dựa trên tên file nộp.
    Đọc test case từ thư mục 'testcases/' dựa trên tên file nộp.
    Cấu trúc: testcases/{loại_bài}/input_x.txt và output_x.txt
    Trả về list các dict: {'input': str, 'expected': str, 'name': str}
    """
    fname = filename.lower()
    tests = []

    # Mapping từ khóa trong tên file -> tên thư mục trong testcases
    # Ví dụ: file nộp là "bai_tap_sort_bubble.py" -> tìm trong folder "testcases/sort"
    mapping = {
        'sort': 'sort', 'sap_xep': 'sort', 'bubble': 'sort', 'quick': 'sort', 'merge': 'sort',
        'search': 'search', 'tim_kiem': 'search', 'binary': 'search',
        'fibo': 'fibonacci', 'fibonacci': 'fibonacci',
        'fact': 'factorial', 'giai_thua': 'factorial',
        'prime': 'prime', 'nguyen_to': 'prime',
        'knapsack': 'knapsack', 'cai_tui': 'knapsack', 'dp': 'knapsack',
        'graph': 'graph', 'do_thi': 'graph', 'bfs': 'graph', 'dfs': 'graph', 'dijkstra': 'graph',
        'lcs': 'lcs', 'xau_con': 'lcs', 'string': 'lcs',
        'matrix': 'matrix', 'luoi': 'matrix', 'island': 'matrix',
        'nqueen': 'nqueen', 'hau': 'nqueen', 'backtrack': 'nqueen',
        'mst': 'mst', 'kruskal': 'mst', 'prim': 'mst', 'cay_khung': 'mst'
    }

    target_folder = None
    
    # Ưu tiên 1: Nếu người dùng chọn topic cụ thể
    if topic and topic in mapping.values():
        target_folder = topic
    else:
        # Ưu tiên 2: Đoán qua tên file
        for key, folder in mapping.items():
            if key in fname:
                target_folder = folder
                break
    
    if not target_folder:
        return []

    folder_path = os.path.join(TESTCASE_ROOT, target_folder)
    if not os.path.exists(folder_path):
        return []

    # Quét tất cả file input_*.txt và tìm output tương ứng
    input_files = sorted(glob.glob(os.path.join(folder_path, 'input_*.txt')))
    
    for inp_file in input_files:
        out_file = inp_file.replace('input_', 'output_')
        
        if os.path.exists(out_file):
            try:
                with open(inp_file, 'r', encoding='utf-8') as f:
                    input_data = f.read().strip()
                with open(out_file, 'r', encoding='utf-8') as f:
                    expected_data = f.read().strip()
                
                # Lấy tên test case từ tên file (vd: input_1.txt -> 1)
                test_name = os.path.basename(inp_file).replace('input_', '').replace('.txt', '')
                
                tests.append({
                    "name": f"Test {test_name}",
                    "input": input_data,
                    "expected": expected_data
                })
            except Exception:
                continue

    return tests