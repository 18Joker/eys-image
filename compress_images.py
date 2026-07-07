#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PNG 图片压缩脚本
================
用于把对象存储上的大图做「近无损 / 无损」优化，提升用户访问速度。

策略（默认 palette 模式）：
  - 保持 PNG 格式与原始尺寸（不改分辨率，不破坏现有 .png 引用）。
  - 采用「调色板量化 + optimize 重压缩」(TinyPNG 同款思路)：
      将颜色量化到 256 色并保留透明通道，再用 zlib 最高压缩级别重编码。
    对扁平 / 插画风格几乎肉眼无损，体积通常可降 40%~70%。
  - 若设 MODE="lossless"：仅做 optimize=True + compress_level=9 的无损重压，
      质量 100% 不变，但降幅有限（通常 5%~20%）。

用法：
  直接运行：python compress_images.py
  需要调整时修改下方 CONFIG 即可。
"""

import os
from pathlib import Path
from PIL import Image

# ============================== 配置区 ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 每个任务：源文件夹 -> 压缩后新文件夹
#   american_retro_style_v2 -> american_retro_style_v3  (V3)
#   official_v3             -> official_v4              (V4)
TASKS = [
    {"src": "american_retro_style_v2", "dst": "american_retro_style_v3"},
    {"src": "official_v3",             "dst": "official_v4"},
]

# 压缩模式：
#   "palette"   —— 256 色调色板量化（近无损，体积小，默认）
#   "lossless"  —— 纯无损重压（质量不变，降幅有限）
MODE = "palette"

PALETTE_COLORS = 256          # palette 模式下调色板颜色数（最大 256）
DITHER = Image.FLOYDSTEINBERG # 抖动：FLOYDSTEINBERG 平滑渐变 / NONE 纯色块更干净
COMPRESS_LEVEL = 9            # zlib 压缩级别 1~9
ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")
# ================================================================


def compress_image(src_path, dst_path):
    """压缩单张图片，返回 (原始字节数, 压缩后字节数)。"""
    # 提前创建完整目录链路
    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src_path) as im:
        im.load()
        has_alpha = (
            im.mode in ("RGBA", "LA")
            or (im.mode == "P" and "transparency" in im.info)
        )

        if MODE == "palette":
            im = im.convert("RGBA") if has_alpha else im.convert("RGB")
            quantized = im.quantize(
                colors=PALETTE_COLORS, method=Image.FASTOCTREE, dither=DITHER
            )
            quantized.save(
                dst_path,
                format="PNG",
                optimize=True,
                compress_level=COMPRESS_LEVEL,
            )
        else:  # lossless
            im.save(
                dst_path,
                format="PNG",
                optimize=True,
                compress_level=COMPRESS_LEVEL,
            )

    return os.path.getsize(src_path), os.path.getsize(dst_path)


def process_task(task):
    src_root = os.path.join(BASE_DIR, task["src"])
    dst_root = os.path.join(BASE_DIR, task["dst"])
    if not os.path.isdir(src_root):
        print(f"  [跳过] 源文件夹不存在: {src_root}")
        return None

    total_before = total_after = 0
    count = 0
    print(f"\n▶ 处理 {task['src']}  ->  {task['dst']}")
    for root, _, files in os.walk(src_root):
        for fname in files:
            src_path = os.path.join(root, fname)
            rel = os.path.relpath(src_path, src_root)
            dst_path = os.path.join(dst_root, rel)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ALLOWED_EXT:
                # 非图片文件（如 style.md）原样复制，保持目录结构完整
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                with open(src_path, "rb") as f_in, open(dst_path, "wb") as f_out:
                    f_out.write(f_in.read())
                continue
            try:
                before, after = compress_image(src_path, dst_path)
            except Exception as e:
                print(f"  [失败] {rel}: {e}")
                continue
            total_before += before
            total_after += after
            count += 1
            ratio = (1 - after / before) * 100 if before else 0
            print(
                f"  {rel:42s}  {before/1024:8.1f}KB -> {after/1024:8.1f}KB  "
                f"({ratio:+.1f}%)"
            )
    saved = (1 - total_after / total_before) * 100 if total_before else 0
    print(
        f"  ✓ 共 {count} 张,  {total_before/1024/1024:.2f}MB -> "
        f"{total_after/1024/1024:.2f}MB  (节省 {saved:.1f}%)"
    )
    return total_before, total_after, count


def main():
    print(f"压缩模式: {MODE}  |  调色板颜色: {PALETTE_COLORS if MODE=='palette' else 'N/A'}")
    gb = ga = gc = 0
    for task in TASKS:
        r = process_task(task)
        if r:
            gb += r[0]
            ga += r[1]
            gc += r[2]
    print(f"\n========== 总计 ==========")
    print(f"图片: {gc} 张")
    if gb:
        print(
            f"体积: {gb/1024/1024:.2f}MB -> {ga/1024/1024:.2f}MB  "
            f"(节省 {(1-ga/gb)*100:.1f}%)"
        )


if __name__ == "__main__":
    main()
