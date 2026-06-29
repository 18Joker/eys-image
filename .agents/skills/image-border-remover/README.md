# Image Border Remover Skill

去除图片边框的自动化工具，支持批量处理并生成对比预览。

## 功能特性

- ✅ 自动扫描指定文件夹下的所有图片
- ✅ 生成图生图任务配置
- ✅ 执行图片生成脚本
- ✅ 输出到新文件夹（原文件夹名 `_no_border`）
- ✅ 生成原图与新图的对比HTML页面
- ✅ 自动在浏览器中打开对比页面

## 支持的图片格式

- PNG
- JPG/JPEG
- WebP
- BMP

## 使用方法

### 方法1：直接使用Skill

在对话中提供图片文件夹路径，skill会自动执行整个流程：

```
帮我处理 D:\test_images 文件夹下的图片，去除所有图片的边框，然后生成对比页面让我看看效果
```

### 方法2：使用自动化脚本

```bash
python "<skill目录>/scripts/border_remover.py" <输入文件夹路径>
```

**示例**：
```bash
# 相对路径（推荐）
python ".agents/skills/image-border-remover/scripts/border_remover.py" D:\test_images

# 或绝对路径
python "D:\program\project\front\eys-image\.agents\skills\image-border-remover\scripts\border_remover.py" D:\test_images
```

### 方法3：分步执行

```python
# 1. 扫描图片（默认只扫描当前文件夹，不递归）
from scripts.border_remover import scan_images
images = scan_images("D:\\test_images")

# 如果需要递归扫描子文件夹，设置 recursive=True
images = scan_images("D:\\test_images", recursive=True)

# 2. 生成任务配置
from scripts.border_remover import generate_batch_tasks
batch_tasks_path = generate_batch_tasks(images, "D:\\test_images_no_border")

# 3. 执行图片生成（传递配置文件路径）
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
image_gen_script = os.path.join(script_dir, "..", "..", "..", "py", "image_generate_v4.py")
os.system(f'python "{image_gen_script}" "{batch_tasks_path}"')

# 4. 生成对比HTML
from scripts.border_remover import generate_comparison_html
html_path = generate_comparison_html(images, "D:\\test_images_no_border")

# 5. 打开浏览器
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

## 工作原理

1. **扫描图片**：识别指定文件夹下的所有支持格式的图片
2. **生成任务**：为每张图片创建图生图任务，使用固定prompt去除边框
3. **执行生成**：调用`image_generate_v4.py`脚本执行批量任务
4. **生成对比**：创建并排对比HTML，展示原图和处理后图片
5. **打开预览**：在浏览器中自动打开对比页面

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

## 文件结构

```
image-border-remover/
├── SKILL.md                    # Skill主文件
├── README.md                   # 说明文档
├── evals/
│   └── evals.json              # 测试用例配置
└── scripts/
    └── border_remover.py       # 自动化脚本
```

## 更新日志

### v1.1.0
- **性能优化**：扫描函数默认不递归，避免重复扫描
- **去重机制**：使用绝对路径去重，确保无重复任务
- **路径优化**：移除硬编码绝对路径，使用相对路径
- **配置传递**：支持直接传递配置文件路径给image_generate_v4.py
- **文档更新**：完善使用说明和性能优化指南

### v1.0.0
- 初始版本
- 支持批量图片边框去除
- 生成对比HTML页面
- 自动化脚本支持

## 许可证

MIT License