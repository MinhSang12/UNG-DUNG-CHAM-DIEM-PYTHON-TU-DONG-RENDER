import unittest
import sys
import os

# Thêm thư mục hiện tại vào path để import được app.grader
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.grader import DSALightningGrader

class TestDSALightningGrader(unittest.TestCase):
    def setUp(self):
        self.grader = DSALightningGrader()

    def test_syntax_error(self):
        """Kiểm tra code lỗi cú pháp"""
        code = "def error_func(:"
        result = self.grader.grade_file_ultra_fast(code, "syntax_error.py")
        self.assertEqual(result['total_score'], 0.0)
        self.assertEqual(result['status'], 'WA')
        self.assertTrue(any("SyntaxError" in note for note in result['notes']))

    def test_linear_search(self):
        """Kiểm tra nhận diện Tìm kiếm tuyến tính"""
        code = """
def linear_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
"""
        result = self.grader.grade_file_ultra_fast(code, "linear.py")
        self.assertIn("Tìm kiếm tuyến tính", result['algorithms'])
        self.assertGreaterEqual(result['total_score'], 50)

    def test_bubble_sort(self):
        """Kiểm tra nhận diện Sắp xếp nổi bọt (Nested Loops + Swap)"""
        code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
"""
        result = self.grader.grade_file_ultra_fast(code, "bubble.py")
        self.assertIn("Sắp xếp cơ bản (Bubble/Selection/Insertion)", result['algorithms'])

    def test_binary_search(self):
        """Kiểm tra nhận diện Tìm kiếm nhị phân (While + Div2 + Compare)"""
        code = """
def binary_search(arr, x):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (high + low) // 2
        if arr[mid] < x:
            low = mid + 1
        elif arr[mid] > x:
            high = mid - 1
        else:
            return mid
    return -1
"""
        result = self.grader.grade_file_ultra_fast(code, "binary.py")
        self.assertIn("Tìm kiếm nhị phân", result['algorithms'])

    def test_spaghetti_code(self):
        """Kiểm tra phát hiện code rác (nhiều biến toàn cục)"""
        code = """
var1 = 1
var2 = 2
var3 = 3
var4 = 4
var5 = 5
var6 = 6  # > 5 biến toàn cục
def main():
    print(var1 + var2)
"""
        result = self.grader.grade_file_ultra_fast(code, "spaghetti.py")
        notes = " ".join(result['notes'])
        self.assertIn("Spaghetti Code", notes)
        self.assertIn("biến toàn cục", notes)

    def test_short_code_anti_gaming(self):
        """Kiểm tra chống gian lận code quá ngắn"""
        code = "print('Hello World')"
        result = self.grader.grade_file_ultra_fast(code, "short.py")
        self.assertIn("Code quá ngắn", result['notes'])
        self.assertLessEqual(result['total_score'], 30)

if __name__ == '__main__':
    unittest.main()