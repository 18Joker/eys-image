"""逐个探测 image_generate_v5.py 中 API_KEYS 的可用性（GET /models，10s 超时）

注意: GET /models 不校验令牌状态, 可能对已停用 Key 返回 200 假阳性;
最终以生图接口为准。可用 --probe-gen 参数追加生图接口二次验证。
"""
import ast
import os
import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://apihub.agnes-ai.com/v1"
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image_generate_v5.py")

# 用 AST 从脚本中提取 API_KEYS 列表（注释掉的 Key 不会出现）
tree = ast.parse(open(SCRIPT, "r", encoding="utf-8").read())
keys = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "API_KEYS":
                keys = [elt.value for elt in node.value.elts]

print(f"共读取 {len(keys)} 个生效 Key\n")

probe_gen = "--probe-gen" in sys.argv
alive, dead = [], []
for i, key in enumerate(keys, 1):
    tag = key[:4] + "..." + key[-6:]
    try:
        r = requests.get(f"{BASE_URL}/models", headers={"Authorization": f"Bearer {key}"}, timeout=10)
        status = r.status_code
        if status == 200 and probe_gen:
            # /models 有假阳性, 追加一次最小生图请求验证
            g = requests.post(
                f"{BASE_URL}/images/generations",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "agnes-image-2.5-flash", "prompt": "a simple red circle", "size": "1024x1024"},
                timeout=(5, 90),
            )
            status = g.status_code
        if status == 200:
            alive.append(key)
            print(f"[{i:02d}] {tag} -> 200 OK 可用")
        else:
            msg = ""
            try:
                msg = r.json().get("error", {}).get("message", "")[:50]
            except Exception:
                pass
            dead.append(tag)
            print(f"[{i:02d}] {tag} -> HTTP {status} 不可用 {msg}")
    except Exception as e:
        dead.append(tag)
        print(f"[{i:02d}] {tag} -> 请求异常: {e}")

print(f"\n结果: 可用 {len(alive)} / 共 {len(keys)}")
