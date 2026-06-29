#!/usr/bin/env python3
"""
图片边框去除自动化脚本
自动扫描图片文件夹，生成图生图任务，执行图片生成，生成对比HTML
"""

import os
import json
import webbrowser
import sys
import io
from pathlib import Path
from typing import List, Dict

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def scan_images(folder_path: str, recursive: bool = False) -> List[str]:
    """
    扫描指定文件夹下的所有图片文件
    
    Args:
        folder_path: 图片文件夹路径
        recursive: 是否递归扫描子文件夹，默认False
        
    Returns:
        图片文件路径列表（已去重）
    """
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    images = []
    
    if not os.path.exists(folder_path):
        print(f"❌ 文件夹不存在: {folder_path}")
        return images
    
    folder = Path(folder_path)
    
    # 使用set去重
    seen = set()
    
    for ext in supported_formats:
        # 根据recursive参数选择glob或rglob
        pattern_func = folder.rglob if recursive else folder.glob
        
        for img in pattern_func(f"*{ext}"):
            img_str = str(img.resolve())  # 使用绝对路径避免重复
            if img_str not in seen:
                seen.add(img_str)
                images.append(img_str)
        
        for img in pattern_func(f"*{ext.upper()}"):
            img_str = str(img.resolve())
            if img_str not in seen:
                seen.add(img_str)
                images.append(img_str)
    
    print(f"📁 扫描到 {len(images)} 张图片")
    return images


