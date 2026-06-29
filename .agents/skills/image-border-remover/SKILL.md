---
name: image-border-remover
description: 去除指定文件夹下所有图片的边框（包括装饰性边框、白色边缘、固定宽度边框等所有类型边框）。当用户提到去除图片边框、移除图片边框、清理图片边缘、处理图片边框、批量处理图片、生成对比页面时使用此skill。支持批量处理，生成对比HTML让用户确认。自动扫描文件夹、生成图生图任务、执行图片生成、输出到新文件夹、生成对比HTML并打开浏览器。
---

# Image Border Remover

去除图片边框的自动化工具，支持批量处理并生成对比预览。

## 工作流程

### 1. 扫描图片文件

扫描用户指定的文件夹，识别所有支持的图片格式（png, jpg, jpeg, webp, bmp）。

```python
import os
from pathlib import Path

def scan_images(folder_path: str, recursive: bool = False) -> list[str]:
    """扫描指定文件夹下的所有图片文件（已去重）"""
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    images = []
    
    if not os.path.exists(folder_path):
        return images
    
    folder = Path(folder_path)
    seen = set()  # 使用set去重
    
    for ext in supported_formats:
        pattern_func = folder.rglob if recursive else folder.glob
        
        for img in pattern_func(f"*{ext}"):
            img_str = str(img.resolve())
            if img_str not in seen:
                seen.add(img_str)
                images.append(img_str)
        
        for img in pattern_func(f"*{ext.upper()}"):
            img_str = str(img.resolve())
            if img_str not in seen:
                seen.add(img_str)
                images.append(img_str)
    
    return images
```

**注意事项**：
- 如果文件夹不存在，需要先创建
- 如果文件夹为空，需要提示用户
- 支持大小写不敏感的文件扩展名
- **默认不递归**：避免重复扫描子文件夹
- **自动去重**：使用绝对路径去重，确保无重复任务

### 2. 生成图生图任务JSON

为每个图片生成一个去除边框的图生图任务。使用固定模板生成prompt：

```json
{
  "task_id": "border_removal_原文件名",
  "type": "image_to_image",
  "prompt": "Remove all borders, frames, and decorative edges from this image. Keep only the main content, crop or extend to remove any border elements. Clean, seamless result.",
  "local_image_path": "原图完整路径",
  "size": "1024x1024",
  "output_path": "输出路径/原文件名_no_border.png"
}
```

**Prompt模板说明**：
- 英文prompt确保模型理解去除边框的需求
- 保留原图主要内容
- 去除所有装饰性边框和边缘
- 生成干净、无边框的结果

**任务ID命名规则**：
- 使用`border_removal_`前缀
- 后接原文件名（不含扩展名）
- 示例：`border_removal_goose_殡仪员`

### 3. 执行图片生成脚本

使用项目中的`image_generate_v4.py`脚本执行批量任务：

```bash
# 推荐：直接传递配置文件路径
python "<项目根目录>/py/image_generate_v4.py" "<batch_tasks.json路径>"

# 示例
python "D:\program\project\front\eys-image\py\image_generate_v4.py" "D:\test_images_no_border\batch_tasks.json"
```

**脚本执行前检查**：
1. 确认`image_generate_v4.py`脚本存在
2. 确认`batch_tasks.json`文件已正确生成
3. 确认输出文件夹已创建

**脚本执行过程**：
- 自动读取指定的`batch_tasks.json`中的任务
- 使用配置的API密钥并发处理
- 将生成的图片保存到指定路径
- 生成HTML画廊展示结果

**执行时间估算**：
- 每张图片约需10-30秒
- 并发处理可大幅缩短总时间（并发数=API Key数量）
- 网络延迟可能影响执行速度

**性能优化**：
- 确保batch_tasks.json中无重复任务
- 使用多个API Key提高并发数
- 合理设置prompt避免重试

### 4. 生成对比HTML

