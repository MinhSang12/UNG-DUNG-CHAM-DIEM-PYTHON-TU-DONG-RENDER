import ast
import asyncio
import subprocess
import sys
import time
import tempfile
import os
from typing import Dict
from app.test_gen import get_test_cases
import re
import google.generativeai as genai
import json
import httpx
from app.services import fetch_problem_from_bank

class DSALightningGrader:
    def __init__(self):
        # Chỉ giữ lại các pattern kiểm tra an toàn, bỏ hết pattern chấm điểm thuật toán
        pass

    def check_safety(self, code: str) -> list:
        """Quét AST để tìm các thư viện/hàm nguy hiểm (Chống tò mò/phá hoại)"""
        dangerous_imports = {'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests'}
        dangerous_funcs = {'open', 'exec', 'eval', 'compile'}
        violations = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # 1. Check import
                if isinstance(node, ast.Import):
                    for n in node.names:
                        if n.name.split('.')[0] in dangerous_imports:
                            violations.append(f"Cấm import thư viện hệ thống: {n.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in dangerous_imports:
                        violations.append(f"Cấm import thư viện hệ thống: {node.module}")
                
                # 2. Check hàm nguy hiểm (open, exec...)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in dangerous_funcs:
                        violations.append(f"Cấm sử dụng hàm: {node.func.id}()")
        except Exception:
            pass # Nếu lỗi parse thì sẽ bắt ở bước syntax check sau
        return violations

    def grade_file_ultra_fast(self, code: str, filename: str, topic: str = None) -> Dict:
        start = time.time()
        code_lower = code.lower()

        # 0. SAFETY CHECK (Mới thêm)
        safety_violations = self.check_safety(code)
        if safety_violations:
            return {
                'filename': filename,
                'total_score': 0,
                'breakdown': {'pep8': 0, 'dsa': 0, 'complexity': 0, 'tests': 0},
                'algorithms': 'Bị từ chối',
                'runtime': '0ms',
                'status': 'FLAG', # Đánh dấu nghi ngờ,đạo văn hoặc mã độc
                'valid_score': False,
                'notes': ["PHÁT HIỆN MÃ NGUY HIỂM:"] + safety_violations
            }

        # 1. SYNTAX CHECK - nếu lỗi cú pháp thì trả về ngay
        try:
            tree = ast.parse(code, filename or '<string>')
        except SyntaxError as e:
            runtime = time.time() - start
            return {
                'filename': filename,
                'total_score': 0.0,
                'breakdown': {'pep8': 0, 'dsa': 0, 'complexity': 0, 'tests': 0},
                'algorithms': '',
                'runtime': f"{runtime*1000:.0f}ms",
                'status': 'WA',
                'valid_score': False,
                'confidence': 0,
                'notes': [f"Lỗi cú pháp: {e.msg} tại dòng {e.lineno}"]
            }

        # 2. PEP8 CHECK
        notes = []
        pep8_score = 10
        if '\t' in code: 
            pep8_score -= 2
            notes.append("PEP8: Sử dụng phím Tab thay vì Space (-2đ)")
            
        lines = code.split('\n')
        long_line_nums = [str(i+1) for i, l in enumerate(lines) if len(l) > 79]
        if long_line_nums:
            deduction = min(4, len(long_line_nums) // 5 + 1) # Trừ ít nhất 1đ nếu có lỗi
            pep8_score -= deduction
            notes.append(f"PEP8: Dòng {', '.join(long_line_nums[:3])}{'...' if len(long_line_nums)>3 else ''} quá dài (>79 ký tự) (-{deduction}đ)")
        
        # 3. FEATURE EXTRACTION (AST VISITOR)
        # Thu thập các đặc điểm kỹ thuật để nhận diện thuật toán
        f = {
            'list': False, 'tuple': False, 'set': False, 'dict': False,
            'nested_loops': False, 'swap': False, 'recursion': False,
            'class': False, 'class_attrs': set(),
            'div2': False, 'pop': False, 'deque': False,
            'dp_var': False, 'imports': set(),
            'loops': 0, 'ifs': 0, 'returns': False,
            'main_guard': False, 'type_hints': False,
            'nodes_count': 0,
            'while_loop': False,
            'comparisons': 0,
            'global_vars': 0,
            'matrix_access': False, # a[i][j]
            '3d_array_access': False, # a[i][j][k]
            'yield': False,         # Generator
            'lambda': False,        # Lambda function
            'long_funcs': 0,
            'nodes_for_fingerprint': [],
            'slicing': False,          # [NEW] Dấu hiệu Merge Sort (arr[:mid])
            'list_comp_filter': False  # [NEW] Dấu hiệu Quick Sort ([x for x in arr if x < p])
        }
        
        max_nesting = 0
        max_loop_depth = 0

        def visit_node(node, depth, loop_depth):
            nonlocal max_nesting, max_loop_depth
            max_nesting = max(max_nesting, depth)
            max_loop_depth = max(max_loop_depth, loop_depth)
            f['nodes_count'] += 1
            
            # Thu thập dữ liệu vân tay (bỏ qua context Load/Store để giảm nhiễu)
            if not isinstance(node, (ast.Load, ast.Store)):
                f['nodes_for_fingerprint'].append(type(node).__name__)

            # Imports
            if isinstance(node, ast.Import):
                for n in node.names: f['imports'].add(n.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module: f['imports'].add(node.module)
            
            # Basic DS
            if isinstance(node, (ast.List, ast.ListComp)): f['list'] = True
            if isinstance(node, ast.Tuple): f['tuple'] = True
            if isinstance(node, (ast.Set, ast.SetComp)): f['set'] = True
            if isinstance(node, (ast.Dict, ast.DictComp)): f['dict'] = True
            
            # Control Flow
            if isinstance(node, (ast.For, ast.While)):
                f['loops'] += 1
                if isinstance(node, ast.While): f['while_loop'] = True
            if isinstance(node, ast.If): f['ifs'] += 1
            if isinstance(node, ast.Return): f['returns'] = True
            if isinstance(node, ast.Compare): f['comparisons'] += 1
            if isinstance(node, ast.Yield): f['yield'] = True
            if isinstance(node, ast.Lambda): f['lambda'] = True

            # [NEW] Detect Slicing (Merge Sort characteristic)
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                f['slicing'] = True
            
            # [NEW] Detect List Comp Filtering (Quick Sort characteristic)
            if isinstance(node, ast.ListComp):
                for gen in node.generators:
                    if gen.ifs: f['list_comp_filter'] = True

            # Matrix Detection (Subscript inside Subscript: grid[i][j])
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Subscript):
                    f['matrix_access'] = True
                    # [NEW] Detect 3D Array (dp[i][j][k])
                    if isinstance(node.value.value, ast.Subscript):
                        f['3d_array_access'] = True
            
            # Spaghetti Code Detection
            # 1. Global Variables (Depth 0 assignments, excluding CONSTANTS)
            if depth == 0 and isinstance(node, (ast.Assign, ast.AnnAssign)):
                is_const = False
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id.isupper(): is_const = True
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name) and node.target.id.isupper(): is_const = True
                if not is_const: f['global_vars'] += 1
            
            # 2. Long Functions (> 30 lines)
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 30: f['long_funcs'] += 1
            
            # Class & Attrs (Linked List, Tree, Graph)
            if isinstance(node, ast.ClassDef): f['class'] = True
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                f['class_attrs'].add(node.attr)
            
            # Operations (Binary Search, Swap, Stack/Queue)
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.FloorDiv, ast.RShift)):
                if isinstance(node.right, ast.Constant) and node.right.value == 2: f['div2'] = True
            
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
                if len(node.targets[0].elts) == 2: f['swap'] = True
                
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'pop': f['pop'] = True
                if isinstance(node.func, ast.Name) and node.func.id == 'deque': f['deque'] = True
            
            # Recursion & Type Hints
            if isinstance(node, ast.FunctionDef):
                if node.returns: f['type_hints'] = True
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == node.name:
                        f['recursion'] = True
            
            if isinstance(node, ast.AnnAssign): f['type_hints'] = True

            # DP Naming Heuristic
            # MỞ RỘNG: Chấp nhận nhiều cách đặt tên biến DP hơn
            if isinstance(node, ast.Name):
                name = node.id.lower()
                if any(x in name for x in ['dp', 'memo', 'table', 'cache', 'f', 'opt']):
                    f['dp_var'] = True

            # Recursive traversal
            for child in ast.iter_fields(node):
                value = child[1]
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            # Tăng loop_depth chỉ khi gặp vòng lặp
                            is_loop = isinstance(item, (ast.For, ast.While))
                            new_loop_depth = loop_depth + 1 if is_loop else loop_depth
                            # Tăng depth chung cho các block
                            new_depth = depth + 1 if isinstance(item, (ast.For, ast.While, ast.FunctionDef, ast.If)) else depth
                            visit_node(item, new_depth, new_loop_depth)
                elif isinstance(value, ast.AST):
                    is_loop = isinstance(value, (ast.For, ast.While))
                    new_loop_depth = loop_depth + 1 if is_loop else loop_depth
                    new_depth = depth + 1 if isinstance(value, (ast.For, ast.While, ast.FunctionDef, ast.If)) else depth
                    visit_node(value, new_depth, new_loop_depth)

        visit_node(tree, 0, 0)
        
        if 'if __name__' in code: f['main_guard'] = True
        if 'collections' in f['imports']: f['deque'] = True
        if max_loop_depth >= 2: f['nested_loops'] = True

        # 4. SCORING & CLASSIFICATION (Quy tắc chấm điểm công bằng)
        algos = []
        dsa_score = 0
        dsa_details = [] # Danh sách giải trình điểm DSA
        
        # --- Cấu trúc dữ liệu cơ bản ---
        if f['list']: algos.append('List'); dsa_score += 2
        if f['tuple']: algos.append('Tuple'); dsa_score += 2
        if f['set']: algos.append('Set'); dsa_score += 3
        if f['dict']: algos.append('Dictionary'); dsa_score += 3
        if f['yield']: algos.append('Generator/Yield'); dsa_score += 5
        if f['lambda']: algos.append('Lambda Function'); dsa_score += 5
        if f['list']: algos.append('List'); dsa_score += 2; dsa_details.append("List (+2đ)")
        if f['tuple']: algos.append('Tuple'); dsa_score += 2; dsa_details.append("Tuple (+2đ)")
        if f['set']: algos.append('Set'); dsa_score += 3; dsa_details.append("Set (+3đ)")
        if f['dict']: algos.append('Dictionary'); dsa_score += 3; dsa_details.append("Dict (+3đ)")
        if f['yield']: algos.append('Generator/Yield'); dsa_score += 5; dsa_details.append("Yield (+5đ)")
        if f['lambda']: algos.append('Lambda Function'); dsa_score += 5; dsa_details.append("Lambda (+5đ)")
        
        # --- Giải thuật cơ bản ---
        if f['nested_loops'] and f['swap']:
            algos.append('Sắp xếp cơ bản (Bubble/Selection/Insertion)')
            dsa_score += 20
            dsa_details.append("Sắp xếp cơ bản 2 vòng lặp (+20đ)")
        elif f['loops'] > 0 and f['ifs'] > 0 and f['returns'] and not f['div2'] and not f['recursion'] and not f['nested_loops']:
            algos.append('Tìm kiếm tuyến tính')
            dsa_score += 20
            dsa_details.append("Tìm kiếm tuyến tính (+20đ)")
            
        # --- Cấu trúc dữ liệu trung cấp ---
        if f['class'] and 'next' in f['class_attrs']:
            algos.append('Linked List')
            dsa_score += 15
            dsa_details.append("Linked List (+15đ)")
        if f['pop'] and not f['deque'] and not f['recursion']:
            algos.append('Stack')
            dsa_score += 5
            dsa_details.append("Stack (+5đ)")
        if f['deque'] or (f['list'] and 'pop(0)' in code):
            algos.append('Queue')
            dsa_score += 10
            dsa_details.append("Queue (+10đ)")
        if 'heapq' in f['imports']:
            algos.append('Heap/Priority Queue')
            dsa_score += 15
            dsa_details.append("Heap (+15đ)")
            
        # --- Giải thuật trung cấp ---
        if f['div2'] and f['while_loop'] and f['comparisons'] > 0:
            algos.append('Tìm kiếm nhị phân')
            dsa_score += 30
            dsa_details.append("Binary Search (chia đôi) (+30đ)")
        if f['recursion']:
            algos.append('Đệ quy')
            dsa_score += 10
            dsa_details.append("Đệ quy (+10đ)")
            
            # [NEW] Phân loại Quick Sort vs Merge Sort dựa trên cấu trúc AST
            # Quick Sort: Dùng List Comp có điều kiện HOẶC Vòng lặp có Swap (In-place partition)
            is_quick = f['list_comp_filter'] or (f['swap'] and f['loops'] > 0) or 'pivot' in code_lower
            # Merge Sort: Dùng Slicing (cắt mảng) HOẶC biến mid
            is_merge = f['slicing'] or 'mid' in code_lower or 'merge' in code_lower

            if is_quick and not is_merge:
                algos.append('Quick Sort')
                dsa_score += 10
                dsa_details.append("Quick Sort (+10đ)")
            elif is_merge:
                algos.append('Merge Sort')
                dsa_score += 10
                dsa_details.append("Merge Sort (+10đ)")
            elif 'sort' in filename.lower(): # Fallback nếu không rõ
                algos.append('Sắp xếp nâng cao')
                dsa_score += 10
                dsa_details.append("Sắp xếp nâng cao (+10đ)")
                
        # --- Cấu trúc dữ liệu nâng cao ---
        if f['class'] and {'left', 'right'}.issubset(f['class_attrs']):
            algos.append('Cây nhị phân/BST')
            dsa_score += 20
            dsa_details.append("BST/Tree (+20đ)")
        if f['class'] and 'children' in f['class_attrs']:
            algos.append('Trie (Prefix Tree)')
            dsa_score += 25
            dsa_details.append("Trie (+25đ)")
        if 'networkx' in f['imports'] or 'adj' in f['class_attrs'] or 'graph' in f['class_attrs']:
            algos.append('Đồ thị (Graph)')
            dsa_score += 20
            dsa_details.append("Graph (+20đ)")
            
        # --- Giải thuật nâng cao ---
        if f['dp_var'] and (f['nested_loops'] or f['recursion']):
            algos.append('Quy hoạch động (DP)')
            dsa_score += 25
            dsa_details.append("Quy hoạch động (+25đ)")
        if (f['deque'] or f['recursion']) and ('visit' in code_lower or 'seen' in code_lower):
            algos.append('Duyệt đồ thị (BFS/DFS)')
            dsa_score += 20
            dsa_details.append("BFS/DFS (+20đ)")
        if f['matrix_access'] and (f['recursion'] or f['deque']):
            algos.append('Ma trận/Grid (BFS/DFS)')
            dsa_score += 20
            dsa_details.append("Ma trận (+20đ)")
        if f['3d_array_access'] and f['dp_var']:
            algos.append('Quy hoạch động 3 chiều')
            dsa_score += 30
            dsa_details.append("DP 3 chiều (+30đ)")
        if f['recursion'] and f['loops'] > 0 and ('backtrack' in code_lower or 'undo' in code_lower or f['pop']):
            algos.append('Backtracking (Quay lui)')
            dsa_score += 30
            dsa_details.append("Backtracking (+30đ)")
        # MỞ RỘNG: Dijkstra không nhất thiết phải tên biến là 'dist'
        if 'heapq' in f['imports'] and (any(x in code_lower for x in ['dist', 'cost', 'd[', 'distance'])):
            algos.append('Dijkstra')
            dsa_score += 25
            dsa_details.append("Dijkstra (+25đ)")
            
        # --- KIỂM TRA LỆCH THUẬT TOÁN (EXPECTED vs ACTUAL) ---
        # Dựa vào tên file để đoán thuật toán sinh viên CẦN làm, và so sánh với cái họ ĐÃ làm
        fname_lower = filename.lower()
        
        # 1. Check Sort: Yêu cầu N log N nhưng viết N^2
        if any(x in fname_lower for x in ['quick', 'merge', 'heap']) and 'sort' in fname_lower:
            if not f['recursion'] and f['nested_loops']:
                notes.append("Sai thuật toán: Bài yêu cầu Quick/Merge Sort (O(n log n)) nhưng code có vẻ là Bubble/Insertion Sort (O(n^2)).")
                notes.append("Sai thuật toán: Tên file yêu cầu Quick/Merge Sort nhưng không tìm thấy hàm đệ quy, chỉ thấy vòng lặp lồng nhau (O(n^2)).")
                dsa_score = max(0, dsa_score - 10)
                dsa_details.append("TRỪ ĐIỂM: Sai thuật toán (-10đ)")

        # 2. Check Search: Yêu cầu Binary nhưng viết Linear
        if 'binary' in fname_lower and 'search' in fname_lower:
            if not f['div2'] and f['loops'] > 0:
                notes.append("Sai thuật toán: Bài yêu cầu Binary Search (chia đôi) nhưng code đang duyệt tuần tự (Linear Search).")
                notes.append("Sai thuật toán: Tên file yêu cầu Binary Search nhưng không tìm thấy phép chia đôi (//2), chỉ thấy vòng lặp tuần tự.")
                dsa_score = max(0, dsa_score - 10)
                dsa_details.append("TRỪ ĐIỂM: Sai thuật toán (-10đ)")

        # 5. FINAL CALCULATION
        dsa_score = min(60, dsa_score)
        
        complexity_score = 10
        # Đánh giá dựa trên độ sâu vòng lặp (Big-O) thay vì độ sâu code
        if max_loop_depth > 3: complexity_score = 2; notes.append(f"Hiệu năng kém: Độ phức tạp O(n^{max_loop_depth}) là quá cao (2/10đ)")
        elif max_loop_depth == 3: complexity_score = 5; notes.append("Hiệu năng: Độ phức tạp O(n^3) khá chậm (5/10đ)")
        elif max_loop_depth == 2: complexity_score = 8 # O(n^2) chấp nhận được cho bài tập cơ bản
        
        test_score = 0
        if f['main_guard']: test_score += 5
        if f['returns'] or 'print' in code: test_score += 10
        if f['type_hints']: test_score += 5
        
        # Spaghetti Code Penalties
        if f['global_vars'] > 5:
            pep8_score = max(0, pep8_score - 2)
            notes.append(f"Code rối: Sử dụng {f['global_vars']} biến toàn cục (-2đ)")
        if f['long_funcs'] > 0:
            pep8_score = max(0, pep8_score - 2)
            notes.append(f"Code rối: Có {f['long_funcs']} hàm quá dài (>30 dòng) (-2đ)")
            
        # --- 6. DYNAMIC TESTING (CHẤM ĐIỂM CHẠY THỰC TẾ) ---
        # Tích hợp test_gen để kiểm tra tính đúng đắn
        test_cases = get_test_cases(filename, topic)
        passed_tests = 0
        total_tests = len(test_cases)
        
        if total_tests > 0:
            # Reset điểm test tĩnh để dùng điểm test động
            test_score = 0 
            notes.append(f"--- Chạy {total_tests} test cases ---")
            
            # Tùy chỉnh timeout: Mặc định 2s, tăng lên 5s cho bài phức tạp
            current_timeout = 2
            if any(k in filename.lower() for k in ['graph', 'bfs', 'dfs', 'nqueen', 'backtrack', 'mst', 'matrix']):
                current_timeout = 5
            
            for tc in test_cases:
                res = self.run_dynamic_test(code, tc['input'], timeout=current_timeout)
                if res['success']:
                    # So sánh output (bỏ qua khoảng trắng thừa)
                    if res['output'] == tc['expected']:
                        passed_tests += 1
                    else:
                        if passed_tests == 0: # Chỉ báo lỗi test đầu tiên sai
                            # Hiển thị Input để sinh viên biết trường hợp nào gây lỗi
                            inp_short = tc['input'].replace('\n', ' ')
                            if len(inp_short) > 20: inp_short = inp_short[:20] + '...'
                            notes.append(f"Sai kết quả tại '{tc['name']}' (Input: {inp_short}): Mong đợi '{tc['expected']}', nhưng code in ra '{res['output']}'")
                else:
                    # Trích xuất dòng lỗi từ traceback
                    err_msg = res['error']
                    line_match = re.search(r'line (\d+)', err_msg)
                    line_info = f" tại dòng {line_match.group(1)}" if line_match else ""
                    
                    # Lấy tên lỗi (VD: ZeroDivisionError)
                    err_type = err_msg.split('\n')[-1] if err_msg else "Unknown Error"
                    notes.append(f"Lỗi thực thi{line_info} ({tc['name']}): {err_type}")
                    break # Dừng nếu code lỗi runtime
            
            # Tính điểm correctness (Tối đa 40 điểm cho tính đúng đắn)
            correctness_score = (passed_tests / total_tests) * 40
            dsa_score = min(dsa_score, 40) # Giảm trọng số static nếu đã có dynamic test
            test_score = correctness_score
            notes.append(f"Kết quả chạy: {passed_tests}/{total_tests} test cases")

        
        # Thêm dòng giải thích chi tiết điểm DSA
        if dsa_details:
            dsa_explanation = f"Phát hiện thuật toán: {', '.join(dsa_details)}"
            notes.insert(0, dsa_explanation)

        raw_total = pep8_score + dsa_score + complexity_score + test_score
        
        # Anti-gaming: Code quá ngắn
        if f['nodes_count'] < 10:
            notes.append('Cảnh báo: Code quá ngắn hoặc không đủ logic (Điểm tối đa: 30)')
            raw_total = min(raw_total, 30)

        # PLAGIARISM FINGERPRINT (Tạo chuỗi N-grams từ AST)
        nodes = f['nodes_for_fingerprint']
        fingerprint = set(tuple(nodes[i:i+3]) for i in range(len(nodes)-2)) if len(nodes) >= 3 else set(nodes)

        total_score = round(min(100, raw_total), 1)
        runtime = time.time() - start

        return {
            'filename': filename,
            'total_score': total_score,
            'breakdown': {
                'pep8': round(pep8_score, 1),
                'dsa': dsa_score,
                'complexity': complexity_score,
                'tests': test_score
            },
            'algorithms': ', '.join(sorted(set(algos))) if algos else 'Cơ bản',
            'runtime': f"{runtime*1000:.0f}ms",
            'status': 'AC' if total_score >= 50 else 'WA',
            'valid_score': True,
            'confidence': 80,
            'fingerprint': fingerprint,
            'notes': notes
        }

    def run_dynamic_test(self, code_str: str, input_str: str, timeout: int = 2) -> Dict:
        """
        Chạy code sinh viên an toàn với giới hạn thời gian (Chống lặp vô tận)
        Sử dụng tempfile để xử lý code từ bộ nhớ.
        """
        temp_file = None
        try:
            # Tạo file tạm thời chứa code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
                tmp.write(code_str)
                temp_file = tmp.name

            # Chạy code trong process riêng biệt
            result = subprocess.run(
                [sys.executable, temp_file], # Chạy file tạm
                input=input_str,
                capture_output=True,
                text=True,
                timeout=timeout # Tự động kill nếu chạy quá 2 giây
            )
            return {
                "success": True,
                "output": result.stdout.strip(),
                "error": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Time Limit Exceeded (Chạy quá {timeout}s - Có thể lặp vô tận)"}
        except Exception as e:
            return {"success": False, "error": f"Runtime Error: {str(e)}"}
        finally:
            # Dọn dẹp file tạm
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except: pass

# SINGLETON - KHÔNG INIT LẠI
lightning_grader = DSALightningGrader()
    
    # Trong file app/grader.py

class AIGrader(DSALightningGrader):
    def __init__(self, api_key=None):
        super().__init__()
        # Cấu hình AI với độ ổn định cao (Temperature = 0)
        real_key = api_key or os.getenv("GEMINI_API_KEY", "AIzaSyAe-tRWGVG8cJW4Hj-IexDDBM4o58BeBYo")
        genai.configure(api_key=real_key)
        # Sử dụng model flash để có tốc độ phản hồi nhanh nhất
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash', 
            generation_config={"temperature": 0}
        )
        self.rubric_api_url = "http://127.0.0.1:8001/api"

    async def grade_auto(self, code: str, filename: str, topic: str = None) -> Dict:
        """
        AI LÀ GIÁM KHẢO CHÍNH: 
        Ưu tiên 1: Tiêu chí từ Ngân hàng bài tập & Rubric.
        Hỗ trợ: Dữ liệu kỹ thuật từ AST chạy song song.
        """
        loop = asyncio.get_running_loop()
        
        # --- BƯỚC 1: CHẠY SONG SONG THU THẬP DỮ LIỆU ---
        actual_topic = filename if (not topic or topic == "None") else topic
        actual_topic = actual_topic.replace(".py", "") # Xóa đuôi file nếu lấy từ filename

