# -*- coding: utf-8 -*-
"""
对战记录分享面板生成器（鹅鸭记牌器）

功能：
  从 海报/鹅鸭杀分享背景/ 随机选一张底图，在其空白面板区域绘制 13 席位
  对战记录面板（序号 + logo + 名称，支持"随机"暗牌），末尾展示
  "场上没有的牌"（未上场的 2 张），样式对齐小程序记牌器页面。

规则：
  - 鸭阵营 2~3、中立 1~2、鹅阵营补足 13 席；互斥组不同时出现
  - 每席 85% 概率明牌（9~13 张明牌），其余显示"随机"
  - "场上没有的牌"从未上场的角色中随机取 2 张

用法：
  python compose_match_panel.py                # 随机底图生成 1 张
  python compose_match_panel.py -n 4           # 随机底图生成 4 张
  python compose_match_panel.py --all          # 8 张底图各出 1 张（校对版面用）
  python compose_match_panel.py --bg 大留白     # 只用文件名含关键字的底图
"""
import argparse
import json
import os
import random
import sys
import time

from PIL import Image, ImageDraw, ImageFont

BASE = r"D:\program\project\front\eys-image2"
BG_DIR = os.path.join(BASE, "海报", "鹅鸭杀分享背景")
LOGO_DIR = os.path.join(BASE, "chibi_style_v1")
ROLES_JSON = os.path.join(BASE, "config", "roles.json")
OUT_DIR = os.path.join(BASE, "海报", "对战记录分享图")

SEAT_COUNT = 13
EXCLUDED_COUNT = 2
DUCK_RANGE = (2, 3)      # 鸭阵营席位范围
NEUTRAL_RANGE = (1, 2)   # 中立阵营席位范围
MUTUAL_GROUPS = [{"猎鹰", "鹈鹕"}, {"呆呆鸟", "决斗呆呆"}]
# roles.json 展示名 -> 实际 logo 文件（roles.json 里 img 指向的文件不存在时兜底）
LOGO_OVERRIDES = {
    "生存者": "goose_生存主义者.png",
    "牧师": "duck_牧师.png",
}

# 每张底图的空白面板区域 (x0, y0, x1, y1)，均基于实际图片人工标注（比例）
BG_LAYOUTS = {
    "底图_01_幕布偷看猫.png":         {"panel": (0.055, 0.335, 0.945, 0.815)},
    "底图_02_毛线团相框.png":         {"panel": (0.165, 0.250, 0.835, 0.750)},
    "底图_03_侦探猫线索板.png":       {"panel": (0.065, 0.340, 0.935, 0.800)},
    "底图_04_猫爪沙发派对.png":       {"panel": (0.105, 0.195, 0.895, 0.515), "header": False},
    "底图_01_幕布偷看猫_大留白.png":   {"panel": (0.030, 0.200, 0.970, 0.780)},
    "底图_02_爪印细花边_大留白.png":   {"panel": (0.090, 0.090, 0.910, 0.890)},
    "底图_03_侦探猫线索板_大留白.png": {"panel": (0.040, 0.190, 0.960, 0.820)},
    "底图_04_云朵月亮船_大留白.png":   {"panel": (0.040, 0.190, 0.960, 0.750)},
}

# 配色对齐小程序：鹅绿 / 鸭红 / 中立黄
FACTION_STYLE = {
    "goose":   {"strip": (107, 185, 126), "tint": (236, 247, 238), "border": (139, 198, 152)},
    "duck":    {"strip": (240, 138, 142), "tint": (254, 240, 240), "border": (244, 162, 166)},
    "neutral": {"strip": (238, 190, 84),  "tint": (253, 247, 228), "border": (242, 204, 116)},
}
RANDOM_CARD = {"bg": (247, 242, 236), "border": (228, 217, 205), "text": (172, 156, 140)}
INK = (128, 110, 94)      # 序号 / 标签文字
HEADER_COLOR = (146, 108, 76)

_FONT_CACHE = {}


