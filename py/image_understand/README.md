# 图片理解脚本 - 从游戏截图中提取角色信息

## 功能说明

本脚本用于从 Goose Goose Duck 游戏截图中自动识别玩家序号和对应的角色名称。使用 Agnes AI 的视觉模型进行图片分析，支持批量处理和多 API Key 并发调用。

## 目录结构

```
image_understand/
├── image_analyze.py      # 主程序脚本
├── batch_tasks.json      # 任务配置文件（需自定义）
├── README.md             # 本文档
├── input/                # 输入图片目录（需创建）
│   └── screenshot.png    # 示例截图
└── output/               # 输出结果目录（自动生成）
    ├── screenshot_001_result.json
    └── analysis_summary.json
```

## 快速开始

### 1. 准备输入图片

将需要分析的游戏截图放入 `input/` 目录：

```bash
mkdir -p input
# 将截图复制到 input/ 目录下
cp your_screenshot.png input/screenshot.png
```

### 2. 配置任务文件

编辑 `batch_tasks.json`，添加需要处理的图片任务：

```json
[
  {
    "task_id": "screenshot_001",
    "type": "image_analysis",
    "local_image_path": "./input/screenshot.png",
    "output_json": "./output/screenshot_001_result.json"
  },
  {
    "task_id": "screenshot_002",
    "type": "image_analysis",
    "local_image_path": "./input/screenshot2.png",
    "output_json": "./output/screenshot_002_result.json"
  }
]
```

**字段说明：**
- `task_id`: 任务唯一标识符（建议使用有意义的名称）
- `type`: 任务类型（固定为 `image_analysis`）
- `local_image_path`: 本地图片路径（相对于脚本所在目录）
- `output_json`: 输出 JSON 文件路径

### 3. 运行脚本

```bash
cd py/image_understand
python image_analyze.py -c batch_tasks.json
```

或使用默认配置文件：

```bash
python image_analyze.py
```

### 4. 查看结果

脚本执行完成后，会生成以下文件：

1. **单个任务结果**：`output/screenshot_001_result.json`
   ```json
   {
     "players": [
       {"number": "06", "role": "模仿者"},
       {"number": "07", "role": "大白鹅"},
       {"number": "08", "role": "探测员"},
       {"number": "10", "role": "工程师"},
       {"number": "11", "role": "加拿大鹅"}
     ]
   }
   ```

2. **汇总结果**：`output/analysis_summary.json`
   ```json
   [
     {
       "task_id": "screenshot_001",
       "result": {
         "players": [...]
       }
     },
     {
       "task_id": "screenshot_002",
       "result": {
         "players": [...]
       }
     }
   ]
   ```

## 高级用法

### 修改识别逻辑

如需调整识别规则，请编辑 `image_analyze.py` 中的 `prompt` 变量（第 95-115 行）：

```python
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
```

### 调整并发参数

在 `image_analyze.py` 顶部修改以下配置（第 32-54 行）：

```python
# API Keys 列表（支持多个 Key 轮询）
API_KEYS = [
    "wk-KyLbGDsypO862KC9dBbBolyscal8p3hmvSf96Un0lzpUtNpr",
    "wk-tMZW7YP1ob8fsXcwoax9Iyl8mxl6QJuRIJhs4dCrT7Vky1S7",
    # ... 更多 Key
]

# 每个 Key 支持的稳定并发度
CONCURRENCY_PER_KEY = 1  # 建议保持为 1，避免触发频控
```

### 更换视觉模型

如需使用其他视觉模型，修改第 177 行的 `model` 参数：

```python
payload = {
    "model": "agnes-2.0-flash",  # 当前使用的模型
    "messages": [...]
}
```

## 常见问题

### Q: 如何获取更多 API Key？

A: 请访问 [Agnes AI Hub](https://apihub.agnes-ai.com) 注册并获取 API Key。

### Q: 图片识别不准确怎么办？

A: 
1. 确保截图清晰，玩家列表完整可见
2. 调整 prompt 中的描述，使其更符合实际场景
3. 尝试降低 `temperature` 参数（第 189 行），提高稳定性

### Q: 遇到 429 频控错误怎么办？

A: 脚本已内置重试机制，会自动等待后换 Key 重试。如需降低触发频率：
1. 减少 `CONCURRENCY_PER_KEY` 的值
2. 增加请求间隔（第 174 行的 `time.sleep()`）

### Q: 如何处理大量图片？

A: 脚本采用线程池并发处理，只需在 `batch_tasks.json` 中添加更多任务即可。建议：
1. 分批处理（每批 10-20 张）
2. 监控日志输出，及时处理失败的任务
3. 定期清理 `output/` 目录，避免占用过多磁盘空间

## 技术特性

- ✅ 多 API Key 轮询，自动剔除失效 Key
- ✅ 指数退避重试机制，应对网络波动和频控
- ✅ 线程池并发处理，提升批量任务效率
- ✅ HTTP 连接池复用，减少握手开销
- ✅ 完善的日志系统，便于问题排查
- ✅ JSON 结果汇总，方便后续数据处理

## 依赖项

```bash
pip install requests
```

## 许可证

本项目仅供学习和研究使用。