# Bước 2: Gọi Microservice với mã bài tập đã xác định
        problem_task = loop.run_in_executor(None, fetch_problem_from_bank, actual_topic)
        # rubric_task = self.fetch_rubric(topic or filename)
        ast_task = loop.run_in_executor(None, self.grade_file_ultra_fast, code, filename, topic)
        
        problem_data,  ast_report = await asyncio.gather(
            problem_task, ast_task
        )
        if not topic or topic == "None":
        # Lấy filename, ví dụ: "CTDL_D1_01.py" -> bỏ ".py" -> còn "CTDL_D1_01"
            topic = filename.replace(".py", "")
        # Chế độ bảo mật luôn được xử lý trước
        # Chế độ bảo mật luôn được xử lý trước
        if ast_report.get('status') == 'FLAG':
            ast_report['has_rubric'] = False
            ast_report['reasoning'] = "HỆ THỐNG TỪ CHỐI CHẤM ĐIỂM VÌ PHÁT HIỆN MÃ NGUY HIỂM."
            ast_report['breakdown'] = {"logic_score": 0, "algorithm_score": 0, "style_score": 0, "optimization_score": 0}
            return ast_report
        db_rubric = problem_data.get('rubric', "Chấm theo tiêu chuẩn DSA chung.") if problem_data else "Chấm theo tiêu chuẩn DSA chung."
        # Chuẩn bị thông tin từ Ngân hàng bài tập
        bank_details = "N/A"
        weight_per_criterion = 10
        if problem_data:
            db_rubric = problem_data.get('rubric', db_rubric)
            bank_details = f"Đề bài: {problem_data.get('requirements')}. Số test cases: {len(problem_data.get('test_cases', []))}."
            
            # 2. Bóc tách và tính toán trọng số động
            if isinstance(db_rubric, str):
                lines = [l.strip().lstrip('-').lstrip('*').strip() for l in db_rubric.split('\n')]
                criteria_list = [l for l in lines if len(l) > 5]
            else:
                criteria_list = db_rubric if isinstance(db_rubric, list) else []
        
            num_criteria = len(criteria_list) if criteria_list else 1
            weight_per_criterion = round(10 / num_criteria, 2) # Chia đều thang điểm 10
        # --- BƯỚC 2: RÀNG BUỘC AI SOẠN THẢO FEEDBACK CHUYÊN SÂU ---
        prompt = f"""
Bạn là Giám khảo trưởng môn DSA. Hãy chấm điểm dựa trên mã nguồn sinh viên và các tiêu chí ĐỘNG được cung cấp.

[NGUỒN DỮ LIỆU GỐC]:
- Tiêu chí từ Database (Rubric): {db_rubric}
- Thông tin bài tập: {bank_details}

[DỮ LIỆU KỸ THUẬT HỖ TRỢ (AST)]:
- Thuật toán nhận diện: {ast_report['algorithms']}
- Ghi chú máy chấm: {ast_report['notes']}
- Runtime: {ast_report['runtime']}

[MÃ NGUỒN SINH VIÊN]:
{code}

YÊU CẦU NGHIÊM NGẶT:
1. NGÔN NGỮ: Mọi nội dung trong JSON (criterion, reason, reasoning, improvement, strengths, weaknesses, overall_feedback) PHẢI dùng tiếng Việt 100%.
2. GIỮ NGUYÊN TIÊU CHÍ: Trường 'criterion' phải sao chép NGUYÊN VĂN 100% các câu có trong {db_rubric}. KHÔNG được sửa từ, KHÔNG được tóm tắt.
3. THANG ĐIỂM 100: Để khớp với UI, hãy chấm trên thang điểm 100.
4. CHẤM ĐIỂM CHI TIẾT & KHẮT KHE:
   - Mỗi tiêu chí trong {db_rubric} có giá trị ĐIỂM CỐ ĐỊNH là {weight_per_criterion * 10} điểm (đã nhân hệ số 10 cho thang 100).
   - Nếu mã nguồn KHÔNG có phần nào liên quan đến tiêu chí: Cho ngay 0 điểm.
5. PHÂN TÍCH CHO UI: Phải cung cấp đầy đủ các trường nhận xét chi tiết để hiển thị lên Dashboard.

TRẢ VỀ JSON CHUẨN DUY NHẤT (KHÔNG CÓ TEXT THỪA):
{{
  "status": "PASS/FAIL/FLAG",
  "detected_algo": "Tên thuật toán",
  "total_score": số (Tổng điểm, thang 10),
  "criteria_results": [
    {{
      "criterion": "Chép y hệt câu trong rubric vào đây",
      "score": số (0 hoặc {weight_per_criterion}),
      "max_score": {weight_per_criterion}, 
      "reason": "Giải thích lý do"
    }}
  ],
  "reasoning": "...",
  "complexity_analysis": "...",
  "strengths": "...",
  "weaknesses": "...",
  "improvement": "...",
  "overall_feedback": "..."
}}
        # --- BƯỚC 3: AI QUYẾT ĐỊNH KẾT QUẢ ---
        try:
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            ai_data = json.loads(clean_json)
            
            # Lấy điểm và các trường dữ liệu cho UI mới
            total = ai_data.get('total_score', 0)
            
            return {
                'filename': filename,
                'total_score': round(total, 1),
                'status': ai_data.get('status', 'AC' if total >= 50 else 'WA'),
                'algorithms': ai_data.get('detected_algo', ast_report['algorithms']),
                'runtime': ast_report['runtime'],
                
                # Các trường mới cho Dashboard kết quả
                'has_rubric': True,
                'reasoning': ai_data.get('reasoning', 'AI chưa đưa ra nhận xét chi tiết.'),
                'improvement': ai_data.get('improvement', 'Chưa có gợi ý cải thiện.'),
                'strengths': ai_data.get('strengths', ''),
                'weaknesses': ai_data.get('weaknesses', ''),
                'complexity_analysis': ai_data.get('complexity_analysis', ''),
                'breakdown': ai_data.get('breakdown', {
                    "logic_score": 0, "algorithm_score": 0, "style_score": 0, "optimization_score": 0
                }),
                'criteria_results': ai_data.get('criteria_results', []),
                
                'valid_score': True,
                'fingerprint': ast_report.get('fingerprint')
            }
        except Exception as e:
            print(f"❌ AI Error: {str(e)}")
            # Fallback về kết quả của máy chấm AST nếu AI lỗi
            ast_report['has_rubric'] = False
            return ast_report
