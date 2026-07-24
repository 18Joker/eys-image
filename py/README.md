# eys-image / py 脚本工具集

鹅鸭杀（Goose Goose Duck）相关图片处理脚本集合：本地 PNG 压缩、Agnes AI 批量生图（文生图 / 图生图）、游戏截图角色 OCR 提取。

---

## 1. 环境准备（conda 激活）

所有脚本依赖 `Pillow` 与 `requests`，已统一安装在 **`eys-ocr`** 这个 conda 环境里（PIL 12.2.0 + requests 已验证）。

### 激活命令

**Git Bash / WSL：**
```bash
source /d/program/tools/conda/conda/etc/profile.d/conda.sh
conda activate eys-ocr
```

**Windows CMD / PowerShell：**
```bat
D:\program\tools\conda\conda\Scripts\activate.bat eys-ocr
```
```powershell
D:\program\tools\conda\conda\Scripts\activate.ps1 eys-ocr
```

**不想激活、直接用解释器（最省事）：**
```bash
/d/program/tools/conda/envs/eys-ocr/python.exe compress_inplace.py ...
```

> 验证环境：`python -c "import PIL, requests; print('ok')"`

如果需要在别的环境重装依赖：
```bash
pip install Pillow requests
```

---

## 2. 脚本清单

| 脚本 | 用途 | 类型 |
|------|------|------|
| `compress_images.py` | 把源文件夹图片压缩后输出到**新**文件夹（不破坏原图） | 本地图像处理 |
| `compress_inplace.py` | 递归遍历指定目录，把超过阈值的图片**就地覆盖**压缩 | 本地图像处理 |
| `image_generate_v4.py` | Agnes AI 批量生图（基础并发版） | AI 生图 |
| `image_generate_v5.py` | Agnes AI 批量生图（含限流/并发上限/Key 熔断，**推荐**） | AI 生图 |
| `image_understand/image_analyze.py` | 从游戏截图中批量提取玩家序号+角色名（视觉模型） | AI 分析 |

> `image_generate_v4.py` 与 `image_generate_v5.py` 功能一致，v5 额外做了全局限流、并发上限、按 Key 熔断，跑大量任务时更稳（不易触发 503）。**日常用 v5。**

---

## 3. 图片压缩脚本

### 3.1 `compress_images.py` — 输出到新文件夹（安全，不覆盖原图）

默认从配置文件 `TASKS` 读取「源目录 → 目标目录」映射，压缩后写入新目录，原图不动。

**改配置**：编辑脚本顶部 `TASKS`、`MODE`。
```python
TASKS = [
    {"src": "official_camps_v2", "dst": "official_camps_v3"},
]
MODE = "palette"   # "palette" 近无损(默认) / "lossless" 纯无损重压
```

**运行**：
```bash
cd /d/program/project/front/eys-image/py
python compress_images.py
```

**输出示例**：
```
压缩模式: palette  |  调色板颜色: 256
▶ 处理 official_camps_v2  ->  official_camps_v3
  duck/duck_狙击手.png           1240.5KB -> 680.2KB  (-45.2%)
  ...
  ✓ 共 50 张,  58.30MB -> 31.20MB  (节省 46.5%)
```

### 3.2 `compress_inplace.py` — 就地覆盖（慎用）

递归压缩目录内所有超阈值的图片并**直接覆盖原文件**；也支持直接传**单张图片路径**。仅压缩后确实更小才覆盖，且用临时文件原子替换，避免损坏。

**命令行示例**：
```bash
# 压缩 official_camps_v3 下所有 >800KB 的图片（palette 模式）
python compress_inplace.py "D:\program\project\front\eys-image\official_camps_v3" --threshold 800 --mode palette

# 只压缩单张图片
python compress_inplace.py "D:\program\project\front\eys-image\official_camps_v3\duck\duck_小黄鸭.png" --threshold 500

# 纯无损重压
python compress_inplace.py "D:\program\project\front\eys-image\official_v4" --mode lossless
```

**不传参**则使用脚本内 `TASKS`/`TARGET_DIR` 固定配置运行。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target` | 脚本内 `TARGET_DIR` | 目标文件夹路径 |
| `--threshold` | `800` | 大小阈值（KB），仅压缩超过此值的文件 |
| `--mode` | `palette` | `palette` 近无损 / `lossless` 无损 |

---

## 4. Agnes AI 批量生图

调用 `https://apihub.agnes-ai.com/v1/images/generations`，支持文生图与图生图，多 Key 并发 + 重试。**API Key 已内置在脚本 `API_KEYS` 列表中。**

