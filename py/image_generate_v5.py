import os
import json
import base64
import mimetypes
import requests
import concurrent.futures
import webbrowser
import queue  # 用于线程安全地管理 API Key
import time
import random
import threading
from pathlib import Path
import sys
import io
import argparse
import logging

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ==================== 日志配置 ====================
def setup_logging():
    """配置日志系统，输出到控制台"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# ==================== 全局配置 ====================
# 支持填入多个 API Key（均为无限量，尽管用，不考虑额度）
API_KEYS = [
    "wk-KyLbGDsypO862KC9dBbBolyscal8p3hmvSf96Un0lzpUtNpr",
    "wk-tMZW7YP1ob8fsXcwoax9Iyl8mxl6QJuRIJhs4dCrT7Vky1S7",
    "wk-v4GDHCYCtZxnFbaYxgqj4sTQFida53rfTgQBcxBVrAOl7IkP",
    "wk-P2bE9HAa1JCMbrzCTAZTAA48yxsrCu8MxpX5MoJEcQuRwxfv",
    "wk-71T4z1tGUhn1ivOTEFhmy7sa77fSa0tFpfw06SxyxgrJwan6",
    "wk-yAViE89LgfA1eemdPw8VP6oqxUzuqKix6HcqeTHOreO7d6Xw",
    "wk-M0kqYE2im38ldxhpggGcAdd24i5bIqc17mkalN6OckDxzJSX",
    "wk-JLIt1hBlc3NX8gH2cXEPY8Oc9BbLU3fgdsgnxhtrjoMuLJWe",
    "wk-XhVB17B38RSAQ6Ic2qJjSyAjKUP0GQa4Kc2lsRei34fRo9Rm",
    "wk-PcwgWhFNx0g0YzUjHHZ0yCUAG1scrq4SMhXtBFUyYk3KD110",
    "wk-FIzBhOWqTUgGj6jZo9cjN6pP2EHEgROqCVqIPPVghJA5dep9",
    "wk-M8KppwUWv8RlKQ6n4p4L2kuYX16QBsZ7J5refe3pppE7t4ir",
    "wk-zynqGMQKSyStyFHAwiE1T6lwhlDKGhedgh0qbmaJ4i22hZBo",
    "wk-HVJO2a07DmR0pt5ogbXcTGhTkrnFYGzd8TpK4lOWaNYeDcz6",
    "wk-yBS4vP6yCD16tJ0rgQQOqCv5EHYigzSiMtiHR27NYGgmsK69",
    "wk-SHxAuoXVvUQoNiiiDf2UckAXm1Mn2O0j2fnfegpYhpLL8roT",
    "wk-aBlZhpt7fuRC0WbKp7Q7sHaWRu945rzrQRfckTHYHcAZRaBk",
]

# 每个 Key 支持的稳定并发度
CONCURRENCY_PER_KEY = 1

# 全局限流（令牌桶）：压住启动洪峰，避免 17 路齐发把服务端打 503
# —— 用户要求：频率太高就降频，慢点可以。这里保守设置。
GLOBAL_RATE_LIMIT = 4.0   # 每秒最大新请求数
GLOBAL_BURST = 4           # 初始令牌桶容量（首波并发上限）

# 全局并发上限：同时最多只允许 N 个请求在“飞行中”，这是降低 503 的关键杠杆
MAX_CONCURRENT_REQUESTS = 5

# 抖动指数退避参数（单轮等待严格封顶 5 秒，绝不超额）
BASE_BACKOFF = 1.0        # 基础退避秒数
MAX_BACKOFF = 5.0         # 单次退避上限（秒）—— 用户要求封顶 5s
MAX_API_RETRIES = 10      # 单个任务最大 API 重试次数（用户指定 10 次）

# 按 Key 的熔断（circuit breaker）参数：仅在该 Key 真的连续失败时临时冷却，
# 不影响任务本身（任务仍会换 Key 继续重试，直到达到最大重试次数）。
KEY_FAILURE_THRESHOLD = 8   # 同一 Key 连续失败达到此次数 → 临时冷却
KEY_COOLDOWN = 30.0         # 临时冷却时长（秒），到期自动恢复
# 至少保留一半 Key 可用，避免把全部 Key 都停掉导致整体停滞
KEY_MIN_ACTIVE = max(1, len(API_KEYS) // 2)

BASE_URL = "https://apihub.agnes-ai.com/v1"  # 官方接口地址
# 默认配置文件路径（相对于脚本所在目录）
DEFAULT_JSON_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_tasks.json")
JSON_CONFIG_PATH = DEFAULT_JSON_CONFIG_PATH  # 使用默认配置文件路径

# ==================== 初始化全局 HTTP 连接池 ====================
# 计算最大工作线程数
MAX_WORKERS = len(API_KEYS) * CONCURRENCY_PER_KEY

# 初始化支持 Keep-Alive 连接复用的 Session 实例
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=MAX_WORKERS,
    pool_maxsize=MAX_WORKERS
)
session.mount("https://", adapter)
session.mount("http://", adapter)
# ================================================================

# ==================== 全局限流 / 协同退避机制 ====================
# 令牌桶：限制整体请求速率，避免启动瞬间 17 路并发把服务端打挂
class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate              # 每秒补充的令牌数
        self.capacity = capacity      # 桶容量（首波突发上限）
        self.tokens = float(capacity)
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, block: bool = True):
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
            if not block:
                return False
            time.sleep(0.05)


class ConcurrencyLimiter:
    """限制同时“在飞行中”的请求数量，直接压低服务端并发压力（治 503 的关键）"""
    def __init__(self, limit: int):
        self._sem = threading.Semaphore(limit)

    def acquire(self):
        self._sem.acquire()

    def release(self):
        self._sem.release()


# 协同退避：某次请求遇到 5xx/429 时标记“服务端过热”，
# 后续重试会在 5s 预算内额外叠加一点抖动，让各线程错峰、瓦解重试风暴（惊群）。
class GlobalBackoff:
    def __init__(self, ttl: float = 3.0):
        self.ttl = ttl
        self.until = 0.0
        self.lock = threading.Lock()

    def mark_busy(self):
        with self.lock:
            self.until = time.monotonic() + self.ttl

    def is_busy(self) -> bool:
        with self.lock:
            return time.monotonic() < self.until

    def reset(self):
        with self.lock:
            self.until = 0.0


# 按 Key 的熔断：长时间连续失败的 Key 临时冷却，避免把请求浪费在“抽风”的 Key 上；
# 401/403 直接永久剔除；冷却到期自动恢复；永不停止全部 Key；且不影响任务继续重试。
class KeyCircuitBreaker:
    def __init__(self, total: int, failure_threshold: int = KEY_FAILURE_THRESHOLD,
                 cooldown: float = KEY_COOLDOWN, min_active: int = KEY_MIN_ACTIVE):
        self.total = total
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self.min_active = min_active
        self.fail_counts = {}        # key -> 连续失败次数
        self.suspended_until = {}    # key -> 冷却到期时间戳（临时）
        self.dead = set()            # 永久剔除的 key（401/403）
        self.lock = threading.Lock()

    def is_usable(self, key, now: float = None) -> bool:
        now = now if now is not None else time.monotonic()
        if key in self.dead:
            return False
        return now >= self.suspended_until.get(key, 0)

    def mark_dead(self, key):
        with self.lock:
            self.dead.add(key)
            self.suspended_until.pop(key, None)
            self.fail_counts.pop(key, None)

    def on_success(self, key):
        with self.lock:
            self.fail_counts[key] = 0

    def on_failure(self, key) -> bool:
        """返回 True 表示该 key 已被临时冷却"""
        with self.lock:
            self.fail_counts[key] = self.fail_counts.get(key, 0) + 1
            if self.fail_counts[key] < self.failure_threshold:
                return False
            # 已达阈值：检查是否还能冷却（不能把所有 Key 都停掉）
            suspended_now = sum(1 for u in self.suspended_until.values() if time.monotonic() < u)
            active = self.total - len(self.dead) - suspended_now
            if active <= self.min_active:
                self.fail_counts[key] = 0  # 重置，避免立刻再次触发
                return False
            self.suspended_until[key] = time.monotonic() + self.cooldown
            self.fail_counts[key] = 0
            return True

    def reap_expired(self):
        """回收已冷却的 key，返回需要重新入队的 key 列表"""
        now = time.monotonic()
        with self.lock:
            expired = [k for k, u in self.suspended_until.items() if now >= u]
            for k in expired:
                del self.suspended_until[k]
            return expired


# 模块级单例
req_limiter = TokenBucket(GLOBAL_RATE_LIMIT, GLOBAL_BURST)
req_limiter_semaphore = ConcurrencyLimiter(MAX_CONCURRENT_REQUESTS)
global_backoff = GlobalBackoff()
key_breaker = KeyCircuitBreaker(total=len(API_KEYS))


def compute_backoff(attempt: int, response=None) -> float:
    """
    返回单次重试等待（秒），严格封顶 MAX_BACKOFF（5s）。
    已把协同退避的额外抖动折进这 5s 预算内，绝不叠加超额。
    """
    base = min(MAX_BACKOFF, BASE_BACKOFF * (2 ** (attempt - 1)))
    wait = random.uniform(0.5, base)
    # 服务端过热时，再叠加一小段抖动（封顶 5s）
    if global_backoff.is_busy():
        wait = min(MAX_BACKOFF, wait + random.uniform(0, 1.0))
    # 尊重 429 的 Retry-After（同样封顶 5s）
    if response is not None:
        ra = parse_retry_after(response)
        if ra:
            wait = min(MAX_BACKOFF, max(wait, ra))
    return wait


def acquire_key(q: queue.Queue, breaker: KeyCircuitBreaker) -> str:
    """从队列取一个可用 Key；队列空时尝试回收已冷却的 Key，避免空转死锁"""
    while True:
        try:
            key = q.get_nowait()
        except queue.Empty:
            for k in breaker.reap_expired():
                q.put(k)
            time.sleep(1.0)  # 全部在冷却中，稍等再试（reaper 会回填）
            continue
        if not breaker.is_usable(key):
            time.sleep(0.1)
            continue
        return key


def _release_key(q: queue.Queue, key, breaker: KeyCircuitBreaker = None):
    """安全地把 Key 还回队列；已冷却/已失效的 Key 不再归还"""
    if key is None:
        return
    if breaker is not None and not breaker.is_usable(key):
        return
    q.put(key)


def parse_retry_after(response) -> float:
    """解析响应头 Retry-After（秒），缺失或非法返回 0"""
    ra = response.headers.get("Retry-After")
    if not ra:
        return 0.0
    try:
        return float(ra)
    except (ValueError, TypeError):
        return 0.0
# ================================================================


def file_to_base64_uri(file_path: str) -> str:
    """读取本地图片文件并将其转化为 Data URI Base64 格式"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"本地文件未找到: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/png"

    with open(file_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64_data}"


