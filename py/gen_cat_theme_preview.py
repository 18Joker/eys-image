# -*- coding: utf-8 -*-
"""Generate an HTML gallery that references cat_theme original PNGs directly (no processing)."""
import os

BASE = r"D:\program\project\front\eys-image2\原图归档\cat_theme"
OUT = os.path.join(BASE, "图片总览.html")

CAMP_TITLES = {
    "duck": "鸭阵营",
    "goose": "鹅阵营",
    "goose2": "鹅阵营·备选",
    "neutral": "中立阵营",
}

sections = []
total = 0
for camp in ["duck", "goose", "goose2", "neutral"]:
    camp_dir = os.path.join(BASE, camp)
    files = sorted(f for f in os.listdir(camp_dir) if f.lower().endswith(".png"))
    total += len(files)
    cards = []
    for name in files:
        display = os.path.splitext(name)[0].split("_", 1)[-1]
        # URL-encode for src to survive spaces/special chars
        src = f"{camp}/{name}"
        cards.append(
            f'<figure class="card"><img src="{src}" alt="{display}" loading="lazy">'
            f"<figcaption>{display}</figcaption></figure>"
        )
    sections.append(
        f'<section><h2>{CAMP_TITLES[camp]} <span class="count">{len(files)}</span></h2>'
        f'<div class="grid">{"".join(cards)}</div></section>'
    )

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>cat_theme 阵营设计总览</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    background: #14161a;
    color: #e8e8ea;
    padding: 20px 24px 40px;
  }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .sub {{ color: #8a8f98; font-size: 13px; margin-bottom: 24px; }}
  section {{ margin-bottom: 32px; }}
  h2 {{
    font-size: 17px;
    padding-left: 10px;
    border-left: 4px solid #4f8ef7;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  h2 .count {{
    font-size: 12px;
    font-weight: normal;
    color: #aab0bb;
    background: #24272e;
    border-radius: 10px;
    padding: 1px 9px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
  }}
  .card {{
    background: #1d2026;
    border: 1px solid #2a2e36;
    border-radius: 8px;
    overflow: hidden;
    transition: border-color .15s, transform .15s;
  }}
  .card:hover {{ border-color: #4f8ef7; transform: translateY(-2px); }}
  .card img {{
    display: block;
    width: 100%;
    aspect-ratio: 1;
    object-fit: contain;
    background: #262a31;
  }}
  figcaption {{
    text-align: center;
    font-size: 13px;
    padding: 6px 4px 7px;
    color: #d4d7dd;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
</style>
</head>
<body>
<h1>cat_theme 阵营设计总览</h1>
<p class="sub">共 {total} 张 · 直接引用原图（duck / goose / goose2 / neutral）· 无任何加工</p>
{''.join(sections)}
</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"done: {OUT} ({os.path.getsize(OUT)/1024:.0f} KB, {total} images)")