生成并排对比HTML，展示原图和处理后的新图：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>图片边框去除对比</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; background: #f5f5f5; padding: 20px; }
        h1 { text-align: center; margin-bottom: 20px; color: #333; }
        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
            gap: 20px;
        }
        .comparison-item {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .comparison-item h3 {
            margin-bottom: 10px;
            color: #555;
            font-size: 14px;
            word-break: break-all;
        }
        .images {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .image-box {
            text-align: center;
        }
        .image-box img {
            max-width: 100%;
            max-height: 300px;
            object-fit: contain;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .image-box .label {
            margin-top: 8px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>图片边框去除对比</h1>
    <div class="comparison-grid">
        <!-- 动态生成对比项 -->
    </div>
</body>
</html>
```

**HTML生成规则**：
- 每个图片生成一个对比项
- 左侧显示原图，右侧显示处理后图片
- 包含文件名和路径信息
- 支持响应式布局

### 5. 浏览器打开确认

自动在浏览器中打开生成的HTML文件，让用户查看对比效果。

```python
import webbrowser
webbrowser.open(f"file://{os.path.abspath(output_html)}")
```

**浏览器打开失败处理**：
- 如果浏览器打开失败，提供HTML文件路径
- 用户可以手动双击HTML文件打开
- 提示用户检查浏览器设置

## 使用方法

### 方法1：手动执行（推荐）

用户只需提供图片文件夹路径，skill会自动：
1. 扫描所有图片
2. 生成处理任务
3. 执行图片生成
4. 输出到新文件夹`{原文件夹名}_no_border/`
5. 生成对比HTML并打开

### 方法2：使用自动化脚本

使用`scripts/border_remover.py`脚本自动化执行整个流程：

```bash
python "<skill目录>/scripts/border_remover.py" <输入文件夹路径>
```

**脚本功能**：
1. 自动扫描图片文件夹
2. 生成图生图任务配置
3. 提示用户执行图片生成脚本
4. 生成对比HTML
5. 在浏览器中打开对比页面

**使用示例**：
```bash
# 相对路径（推荐）
python ".agents/skills/image-border-remover/scripts/border_remover.py" D:\test_images

# 或绝对路径
python "D:\program\project\front\eys-image\.agents\skills\image-border-remover\scripts\border_remover.py" D:\test_images
```

### 方法3：分步执行

如果需要更灵活的控制，可以分步执行：

1. **扫描图片**：
   ```python
   from scripts.border_remover import scan_images
   images = scan_images("D:\\test_images")
   
   # 如果需要递归扫描子文件夹
   images = scan_images("D:\\test_images", recursive=True)
   ```

2. **生成任务配置**：
   ```python
   from scripts.border_remover import generate_batch_tasks
   batch_tasks_path = generate_batch_tasks(images, "D:\\test_images_no_border")
   ```

3. **执行图片生成**：
   ```bash
   # 推荐：直接传递配置文件路径
   python "<项目根目录>/py/image_generate_v4.py" "<batch_tasks.json路径>"
   ```

4. **生成对比HTML**：
   ```python
   from scripts.border_remover import generate_comparison_html
   html_path = generate_comparison_html(images, "D:\\test_images_no_border")
   ```

5. **打开浏览器**：
   ```python
   from scripts.border_remover import open_html_in_browser
   open_html_in_browser(html_path)
   ```

## 输出结构

```
原文件夹/
├── 图片1.png
├── 图片2.jpg
└── ...
    
原文件夹_no_border/
├── 图片1_no_border.png
├── 图片2_no_border.jpg
├── ...
├── batch_tasks.json
├── image_gallery.html
└── comparison.html
```

**输出文件说明**：
- `*_no_border.png` - 去除边框后的新图片
- `batch_tasks.json` - 图生图任务配置文件
- `image_gallery.html` - 生成脚本自动创建的画廊页面
- `comparison.html` - 原图与新图的对比页面

## 性能优化

### 扫描优化
- **默认不递归**：`scan_images()` 默认只扫描当前文件夹，避免重复扫描
- **递归扫描**：需要扫描子文件夹时，设置 `recursive=True` 参数
- **自动去重**：使用绝对路径去重，避免同一图片被多次处理

### 执行优化
- **并发处理**：`image_generate_v4.py` 支持多API Key并发处理
- **任务去重**：确保batch_tasks.json中无重复任务
- **配置文件传递**：支持直接传递配置文件路径，无需手动复制

### 预期性能
- 单张图片处理时间：10-30秒
- 并发数量：等于API Key数量
- 10张图片预计耗时：1-3分钟（取决于并发数和网络）

## 注意事项

- 新文件夹与原文件夹在同一父目录下
- 对比HTML使用file://协议，直接双击即可打开
- 如果图片较多，处理时间可能较长（每张约10-30秒）
- 确保有足够的API调用额度
- 如果脚本执行失败，检查网络连接和API密钥
- **路径问题**：所有脚本现在使用相对路径，可移植性更好

## 故障排除

### 问题1：脚本执行失败
**可能原因**：
- 网络连接问题
- API密钥无效或额度不足
- 图片文件不存在或格式不支持

**解决方案**：
1. 检查网络连接
2. 验证API密钥有效性
3. 确认图片文件存在且格式正确

### 问题2：生成图片质量不佳
**可能原因**：
- 原图边框过于复杂
- Prompt描述不够精确
- 模型处理能力限制

**解决方案**：
1. 尝试使用更高质量的原图
2. 调整Prompt描述
3. 使用其他图片处理工具辅助

### 问题3：对比HTML无法打开
**可能原因**：
- 浏览器安全设置阻止本地文件访问
- 文件路径包含特殊字符
- HTML文件损坏

**解决方案**：
1. 检查浏览器安全设置
2. 确保文件路径正确
3. 重新生成HTML文件

## 技术细节

### API调用限制
- 每个API密钥支持并发数：1
- 最大并发工作线程数：API密钥数量
- 请求超时时间：90秒
- 下载超时时间：120秒

### 图片处理参数
- 输出分辨率：1024x1024
- 图片格式：PNG
- 压缩质量：无损

### 错误重试机制
- API请求失败：最多重试3次
- 下载失败：最多重试3次
- 指数退避策略：每次重试等待时间翻倍