def download_image(sess: requests.Session, url: str, save_path: str, log_prefix: str, retries: int = 10, backoff: float = 1.0) -> bool:
    """下载生成的图片并保存到本地，带指数退避重试机制（使用连接池复用）"""
    for attempt in range(1, retries + 1):
        try:
            # 设 5 秒连接超时，120 秒读取超时
            response = sess.get(url, timeout=(5, 120))
            response.raise_for_status()

            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'wb') as f:
                f.write(response.content)
            logging.info(f"{log_prefix} 👉 [成功] 图片已保存至: {save_path}")
            return True
        except Exception as e:
            if attempt < retries:
                # 加上微小随机干扰打散重试时间
                wait = min(backoff * (2 ** (attempt - 1)), 5) + random.uniform(0.1, 0.5)
                logging.warning(f"{log_prefix} ⚠️ [第{attempt}/{retries}次] 下载失败: {e}，{wait:.1f}秒后重试...")
                time.sleep(wait)
            else:
                logging.error(f"{log_prefix} ❌ [错误] 图片下载失败（已重试{retries}次）: {e}")
                return False


def process_single_task(task: dict, key_queue: queue.Queue, project_root: str = None) -> str | None:
    """
    执行单个生图任务。
    设计原则（用户要求）：
      - 绝不中途放弃任务，只有打满 MAX_API_RETRIES 次才判定失败；
      - Key 无限量，尽管用；仅在该 Key 真连续失败时临时冷却（不放弃任务）；
      - 频率过高就降频：全局并发上限 + 令牌桶限速；
      - 单次重试等待严格 ≤ MAX_BACKOFF(5s)。
    """
    task_id = task.get("task_id", "Unknown")
    task_type = task.get("type", "text_to_image")
    prompt = task.get("prompt")
    size = task.get("size", "1024x1024")
    output_path = task.get("output_path", f"./output_{task_id}.png")

    # 如果指定了项目根目录，将相对 output_path 解析为绝对路径
    if project_root and not os.path.isabs(output_path):
        output_path = os.path.join(project_root, output_path)

    log_prefix = f"[{task_id}]"

    # 自动匹配最佳模型
    model = task.get("model")
    if not model:
        if task_type == "text_to_image":
            model = "agnes-image-2.1-flash"
        elif task_type == "image_to_image":
            model = "agnes-image-2.0-flash"

    logging.info(f"{log_prefix} 🚀 任务启动 | 类型: {task_type} | 模型: {model} | 分辨率: {size}")

    # 构建通用 payload
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size
    }

    if task_type == "image_to_image":
        local_image_path = task.get("local_image_path")
        if not local_image_path:
            logging.error(f"{log_prefix} ❌ [失败] 图生图任务必须提供本地图片路径 'local_image_path'。")
            return None

        try:
            # 提示：如果是极高分辨率的本地大图，建议在转 Base64 之前先进行尺寸压制，以节约网络上传带宽
            base64_uri = file_to_base64_uri(local_image_path)
            payload["extra_body"] = {
                "image": [base64_uri]
            }
        except Exception as e:
            logging.error(f"{log_prefix} ❌ [本地错误] 读取本地图片失败: {e}")
            return None

    endpoint = f"{BASE_URL}/images/generations"
    generated_url = None
    api_key = None

    # 统一的重试循环：每次重试都重新拿 Key、重新发请求，直到成功或打满 MAX_API_RETRIES
    for attempt in range(1, MAX_API_RETRIES + 1):
        # 1) 并发上限（压低服务端并发压力）
        req_limiter_semaphore.acquire()
        try:
            # 2) 全局限速：压住启动洪峰
            req_limiter.acquire()
            # 3) 从队列获取一个可用 Key（按 Key 熔断已自动隔离坏 Key，但任务会换 Key 继续）
            api_key = acquire_key(key_queue, key_breaker)

            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                # 发送 API 请求（连接超时 5s，读取超时 90s）
                response = session.post(endpoint, headers=headers, json=payload, timeout=(5, 90))
                code = response.status_code

                # 1. 请求成功
                if code == 200:
                    res_json = response.json()
                    image_list = res_json.get("data", [])
                    if image_list and len(image_list) > 0:
                        generated_url = image_list[0].get("url")
                        if generated_url:
                            key_breaker.on_success(api_key)   # 该 Key 恢复正常
                            global_backoff.reset()            # 服务端恢复，解除协同退避
                            break
                        else:
                            logging.error(f"{log_prefix} ❌ [解析错误] 返回结构正常，但没有找到图片 URL")
                    else:
                        logging.error(f"{log_prefix} ❌ [响应异常] 接口返回值未包含预期图像：{res_json}")

                # 2. 鉴权失败/额度不足 (401/403) —— 该 Key 永久失效，剔除后换 Key 继续重试
                elif code in (401, 403):
                    key_breaker.mark_dead(api_key)
                    logging.error(f"{log_prefix} ❌ [密钥失效/无额度] (HTTP {code}) 该 Key 已永久剔除，换 Key 重试！")
                    api_key = None  # 不归还，下一轮换 Key
                    continue

                # 3. 频控限流 (429) —— 尊重 Retry-After，抖动后重试（不放弃任务）
                elif code == 429:
                    global_backoff.mark_busy()
                    wait = compute_backoff(attempt, response)
                    logging.warning(f"{log_prefix} ⚠️ [触发频控 (429)] 将在 {wait:.1f}s 后抖动重试（第{attempt}/{MAX_API_RETRIES}次）...")
                    time.sleep(wait)
                    _release_key(key_queue, api_key, key_breaker)
                    api_key = None

                # 4. 客户端错误 (400) 或其他服务端错误 (5xx/500) —— 一律当作可重试错误，抖动后重试，绝不中途放弃
                else:
                    global_backoff.mark_busy()
                    suspended = key_breaker.on_failure(api_key)  # 累计失败，可能触发临时冷却
                    if suspended:
                        logging.warning(f"{log_prefix} ⚠️ [HTTP {code}] Key 连续失败已达阈值，临时冷却 {KEY_COOLDOWN:.0f}s（任务仍换 Key 继续）")
                    wait = compute_backoff(attempt, response if code == 429 else None)
                    label = "客户端错误 (HTTP 400)" if code == 400 else f"服务端错误 (HTTP {code})"
                    logging.warning(f"{log_prefix} ⚠️ [{label}] 将在 {wait:.1f}s 后抖动重试（第{attempt}/{MAX_API_RETRIES}次）...")
                    time.sleep(wait)
                    _release_key(key_queue, api_key, key_breaker)
                    api_key = None

            except requests.exceptions.RequestException as e:
                global_backoff.mark_busy()
                suspended = key_breaker.on_failure(api_key)
                if suspended:
                    logging.warning(f"{log_prefix} ⚠️ [网络错误] Key 连续失败已达阈值，临时冷却 {KEY_COOLDOWN:.0f}s（任务仍继续）")
                wait = compute_backoff(attempt)
                logging.warning(f"{log_prefix} ⚠️ [网络错误] 请求 API 失败: {e}，将在 {wait:.1f}s 后抖动重试（第{attempt}/{MAX_API_RETRIES}次）...")
                time.sleep(wait)
                _release_key(key_queue, api_key, key_breaker)
                api_key = None
            except Exception as e:
                logging.error(f"{log_prefix} ❌ [未知异常] 执行过程中出错: {e}")
                _release_key(key_queue, api_key, key_breaker)
                api_key = None
                break
        finally:
            # 释放并发额度，让其他等待中的任务可以发起请求
            req_limiter_semaphore.release()

    # 归还仍持有的 Key（成功/正常结束路径）
    _release_key(key_queue, api_key, key_breaker)

    # 在释放 Key 后，在本地线程里慢慢进行下载（下载不占用 API 的 Key 限制）
    if generated_url:
        logging.info(f"{log_prefix} 🎨 图像已由 Agnes 生成成功，正在下载中...")
        if download_image(session, generated_url, output_path, log_prefix):
            return output_path

    logging.error(f"{log_prefix} ❌ [最终失败] 已重试 {MAX_API_RETRIES} 次仍未成功。")
    return None