def get_font(size, bold=False):
    key = (int(size), bold)
    if key not in _FONT_CACHE:
        path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, int(size))
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def load_roles():
    """读取 config/roles.json，解析角色名称/阵营/logo 实际路径（按名字去重）。"""
    with open(ROLES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    roles, seen = [], set()
    for r in data["roles"]:
        name = r["name"]
        if name in seen:
            continue
        seen.add(name)
        faction = r["faction"]
        candidates = [
            os.path.basename(r.get("img", "")),
            LOGO_OVERRIDES.get(name, ""),
            "{}_{}.png".format(faction, name),
        ]
        logo = None
        for cand in candidates:
            if not cand:
                continue
            p = os.path.join(LOGO_DIR, faction, cand)
            if os.path.exists(p):
                logo = p
                break
        if logo is None:
            print("[警告] 未找到 logo，该角色不会进入卡池: {}".format(name))
            continue
        roles.append({"name": name, "faction": faction, "logo": logo})
    return roles


def pick_roles(pool, count, taken):
    """从阵营池里抽 count 个，避开互斥组与已选角色。"""
    available = [r for r in pool if r not in taken]
    random.shuffle(available)
    chosen = []
    for role in available:
        if len(chosen) >= count:
            break
        conflict = any(
            role["name"] in g and any(c["name"] in g for c in chosen)
            for g in MUTUAL_GROUPS
        )
        if not conflict:
            chosen.append(role)
    return chosen


def generate_match(roles):
    """按阵营规则抽 13 席 + 场上没有的牌。返回 (seats, excluded)。"""
    duck_n = random.randint(*DUCK_RANGE)
    neutral_n = random.randint(*NEUTRAL_RANGE)
    goose_n = SEAT_COUNT - duck_n - neutral_n

    pools = {f: [r for r in roles if r["faction"] == f] for f in ("duck", "neutral", "goose")}
    ducks = pick_roles(pools["duck"], duck_n, [])
    neutrals = pick_roles(pools["neutral"], neutral_n, ducks)
    geese = pick_roles(pools["goose"], goose_n, ducks + neutrals)

    board = ducks + neutrals + geese
    random.shuffle(board)

    # 9~13 张明牌，其余为"随机"暗牌
    revealed_n = random.randint(SEAT_COUNT - 4, SEAT_COUNT)
    hidden_idx = set(random.sample(range(SEAT_COUNT), SEAT_COUNT - revealed_n))
    seats = [
        {"no": i + 1, "role": None if i in hidden_idx else board[i]}
        for i in range(SEAT_COUNT)
    ]

    # 场上没有的牌：从未上场的角色里抽（避免与明牌重复造成矛盾）
    shown = {s["role"]["name"] for s in seats if s["role"]}
    rest = [r for r in roles if r["name"] not in shown]
    excluded = random.sample(rest, EXCLUDED_COUNT)
    return seats, excluded


def _load_logo(path, size):
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def _draw_role_card(img, draw, x, y, s, seat):
    """席位卡：浅色底 + 阵营描边 + 序号 + logo + 阵营色名称条。"""
    role = seat["role"]
    style = FACTION_STYLE[role["faction"]]
    radius = int(s * 0.14)
    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=style["tint"], outline=style["border"], width=max(2, int(s * 0.03)),
    )
    # 序号
    fs = get_font(s * 0.17, bold=True)
    draw.text((x + s * 0.16, y + s * 0.13), "{}号".format(seat["no"]), fill=INK, font=fs, anchor="mm")
    # logo
    logo_s = int(s * 0.50)
    logo = _load_logo(role["logo"], logo_s)
    img.paste(logo, (int(x + (s - logo_s) / 2), int(y + s * 0.46 - logo_s / 2)), logo)
    # 名称条
    strip_h = s * 0.24
    box = [x + s * 0.06, y + s - strip_h - s * 0.05, x + s - s * 0.06, y + s - s * 0.05]
    draw.rounded_rectangle(box, radius=int(strip_h * 0.45), fill=style["strip"])
    name = role["name"]
    fs_name = min(s * 0.155, (box[2] - box[0]) / (len(name) * 1.15))
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), name,
              fill=(255, 255, 255), font=get_font(fs_name, bold=True), anchor="mm")


def _draw_random_card(draw, x, y, s, no):
    """随机暗牌：米白底 + 灰字"随机"。"""
    radius = int(s * 0.14)
    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=RANDOM_CARD["bg"], outline=RANDOM_CARD["border"], width=max(2, int(s * 0.03)),
    )
    fs = get_font(s * 0.15, bold=True)
    draw.text((x + s * 0.16, y + s * 0.13), "{}号".format(no), fill=INK, font=fs, anchor="mm")
    draw.text((x + s / 2, y + s * 0.52), "随机", fill=RANDOM_CARD["text"],
              font=get_font(s * 0.22, bold=True), anchor="mm")


def _draw_excluded_card(img, draw, x, y, s, role):
    """场上没有的牌：白底小卡 + logo + 名称条。"""
    style = FACTION_STYLE[role["faction"]]
    radius = int(s * 0.16)
    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=(255, 255, 255), outline=style["border"], width=max(2, int(s * 0.035)),
    )
    logo_s = int(s * 0.46)
    logo = _load_logo(role["logo"], logo_s)
    img.paste(logo, (int(x + (s - logo_s) / 2), int(y + s * 0.36 - logo_s / 2)), logo)
    strip_h = s * 0.28
    box = [x + s * 0.08, y + s - strip_h - s * 0.07, x + s - s * 0.08, y + s - s * 0.07]
    draw.rounded_rectangle(box, radius=int(strip_h * 0.45), fill=style["strip"])
    name = role["name"]
    fs_name = min(s * 0.17, (box[2] - box[0]) / (len(name) * 1.15))
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), name,
              fill=(255, 255, 255), font=get_font(fs_name, bold=True), anchor="mm")


