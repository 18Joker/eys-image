# -*- coding: utf-8 -*-
"""对 official_camps_v3 全部 PNG 做客观色彩/构图测量：
- 画布尺寸、主体外接框占比
- 背景色（四角众数）
- 剔除背景后的 Top10 固有色（hex + 占主体像素比）
- 去背景后的独立色数（判断平涂矢量 vs 噪点纹理）
- 近黑描边占比（r,g,b 均 < 48）
"""
import os, json, sys
sys.path.insert(0, r'C:/Users/hekezhuan/.workbuddy/binaries/python/envs/default/site-packages')
from PIL import Image
from collections import Counter

ROOT = r'C:/program1/project/Front/eys-image/official_camps_v3'
OUT  = r'C:/program1/project/Front/eys-image/美术特征档案/color_stats.json'

def close(c1, c2, tol=14):
    return abs(c1[0]-c2[0])<=tol and abs(c1[1]-c2[1])<=tol and abs(c1[2]-c2[2])<=tol

def analyze(path):
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    px = im.load()
    corners = [px[0,0], px[w-1,0], px[0,h-1], px[w-1,h-1]]
    bg = Counter(corners).most_common(1)[0][0][:3]

    cnt = Counter()
    total_sub = 0
    black_px = 0
    min_x, min_y, max_x, max_y = w, h, -1, -1
    step = 1
    data = im.getdata()
    idx = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = data[idx]; idx += 1
            if a < 128:
                continue
            if close((r,g,b), bg):
                continue
            total_sub += 1
            cnt[(r,g,b)] += 1
            if r < 48 and g < 48 and b < 48:
                black_px += 1
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y

    if total_sub == 0:
        return None
    top = cnt.most_common(10)
    bw = (max_x-min_x+1)/w; bh = (max_y-min_y+1)/h
    return {
        'size': [w, h],
        'bg_hex': '#%02X%02X%02X' % bg,
        'subject_ratio': round(bw*bh, 3),
        'unique_colors': len(cnt),
        'black_pct': round(black_px/total_sub*100, 1),
        'top_colors': [{'hex': '#%02X%02X%02X' % c, 'pct': round(n/total_sub*100, 1)} for c, n in top],
    }

result = {}
for camp in ['goose', 'duck', 'neutral']:
    d = os.path.join(ROOT, camp)
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith('.png'):
            continue
        key = f'{camp}/{f}'
        try:
            result[key] = analyze(os.path.join(d, f))
        except Exception as e:
            result[key] = {'error': str(e)}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as fp:
    json.dump(result, fp, ensure_ascii=False, indent=1)

# 紧凑摘要输出
for k, v in result.items():
    if v is None or 'error' in v:
        print(k, 'ERROR', v); continue
    tops = ' '.join(f"{c['hex']}:{c['pct']}" for c in v['top_colors'][:6])
    print(f"{k} | {v['size'][0]}x{v['size'][1]} | bg={v['bg_hex']} | subj={v['subject_ratio']} | uniq={v['unique_colors']} | blk={v['black_pct']}% | {tops}")