def generate_html_gallery(image_paths: list[str], output_html: str):
    """将成功生成的图片列表写入一个 HTML 页面，图片尺寸与实际尺寸适配"""
    cards = []
    for idx, path in enumerate(image_paths):
        abs_path = os.path.abspath(path)
        filename = os.path.basename(abs_path)
        file_uri = Path(abs_path).as_uri()
        cards.append(f"""    <div class="card" id="card-{idx}">
      <img src="{file_uri}" alt="{filename}" loading="lazy" data-idx="{idx}" onload="adjustCardSize(this)">
      <div class="info">
        <div class="filename">{filename}</div>
        <div class="filepath">{abs_path}</div>
      </div>
    </div>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 图片生成结果 - 共 {len(image_paths)} 张</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #f5f5f5; padding: 30px; }}
h1 {{ font-size: 24px; margin-bottom: 20px; color: #333; }}
h1 span {{ font-weight: normal; font-size: 16px; color: #888; }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
.card {{ background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); transition: transform 0.15s; display: flex; flex-direction: column; }}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.12); }}
.card img {{ width: 100%; display: block; cursor: pointer; object-fit: contain; background: #fafafa; }}
.card .info {{ padding: 12px 16px; }}
.card .filename {{ font-size: 14px; font-weight: 600; color: #222; word-break: break-all; }}
.card .filepath {{ font-size: 11px; color: #999; word-break: break-all; margin-top: 4px; }}
</style>
</head>
<body>
<h1>AI 图片生成结果 <span>共 {len(image_paths)} 张</span></h1>
<div class="gallery">
{chr(10).join(cards)}
</div>
<script>
function adjustCardSize(img) {{
  // 获取图片原始宽高比
  const ratio = img.naturalWidth / img.naturalHeight;
  // 设置最大高度为 500px，根据宽高比计算实际高度
  const maxHeight = 500;
  const maxWidth = img.parentElement.offsetWidth;
  let height = Math.min(maxWidth / ratio, maxHeight);
  // 如果高度受限，则根据高度反算宽度
  if (height < maxWidth / ratio) {{
    img.style.width = (height * ratio) + 'px';
    img.style.height = height + 'px';
  }}
}}
</script>
</body>
</html>"""

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)

    abs_html = os.path.abspath(output_html)
    logging.info(f"HTML 页面已生成: {abs_html}")


