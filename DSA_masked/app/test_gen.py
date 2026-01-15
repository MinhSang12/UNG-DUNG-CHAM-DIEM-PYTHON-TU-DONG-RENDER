import random

def get_test_cases(filename):
    """
    Sinh test case dựa trên tên file nộp.
    Trả về list các dict: {'input': str, 'expected': str, 'name': str}
    """
    fname = filename.lower()
    tests = []

    # 1. BÀI TOÁN SẮP XẾP (Sort)
    # Nhận diện qua tên file có chứa: sort, sap_xep, bubble, quick...
    if any(x in fname for x in ['sort', 'sap_xep', 'bubble', 'quick', 'merge', 'insertion']):
        # Test 1: Random ngẫu nhiên
        arr = [random.randint(1, 100) for _ in range(10)]
        tests.append({
            "name": "Random Array",
            "input": f"{len(arr)}\n{' '.join(map(str, arr))}",
            "expected": ' '.join(map(str, sorted(arr)))
        })
        # Test 2: Mảng ngược (Trường hợp khó)
        arr = list(range(10, 0, -1))
        tests.append({
            "name": "Reverse Array",
            "input": f"{len(arr)}\n{' '.join(map(str, arr))}",
            "expected": ' '.join(map(str, sorted(arr)))
        })
        # Test 3: Mảng đã sắp xếp sẵn
        arr = [1, 2, 3, 4, 5]
        tests.append({
            "name": "Sorted Array",
            "input": f"{len(arr)}\n{' '.join(map(str, arr))}",
            "expected": ' '.join(map(str, sorted(arr)))
        })

    # 2. BÀI TOÁN TÌM KIẾM (Search)
    # Nhận diện qua tên file: search, tim_kiem, binary, linear...
    elif any(x in fname for x in ['search', 'tim_kiem', 'binary', 'linear']):
        # Test 1: Tìm thấy phần tử
        arr = sorted([random.randint(1, 50) for _ in range(10)]) # Binary search yêu cầu mảng sorted
        target = arr[5] # Lấy phần tử ở giữa để tìm
        tests.append({
            "name": "Found Item",
            "input": f"{len(arr)}\n{' '.join(map(str, arr))}\n{target}",
            "expected": str(5) # Kỳ vọng trả về index 5
        })
        # Test 2: Không tìm thấy
        target = 1000
        tests.append({
            "name": "Not Found",
            "input": f"{len(arr)}\n{' '.join(map(str, arr))}\n{target}",
            "expected": "-1"
        })

    return tests