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
# 支持填入多个 API Key
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
CONCURRENCY_PER_KEY = 3

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


def download_image(sess: requests.Session, url: str, save_path: str, log_prefix: str, retries: int = 3, backoff: float = 1.0) -> bool:
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
                wait = backoff * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                logging.warning(f"{log_prefix} ⚠️ [第{attempt}/{retries}次] 下载失败: {e}，{wait:.1f}秒后重试...")
                time.sleep(wait)
            else:
                logging.error(f"{log_prefix} ❌ [错误] 图片下载失败（已重试{retries}次）: {e}")
                return False


def process_single_task(task: dict, key_queue: queue.Queue) -> str | None:
    """
    执行单个生图任务
    从密钥队列中动态获取可用的 API Key，并在调用完成后立即释放（支持坏Key自动剔除与API重试）
    """
    task_id = task.get("task_id", "Unknown")
    task_type = task.get("type", "text_to_image")
    prompt = task.get("prompt")
    size = task.get("size", "1024x1024")
    output_path = task.get("output_path", f"./output_{task_id}.png")

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

    max_api_retries = 3

    # 针对 API 请求阶段建立重试机制，每次重试均从队列重新抓取 Key 进行调用
    for attempt in range(1, max_api_retries + 1):
        # 从队列中获取一个可用的 API Key (如果没有多余的 Key 此时会阻塞等待)
        api_key = key_queue.get()
        is_key_valid = True  # 标记此 Key 当前是否依然健康可用

        # 请求前引入轻微随机延迟，打散请求，降低触发 IP 级频控的概率
        time.sleep(random.uniform(0.05, 0.2))

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # 发送 API 请求（连接超时 5s，读取超时 90s）
            response = session.post(endpoint, headers=headers, json=payload, timeout=(5, 90))

            # 1. 请求成功
            if response.status_code == 200:
                res_json = response.json()
                image_list = res_json.get("data", [])

                if image_list and len(image_list) > 0:
                    generated_url = image_list[0].get("url")
                    if not generated_url:
                        logging.error(f"{log_prefix} ❌ [解析错误] 返回结构正常，但没有找到图片 URL")
                    else:
                        # 成功获取到图片 URL，终止重试循环
                        break
                else:
                    logging.error(f"{log_prefix} ❌ [响应异常] 接口返回值未包含预期图像：{res_json}")

            # 2. 鉴权失败/额度不足 (401/403)
            elif response.status_code in (401, 403):
                logging.error(f"{log_prefix} ❌ [密钥失效/无额度] (HTTP {response.status_code}) 当前 Key 标记为失效，不再放回队列！")
                is_key_valid = False
                # 继续循环，让下一次重试使用新 Key 重新生图

            # 3. 频控限流 (429)
            elif response.status_code == 429:
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                logging.warning(f"{log_prefix} ⚠️ [触发频控 (429)] 等待 {wait_time:.1f} 秒后换 Key 重试...")
                time.sleep(wait_time)

            # 4. 其他服务端错误 (5xx)
            else:
                wait_time = 2 ** attempt
                logging.warning(f"{log_prefix} ⚠️ [服务端错误 (HTTP {response.status_code})] 将在 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        except requests.exceptions.RequestException as e:
            wait_time = 2 ** attempt
            logging.warning(f"{log_prefix} ⚠️ [网络错误 (尝试 {attempt}/{max_api_retries})] 请求 API 失败: {e}，将在 {wait_time} 秒后重试...")
            time.sleep(wait_time)
        except Exception as e:
            logging.error(f"{log_prefix} ❌ [未知异常] 执行过程中出错: {e}")
        finally:
            # 关键改动：如果判断 Key 未失效，将其完好放回队列供后续复用
            # 如果 Key 被判定为失效(401/403)，则不返回队列（即动态从系统里过滤掉此 Key）
            if is_key_valid:
                key_queue.put(api_key)

    # 在释放 Key 后，在本地线程里慢慢进行下载（下载不占用 API 的 Key 限制）
    if generated_url:
        logging.info(f"{log_prefix} 🎨 图像已由 Agnes 生成成功，正在下载中...")
        if download_image(session, generated_url, output_path, log_prefix):
            return output_path

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

    with open(config_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    # 1. 初始化线程安全的 API Key 队列
    key_queue = queue.Queue()
    for key in API_KEYS:
        # 每个 Key 放入 CONCURRENCY_PER_KEY 次，作为并发“通行证”
        for _ in range(CONCURRENCY_PER_KEY):
            key_queue.put(key)

    logging.info("批量并发任务开始运行。")
    logging.info(f"检测到已配置 {len(API_KEYS)} 个 API Key，每个 Key 限制并发数为: {CONCURRENCY_PER_KEY}")
    logging.info(f"系统最大并发工作线程数已自动调整为: {MAX_WORKERS}")

    successful_images = []

    # 2. 采用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        futures = {executor.submit(process_single_task, task, key_queue): task for task in tasks}

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
    parser = argparse.ArgumentParser(description='AI 图片批量生成脚本')
    parser.add_argument('-c', '--config', type=str, default=JSON_CONFIG_PATH,
                        help=f'JSON 配置文件路径 (默认: {JSON_CONFIG_PATH})')
    args = parser.parse_args()
    
    setup_logging()
    run_batch_concurrency(args.config)