def render(bg_path, seats, excluded, out_path):
    img = Image.open(bg_path).convert("RGBA")
    W, H = img.size
    fname = os.path.basename(bg_path)
    lay = BG_LAYOUTS[fname]
    px0, py0, px1, py1 = lay["panel"]
    px0, px1 = px0 * W, px1 * W
    py0, py1 = py0 * H, py1 * H
    pw, ph = px1 - px0, py1 - py0
    draw = ImageDraw.Draw(img)

    pad = pw * 0.014
    gap = pw * 0.012
    header = lay.get("header", True)
    header_h = ph * 0.085 if header else 0
    ex_h = min(ph * 0.14, pw * 0.17)
    grid_h = ph - pad * 2 - header_h - ex_h - gap * 2.4
    card_s = min((pw - pad * 2 - gap * 4) / 5, (grid_h - 2 * gap) / 3)
    # 内容块（标题 + 网格 + 没有的牌）在面板内垂直居中，避免竖长面板底部大片留白
    block_h = (header_h + gap * 0.6 if header else 0) + 3 * card_s + 2 * gap + gap * 1.2 + ex_h
    gy0 = py0 + pad + max(0.0, (ph - pad * 2 - block_h) * 0.45)
    grid_w = 5 * card_s + 4 * gap
    gx0 = px0 + (pw - grid_w) / 2

    if header:
        draw.text((px0 + pad, gy0 + header_h * 0.5), "轮抽身份顺序",
                  fill=HEADER_COLOR, font=get_font(ph * 0.052, bold=True), anchor="lm")
    gy0 += header_h + gap * 0.6

    # 13 席位：前两行各 5 张，最后一行 3 张居中
    for i, seat in enumerate(seats):
        row, col = divmod(i, 5)
        if row == 2:
            x = gx0 + (grid_w - (3 * card_s + 2 * gap)) / 2 + col * (card_s + gap)
        else:
            x = gx0 + col * (card_s + gap)
        y = gy0 + row * (card_s + gap)
        if seat["role"]:
            _draw_role_card(img, draw, x, y, card_s, seat)
        else:
            _draw_random_card(draw, x, y, card_s, seat["no"])

    # 场上没有的牌
    ex_y = gy0 + 3 * card_s + 2 * gap + gap * 1.2
    ex_cy = ex_y + ex_h / 2
    fs_label = get_font(ph * 0.05, bold=True)
    draw.text((px0 + pad, ex_cy), "场上没有的牌", fill=HEADER_COLOR, font=fs_label, anchor="lm")
    label_w = draw.textlength("场上没有的牌", font=fs_label)
    ex_s = min(ex_h, card_s * 0.72)
    ex_x = px0 + pad + label_w + gap * 2
    for j, role in enumerate(excluded):
        _draw_excluded_card(img, draw, ex_x + j * (ex_s + gap * 1.5), ex_cy - ex_s / 2, ex_s, role)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def summarize(seats, excluded):
    parts = []
    for s in seats:
        parts.append("{}{}".format(s["no"], s["role"]["name"] if s["role"] else "随机"))
    return " ".join(parts) + " ｜ 场上没有: " + "、".join(r["name"] for r in excluded)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=1, help="生成张数（随机底图）")
    ap.add_argument("--all", action="store_true", help="每张底图各出 1 张")
    ap.add_argument("--bg", default="", help="底图文件名关键字过滤")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（复现用）")
    ap.add_argument("--out", default=OUT_DIR, help="输出目录")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    roles = load_roles()
    bgs = sorted(f for f in os.listdir(BG_DIR) if f.lower().endswith(".png"))
    if args.bg:
        bgs = [b for b in bgs if args.bg in b]
    unknown = [b for b in bgs if b not in BG_LAYOUTS]
    if unknown:
        print("[警告] 以下底图未标注空白区域，已跳过: {}".format("、".join(unknown)))
        bgs = [b for b in bgs if b in BG_LAYOUTS]
    if not bgs:
        print("没有可用的底图")
        return

    os.makedirs(args.out, exist_ok=True)
    targets = bgs if args.all else [random.choice(bgs) for _ in range(args.n)]
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    for k, bg in enumerate(targets):
        seats, excluded = generate_match(roles)
        stem = os.path.splitext(bg)[0]
        out = os.path.join(args.out, "对战记录_{}_{}.png".format(stem, ts))
        render(os.path.join(BG_DIR, bg), seats, excluded, out)
        print("[{}] {}".format(os.path.basename(out), summarize(seats, excluded)))


if __name__ == "__main__":
    main()