def generate_batch_tasks(images: List[str], output_folder: str) -> str:
    """
    生成图生图任务JSON
    
    Args:
        images: 图片文件路径列表
        output_folder: 输出文件夹路径
        
    Returns:
        生成的batch_tasks.json文件路径
    """
    tasks = []
    
    for image_path in images:
        filename = Path(image_path).stem
        task_id = f"border_removal_{filename}"
        
        task = {
            "task_id": task_id,
            "type": "image_to_image",
            "prompt": "Remove the borders, while keeping everything else unchanged.",
            "local_image_path": os.path.abspath(image_path),
            "size": "1024x1024",
            "output_path": os.path.join(output_folder, f"{filename}_no_border.png")
        }
        tasks.append(task)
    
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
    # 生成batch_tasks.json
    batch_tasks_path = os.path.join(output_folder, "batch_tasks.json")
    with open(batch_tasks_path, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    
    print(f"📝 已生成任务配置: {batch_tasks_path}")
    return batch_tasks_path


def generate_comparison_html(images: List[str], output_folder: str) -> str:
    """
    生成原图与新图的对比HTML
    
    Args:
        images: 原图文件路径列表
        output_folder: 输出文件夹路径
        
    Returns:
        生成的comparison.html文件路径
    """
    # 收集对比项
    comparison_items = []
    
    for image_path in images:
        filename = Path(image_path).stem
        original_path = os.path.abspath(image_path)
        processed_path = os.path.join(output_folder, f"{filename}_no_border.png")
        
        if os.path.exists(processed_path):
            comparison_items.append({
                'original': original_path,
                'processed': os.path.abspath(processed_path),
                'filename': filename
            })
    
    if not comparison_items:
        print("⚠️ 没有找到处理后的图片，无法生成对比HTML")
        return ""
    
    # 生成HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>图片边框去除对比</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, 'Segoe UI', sans-serif; 
            background: #f5f5f5; 
            padding: 20px; 
        }}
        h1 {{ 
            text-align: center; 
            margin-bottom: 20px; 
            color: #333; 
            font-size: 24px;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
            gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .comparison-item {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .comparison-item h3 {{
            margin-bottom: 10px;
            color: #555;
            font-size: 14px;
            word-break: break-all;
        }}
        .images {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }}
        .image-box {{
            flex: 1;
            text-align: center;
        }}
        .image-box img {{
            max-width: 100%;
            max-height: 300px;
            object-fit: contain;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .image-box .label {{
            margin-top: 8px;
            font-size: 12px;
            color: #666;
        }}
        .arrow {{
            flex-shrink: 0;
            font-size: 24px;
            color: #007bff;
            padding: 0 10px;
        }}
    </style>
</head>
<body>
    <h1>图片边框去除对比</h1>
    <div class="comparison-grid">
"""
    
    for item in comparison_items:
        original_uri = Path(item['original']).as_uri()
        processed_uri = Path(item['processed']).as_uri()
        
        html_content += f"""        <div class="comparison-item">
            <h3>{item['filename']}</h3>
            <div class="images">
                <div class="image-box">
                    <img src="{original_uri}" alt="原图">
                    <div class="label">原图</div>
                </div>
                <div class="arrow">→</div>
                <div class="image-box">
                    <img src="{processed_uri}" alt="处理后">
                    <div class="label">去除边框后</div>
                </div>
            </div>
        </div>
"""
    
    html_content += """    </div>
</body>
</html>"""
    
    # 保存HTML文件
    html_path = os.path.join(output_folder, "comparison.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📄 对比HTML已生成: {html_path}")
    return html_path


def open_html_in_browser(html_path: str):
    """
    在浏览器中打开HTML文件
    
    Args:
        html_path: HTML文件路径
    """
    if not html_path or not os.path.exists(html_path):
        print("⚠️ HTML文件不存在，无法打开")
        return
    
    try:
        file_uri = Path(html_path).as_uri()
        webbrowser.open(file_uri)
        print(f"🌐 已在浏览器中打开: {html_path}")
    except Exception as e:
        print(f"❌ 浏览器打开失败: {e}")
        print(f"📄 请手动打开文件: {html_path}")


def main():
    """主函数"""
    print("🚀 图片边框去除自动化工具")
    print("=" * 50)
    
    # 从命令行参数获取输入文件夹路径
    import sys
    if len(sys.argv) < 2:
        print("用法: python border_remover.py <输入文件夹路径>")
        print("示例: python border_remover.py D:\\test_images")
        return
    
    input_folder = sys.argv[1]
    
    # 生成输出文件夹路径
    parent_dir = os.path.dirname(input_folder)
    folder_name = os.path.basename(input_folder)
    output_folder = os.path.join(parent_dir, f"{folder_name}_no_border")
    
    print(f"📂 输入文件夹: {input_folder}")
    print(f"📂 输出文件夹: {output_folder}")
    print()
    
    # 1. 扫描图片
    print("🔍 步骤1: 扫描图片文件...")
    images = scan_images(input_folder)
    
    if not images:
        print("❌ 没有找到图片文件，程序退出")
        return
    
    print()
    
    # 2. 生成任务配置
    print("📝 步骤2: 生成图生图任务配置...")
    batch_tasks_path = generate_batch_tasks(images, output_folder)
    print()
    
    # 3. 提示用户执行脚本
    print("🚀 步骤3: 执行图片生成脚本...")
    # 获取image_generate_v4.py脚本的相对路径
    # 当前脚本: <项目根目录>/.agents/skills/image-border-remover/scripts/border_remover.py
    # 需要上溯5层到项目根目录: scripts -> image-border-remover -> skills -> .agents -> 项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    image_gen_script = os.path.join(project_root, "py", "image_generate_v4.py")
    
    print(f"请手动执行以下命令:")
    print(f'python "{image_gen_script}" -c "{batch_tasks_path}"')
    print()
    print("⚠️ 注意: 执行前请确保batch_tasks.json中的路径正确")
    print()
    
    # 4. 生成对比HTML
    print("📄 步骤4: 生成对比HTML...")
    html_path = generate_comparison_html(images, output_folder)
    print()
    
    # 5. 打开浏览器
    print("🌐 步骤5: 打开浏览器查看对比效果...")
    open_html_in_browser(html_path)
    print()
    
    print("=" * 50)
    print("✅ 完成！")
    print(f"📁 输出文件夹: {output_folder}")
    print(f"📄 对比HTML: {html_path}")


if __name__ == "__main__":
    main()