### 4.1 任务配置文件 `batch_tasks.json`

与脚本同目录，是一个任务数组。当前示例任务是「把阵营 logo 背景改成深绯红」的图生图：

```json
[
  {
    "task_id": "bg_duck_duck_狙击手",
    "type": "image_to_image",
    "prompt": "Recolor ONLY the flat solid background ... (英文指令)",
    "prompt_zh": "仅将这张 2D 卡通游戏图标的纯色背景重新着色为深暗红色 ...",
    "size": "1024x1024",
    "local_image_path": "D:\\program\\project\\front\\eys-image\\official_camps_v1\\duck\\duck_狙击手.png",
    "output_path": "D:\\program\\project\\front\\eys-image\\official_camps_v2\\duck\\duck_狙击手.png",
    "model": "agnes-image-2.0-flash"
  }
]
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `task_id` | ✅ | 任务唯一标识，用于日志与文件名 |
| `type` | ✅ | `text_to_image` 文生图 / `image_to_image` 图生图 |
| `prompt` | ✅ | 英文生成指令 |
| `size` | ❌ | 分辨率，默认 `1024x1024` |
| `local_image_path` | 图生图必填 | 输入图本地路径（转 base64 上传） |
| `output_path` | ❌ | 输出路径，默认 `./output_{task_id}.png` |
| `model` | ❌ | 不填自动选：文生图 `agnes-image-2.1-flash`，图生图 `agnes-image-2.0-flash` |
| `prompt_zh` | ❌ | 中文备注，仅文档用途，不参与请求 |

> 项目根目录会被脚本自动推导（依据 `batch_tasks.json` 的位置），相对 `output_path` 会解析为绝对路径。

### 4.2 运行

```bash
# 使用同目录默认 batch_tasks.json
python image_generate_v5.py

# 指定其他配置文件
python image_generate_v5.py -c path/to/your_tasks.json
```

**文生图任务示例**（加入 `batch_tasks.json`）：
```json
{
  "task_id": "poster_goose_01",
  "type": "text_to_image",
  "prompt": "Flat 2D cartoon game icon of a white goose, bold black outline, cel-shading, plain background, Goose Goose Duck style",
  "size": "1024x1024",
  "output_path": "D:\\program\\project\\front\\eys-image\\generated-images\\poster_goose_01.png"
}
```

### 4.3 输出

- 每张成功图片写入 `output_path`
- 全部完成后在同目录生成 `image_gallery.html`（浏览器打开可网格预览所有成果图）

---

## 5. 游戏截图角色提取 `image_understand/image_analyze.py`

用视觉模型从鹅鸭杀截图里抽出「玩家序号 + 角色名」，输出 JSON。详见子目录 `image_understand/README.md`。

**快速示例**：
```bash
cd /d/program/project/front/eys-image/py/image_understand
python image_analyze.py -c batch_tasks.json
```

`batch_tasks.json` 任务项（`type` 固定 `image_analysis`）：
```json
[
  {
    "task_id": "screenshot_001",
    "type": "image_analysis",
    "local_image_path": "./input/screenshot.png",
    "output_json": "./output/screenshot_001_result.json"
  }
]
```
输出 `./output/screenshot_001_result.json` + 汇总 `analysis_summary.json`：
```json
{ "players": [ {"number": "06", "role": "模仿者"}, {"number": "07", "role": "大白鹅"} ] }
```

---

## 6. 常见工作流

**A. 跑完 v5 生图后顺手压缩输出目录**
```bash
python image_generate_v5.py -c batch_tasks.json
python compress_inplace.py "D:\program\project\front\eys-image\official_camps_v2" --threshold 500
```

**B. 多批生图不互相干扰**
把每批任务放到独立 `batch_tasks_xxx.json`，分别调用：
```bash
python image_generate_v5.py -c batch_tasks_camps.json
python image_generate_v5.py -c batch_tasks_posters.json
```

**C. 一次性近无损压缩整个项目旧目录**
编辑 `compress_images.py` 的 `TASKS` 增加映射，再 `python compress_images.py`。

---

## 7. 依赖

```bash
pip install Pillow requests
```

AI 脚本还需可访问 `https://apihub.agnes-ai.com`（联网）。
