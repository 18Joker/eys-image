#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片就地压缩脚本
================
指定一个目标文件夹，递归遍历其中的图片文件，
把大小超过阈值的图片压缩后【直接覆盖】原文件（不新建文件夹、不改文件名）。

压缩策略（沿用 compress_images.py 思路）：
  - palette 模式：256 色调色板量化 + zlib 最高压缩级别（近无损，体积降幅大，默认）
  - lossless 模式：仅 optimize + compress_level=9 无损重压（质量不变，降幅有限）
  - 保留原图格式（png/jpg/jpeg/webp/bmp/tiff），不改扩展名。

安全：
  - 先写入同目录临时文件，成功后再 os.replace 覆盖，避免压缩中途失败导致原图损坏。
  - 仅当压缩后体积确实更小才覆盖；若压缩后反而变大则保留原文件。

用法：
  # 命令行指定目录（优先级最高）
  python compress_inplace.py <目标文件夹> [--threshold 800] [--mode palette]

  # 或不传参，使用下方 CONFIG 中固定的 TARGET_DIR 运行
  python compress_inplace.py
"""

import argparse
import os
import tempfile
from pathlib import Path

from PIL import Image

# ============================== 配置区 ==============================
# 不传命令行参数时使用此目录（留空字符串 "" 则必须命令行传入）
TARGET_DIR = r"D:\program\project\front\eys-image\american_retro_style_v3"

# 大小阈值（KB）：仅压缩大于此值的文件。默认 800KB
THRESHOLD_KB = 800

# 压缩模式：
#   "palette"   —— 256 色调色板量化（近无损，体积小，默认）
#   "lossless"  —— 纯无损重压（质量不变，降幅有限）
MODE = "palette"

PALETTE_COLORS = 256          # palette 模式下调色板颜色数（最大 256）
DITHER = Image.FLOYDSTEINBERG # 抖动：FLOYDSTEINBERG 平滑渐变 / NONE 纯色块更干净
COMPRESS_LEVEL = 9            # zlib 压缩级别 1~9
JPEG_QUALITY = 85             # lossless/jpeg 保存质量
ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")
# ================================================================


def compress_to_bytes(src_path, mode):
    """读取图片并压缩，返回压缩后的字节数据；失败抛异常。"""
    with Image.open(src_path) as im:
        im.load()
        fmt = (im.format or "PNG").upper()
        has_alpha = (
            im.mode in ("RGBA", "LA")
            or (im.mode == "P" and "transparency" in im.info)
        )

        if mode == "palette" and fmt in ("PNG", "WEBP"):
            im = im.convert("RGBA") if has_alpha else im.convert("RGB")
            out = im.quantize(
                colors=PALETTE_COLORS, method=Image.FASTOCTREE, dither=DITHER
            )
            save_kwargs = {"optimize": True, "compress_level": COMPRESS_LEVEL}
            save_fmt = "PNG" if fmt == "PNG" else "WEBP"
        elif fmt in ("JPEG",):
            out = im.convert("RGB")
            save_kwargs = {"quality": JPEG_QUALITY, "optimize": True}
            save_fmt = "JPEG"
        else:  # 其余格式走无损重压
            out = im
            save_kwargs = {"optimize": True, "compress_level": COMPRESS_LEVEL}
            save_fmt = fmt

    import io
    buf = io.BytesIO()
    out.save(buf, format=save_fmt, **save_kwargs)
    return buf.getvalue()


def compress_file(src_path, mode, threshold):
    """压缩单个文件并就地覆盖。返回 (原字节数, 压缩后字节数) 或 None（无需/未覆盖）。"""
    before = os.path.getsize(src_path)
    if before <= threshold:
        return None  # 未超过阈值，跳过

    data = compress_to_bytes(src_path, mode)
    after = len(data)
    if after >= before:
        return None  # 压缩后未变小，保留原文件

    # 先写临时文件，再原子替换，避免损坏原图
    d = os.path.dirname(src_path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, src_path)  # 原子覆盖
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return before, after


def process_dir(target_dir, mode, threshold):
    if not os.path.isdir(target_dir):
        print(f"[错误] 目标文件夹不存在: {target_dir}")
        return

    total_before = total_after = 0
    count = skipped = 0
    print(f"\n▶ 目标文件夹: {target_dir}")
    print(f"  阈值: >{threshold/1024:.0f}KB  |  模式: {mode}")
    for root, _, files in os.walk(target_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ALLOWED_EXT:
                continue
            src_path = os.path.join(root, fname)
            try:
                r = compress_file(src_path, mode, threshold)
            except Exception as e:
                print(f"  [失败] {src_path}: {e}")
                continue
            if r is None:
                skipped += 1
                continue
            before, after = r
            total_before += before
            total_after += after
            count += 1
            ratio = (1 - after / before) * 100
            print(
                f"  {src_path}: {before/1024:8.1f}KB -> {after/1024:8.1f}KB  "
                f"({ratio:+.1f}%)"
            )

    saved = (1 - total_after / total_before) * 100 if total_before else 0
    print(f"\n========== 完成 ==========")
    print(f"已压缩: {count} 张  |  跳过(未超阈值/压缩无效): {skipped} 张")
    if total_before:
        print(
            f"体积: {total_before/1024/1024:.2f}MB -> "
            f"{total_after/1024/1024:.2f}MB  (节省 {saved:.1f}%)"
        )


def main():
    parser = argparse.ArgumentParser(description="图片就地压缩（覆盖原文件）")
    parser.add_argument("target", nargs="?", default="", help="目标文件夹路径")
    parser.add_argument(
        "--threshold", type=int, default=THRESHOLD_KB, help="大小阈值(KB)，默认 800"
    )
    parser.add_argument(
        "--mode", choices=["palette", "lossless"], default=MODE, help="压缩模式"
    )
    args = parser.parse_args()

    target = args.target or TARGET_DIR
    if not target:
        print("[错误] 未指定目标文件夹。请命令行传入路径，或在 CONFIG 中设置 TARGET_DIR。")
        return

    threshold = args.threshold * 1024
    process_dir(target, args.mode, threshold)


if __name__ == "__main__":
    main()
