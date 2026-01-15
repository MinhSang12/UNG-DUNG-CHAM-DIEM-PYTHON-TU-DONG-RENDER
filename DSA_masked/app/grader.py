import time
import ast
import asyncio
from typing import Dict
import os
import subprocess
import sys

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
        except:
            pass # Nếu lỗi parse thì sẽ bắt ở bước syntax check sau
        return violations

    def grade_file_ultra_fast(self, code: str, filename: str) -> Dict:
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
                'status': 'FLAG', # Đánh dấu nghi ngờ
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

        # 2. PEP8 QUICK CHECK
        notes = []
        pep8_score = 10
        if '\t' in code: 
            pep8_score -= 2
            notes.append("PEP8: Sử dụng phím Tab thay vì Space (nên dùng 4 spaces)")
            
        lines = code.split('\n')
        long_lines = sum(1 for l in lines if len(l) > 79)
        if long_lines > 0:
            pep8_score -= min(4, long_lines // 5)
            notes.append(f"PEP8: Có {long_lines} dòng code quá dài (>79 ký tự)")
        
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
            'long_funcs': 0,
            'nodes_for_fingerprint': []
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
            if isinstance(node, ast.Name) and ('dp' in node.id.lower() or 'memo' in node.id.lower()):
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
        
        # --- Cấu trúc dữ liệu cơ bản ---
        if f['list']: algos.append('List'); dsa_score += 2
        if f['tuple']: algos.append('Tuple'); dsa_score += 2
        if f['set']: algos.append('Set'); dsa_score += 3
        if f['dict']: algos.append('Dictionary'); dsa_score += 3
        
        # --- Giải thuật cơ bản ---
        if f['nested_loops'] and f['swap']:
            algos.append('Sắp xếp cơ bản (Bubble/Selection/Insertion)')
            dsa_score += 20
        elif f['loops'] > 0 and f['ifs'] > 0 and f['returns'] and not f['div2'] and not f['recursion'] and not f['nested_loops']:
            algos.append('Tìm kiếm tuyến tính')
            dsa_score += 20
            
        # --- Cấu trúc dữ liệu trung cấp ---
        if f['class'] and 'next' in f['class_attrs']:
            algos.append('Linked List')
            dsa_score += 15
        if f['pop'] and not f['deque'] and not f['recursion']:
            algos.append('Stack')
            dsa_score += 5
        if f['deque'] or (f['list'] and 'pop(0)' in code):
            algos.append('Queue')
            dsa_score += 10
        if 'heapq' in f['imports']:
            algos.append('Heap/Priority Queue')
            dsa_score += 15
            
        # --- Giải thuật trung cấp ---
        if f['div2'] and f['while_loop'] and f['comparisons'] > 0:
            algos.append('Tìm kiếm nhị phân')
            dsa_score += 30
        if f['recursion']:
            algos.append('Đệ quy')
            dsa_score += 10
            if 'merge' in code_lower or 'quick' in code_lower or 'mid' in code_lower:
                algos.append('Sắp xếp nâng cao (Merge/Quick)')
                dsa_score += 10
                
        # --- Cấu trúc dữ liệu nâng cao ---
        if f['class'] and {'left', 'right'}.issubset(f['class_attrs']):
            algos.append('Cây nhị phân/BST')
            dsa_score += 20
        if 'networkx' in f['imports'] or 'adj' in f['class_attrs'] or 'graph' in f['class_attrs']:
            algos.append('Đồ thị (Graph)')
            dsa_score += 20
            
        # --- Giải thuật nâng cao ---
        if f['dp_var'] and (f['nested_loops'] or f['recursion']):
            algos.append('Quy hoạch động (DP)')
            dsa_score += 25
        if (f['deque'] or f['recursion']) and ('visit' in code_lower or 'seen' in code_lower):
            algos.append('Duyệt đồ thị (BFS/DFS)')
            dsa_score += 20
        if 'heapq' in f['imports'] and 'dist' in code_lower:
            algos.append('Dijkstra')
            dsa_score += 25

        # 5. FINAL CALCULATION
        dsa_score = min(60, dsa_score)
        
        complexity_score = 10
        # Đánh giá dựa trên độ sâu vòng lặp (Big-O) thay vì độ sâu code
        if max_loop_depth > 3: complexity_score = 2; notes.append(f"Hiệu năng kém: Độ phức tạp O(n^{max_loop_depth}) là quá cao")
        elif max_loop_depth == 3: complexity_score = 5; notes.append("Hiệu năng: Độ phức tạp O(n^3) khá chậm")
        elif max_loop_depth == 2: complexity_score = 8 # O(n^2) chấp nhận được cho bài tập cơ bản
        
        test_score = 0
        if f['main_guard']: test_score += 5
        if f['returns'] or 'print' in code: test_score += 10
        if f['type_hints']: test_score += 5
        
        # Spaghetti Code Penalties
        if f['global_vars'] > 5:
            pep8_score = max(0, pep8_score - 2)
            notes.append(f"Code rối: Sử dụng {f['global_vars']} biến toàn cục (Nên đóng gói vào hàm/class)")
        if f['long_funcs'] > 0:
            pep8_score = max(0, pep8_score - 2)
            notes.append(f"Code rối: Có {f['long_funcs']} hàm quá dài (>30 dòng, nên tách nhỏ)")

        raw_total = pep8_score + dsa_score + complexity_score + test_score
        
        # Anti-gaming: Code quá ngắn
        if f['nodes_count'] < 10:
            notes.append('Cảnh báo: Code quá ngắn hoặc không đủ logic')
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

    def run_dynamic_test(self, filepath: str, input_str: str, timeout: int = 2) -> Dict:
        """
        Chạy code sinh viên an toàn với giới hạn thời gian (Chống lặp vô tận)
        """
        try:
            # Chạy code trong process riêng biệt
            result = subprocess.run(
                [sys.executable, filepath], # Chạy bằng python hiện tại
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
            return {"success": False, "error": "Time Limit Exceeded (Chạy quá 2s - Có thể lặp vô tận)"}
        except Exception as e:
            return {"success": False, "error": f"Runtime Error: {str(e)}"}

# SINGLETON - KHÔNG INIT LẠI
lightning_grader = DSALightningGrader()

class AIGrader(DSALightningGrader):
    def __init__(self, api_key=None):
        super().__init__()
        pass

    async def check_connection(self):
        return True

    async def grade_with_ai(self, code: str, filename: str) -> Dict:
        # Chỉ chạy logic chấm điểm tĩnh (AST), bỏ qua AI
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.grade_file_ultra_fast, code, filename)
