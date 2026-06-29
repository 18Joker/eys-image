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
CONCURRENCY_PER_KEY = 1

BASE_URL = "https://apihub.agnes-ai.com/v1"  # 官方接口地址
# 默认配置文件路径（相对于脚本所在目录）
DEFAULT_JSON_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_tasks.json")
JSON_CONFIG_PATH = None  # 运行时动态设置

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


def analyze_single_image(task: dict, key_queue: queue.Queue) -> dict | None:
    """
    执行单个图片分析任务
    从密钥队列中动态获取可用的 API Key，并在调用完成后立即释放（支持坏Key自动剔除与API重试）
    """
    task_id = task.get("task_id", "Unknown")
    local_image_path = task.get("local_image_path")
    output_json = task.get("output_json", f"./output_{task_id}.json")
    
    log_prefix = f"[{task_id}]"

    if not local_image_path:
        logging.error(f"{log_prefix} ❌ [失败] 必须提供本地图片路径 'local_image_path'。")
        return None

    # 构建视觉模型 prompt - 专门用于提取角色信息
    prompt = """请分析这张游戏截图，识别左侧玩家列表中的序号和对应的角色名称。

要求：
1. 只关注左侧的玩家列表区域
2. 提取每个玩家的序号（如：06号、07号等）
3. 提取每个玩家的角色名称（如：模仿者、大白鹅、探测员等）
4. 忽略"随机"选项
5. 返回JSON格式，包含以下结构：
   {
     "players": [
       {"number": "06", "role": "模仿者"},
       {"number": "07", "role": "大白鹅"}
     ]
   }

注意：
- number字段只需要数字部分（不带"号"字）
- role字段是完整的角色名称
- 按序号从小到大排序
"""

    try:
        base64_uri = file_to_base64_uri(local_image_path)
    except Exception as e:
        logging.error(f"{log_prefix} ❌ [本地错误] 读取本地图片失败: {e}")
        return None

    endpoint = f"{BASE_URL}/chat/completions"
    result_data = None
    
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

            # 构建多模态消息 payload
            payload = {
                "model": "agnes-2.0-flash",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": base64_uri
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }

            # 发送 API 请求（连接超时 5s，读取超时 90s）
            response = session.post(endpoint, headers=headers, json=payload, timeout=(5, 90))

            # 1. 请求成功
            if response.status_code == 200:
                res_json = response.json()
                content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if content:
                    # 尝试解析 JSON 内容
                    try:
                        # 如果返回的内容包含在代码块中，提取出来
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        
                        result_data = json.loads(content)
                        break  # 成功获取结果，终止重试循环
                    except json.JSONDecodeError as e:
                        logging.warning(f"{log_prefix} ⚠️ [解析警告] JSON解析失败: {e}")
                        logging.debug(f"{log_prefix} 原始内容: {content[:200]}")
                        # 继续重试
                else:
                    logging.error(f"{log_prefix} ❌ [响应异常] 接口返回值未包含预期内容：{res_json}")

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
            logging.error(f"{log_prefix}  [未知异常] 执行过程中出错: {e}")
        finally:
            # 关键改动：如果判断 Key 未失效，将其完好放回队列供后续复用
            # 如果 Key 被判定为失效(401/403)，则不返回队列（即动态从系统里过滤掉此 Key）
            if is_key_valid:
                key_queue.put(api_key)

    # 保存结果到 JSON 文件
    if result_data:
        logging.info(f"{log_prefix} ✅ [成功] 图片分析完成，正在保存结果...")
        
        path = Path(output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"{log_prefix} 👉 [成功] 结果已保存至: {output_json}")
        return result_data

    return None


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
        # 每个 Key 放入 CONCURRENCY_PER_KEY 次，作为并发"通行证"
        for _ in range(CONCURRENCY_PER_KEY):
            key_queue.put(key)

    logging.info("批量并发图片分析任务开始运行。")
    logging.info(f"检测到已配置 {len(API_KEYS)} 个 API Key，每个 Key 限制并发数为: {CONCURRENCY_PER_KEY}")
    logging.info(f"系统最大并发工作线程数已自动调整为: {MAX_WORKERS}")

    successful_results = []

    # 2. 采用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        futures = {executor.submit(analyze_single_image, task, key_queue): task for task in tasks}

        # 观察并等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            task_id = task.get("task_id", "Unknown")
            try:
                result = future.result()
                if result:
                    successful_results.append({
                        "task_id": task_id,
                        "result": result
                    })
            except Exception as e:
                logging.error(f"[{task_id}] 线程执行期间产生致命故障: {e}")

    logging.info(f"并发任务队列处理完毕，成功分析了 {len(successful_results)} 张图片。")
    
    # 汇总所有结果到一个总文件
    if successful_results:
        summary_path = os.path.join(os.path.dirname(config_path), "analysis_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(successful_results, f, ensure_ascii=False, indent=2)
        logging.info(f"汇总结果已保存至: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AI 图片批量分析脚本 - 从游戏截图中提取角色信息')
    parser.add_argument('-c', '--config', type=str, default=JSON_CONFIG_PATH,
                        help=f'JSON 配置文件路径 (默认: {JSON_CONFIG_PATH})')
    args = parser.parse_args()
    
    setup_logging()
    run_batch_concurrency(args.config)