def run_batch_concurrency(config_path: str):
    """主并发控制函数"""
    if not os.path.exists(config_path):
        logging.error(f"配置文件不存在: {config_path}")
        return

    if not API_KEYS or (len(API_KEYS) == 1 and API_KEYS[0] == "YOUR_SECOND_API_KEY"):
        logging.error("请在全局配置区中正确配置 API_KEYS 列表。")
        return

    # 从配置文件路径推导项目根目录
    config_dir = os.path.dirname(os.path.abspath(config_path))
    parent1 = os.path.basename(config_dir)
    parent2 = os.path.basename(os.path.dirname(config_dir))
    parent3 = os.path.basename(os.path.dirname(os.path.dirname(config_dir)))

    if parent3 == "output":
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(config_dir)))
    elif parent2 == "output":
        project_root = os.path.dirname(os.path.dirname(config_dir))
    else:
        project_root = os.path.dirname(config_dir)
    logging.info(f"项目根目录推导结果: {project_root}")

    with open(config_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    # 1. 初始化线程安全的 API Key 队列
    key_queue = queue.Queue()
    for key in API_KEYS:
        for _ in range(CONCURRENCY_PER_KEY):
            key_queue.put(key)

    logging.info("批量并发任务开始运行。")
    logging.info(f"检测到已配置 {len(API_KEYS)} 个 API Key（无限量），每个 Key 限制并发数: {CONCURRENCY_PER_KEY}")
    logging.info(f"系统最大并发工作线程数: {MAX_WORKERS}；同时在飞请求上限: {MAX_CONCURRENT_REQUESTS}")
    logging.info(f"全局限速: {GLOBAL_RATE_LIMIT} req/s（首波突发 {GLOBAL_BURST}）；单次退避封顶 {MAX_BACKOFF:.0f}s；"
                 f"单任务最大重试 {MAX_API_RETRIES} 次（打满才判定失败，绝不中途放弃）；"
                 f"Key 熔断: 连续失败 {KEY_FAILURE_THRESHOLD} 次冷却 {KEY_COOLDOWN:.0f}s（保留≥{KEY_MIN_ACTIVE}个可用）")

    successful_images = []

    # 2. 采用线程池执行任务（启动阶段轻微错峰，配合令牌桶压住洪峰）
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for i, task in enumerate(tasks):
            futures[executor.submit(process_single_task, task, key_queue, project_root)] = task
            # 仅对首波任务做轻微错峰，避免 17 路在同一毫秒内全部 submit
            if i < MAX_WORKERS:
                time.sleep(random.uniform(0.1, 0.4))

        # 观察并等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            task_id = task.get("task_id", "Unknown")
            try:
                result = future.result()
                if result:
                    successful_images.append(result)
            except Exception as e:
                logging.error(f"[{task_id}] 线程执行期间产生致命故障: {e}")

    logging.info(f"并发任务队列处理完毕，成功生成了 {len(successful_images)} 张图片。")

    if successful_images:
        successful_images.sort()
        html_path = os.path.join(os.path.dirname(config_path), "image_gallery.html")
        generate_html_gallery(successful_images, html_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AI 图片批量生成脚本 (V5 - 限流/并发上限/Key熔断优化版)')
    parser.add_argument('-c', '--config', type=str, default=JSON_CONFIG_PATH,
                        help=f'JSON 配置文件路径 (默认: {JSON_CONFIG_PATH})')
    args = parser.parse_args()

    setup_logging()
    run_batch_concurrency(args.config)
