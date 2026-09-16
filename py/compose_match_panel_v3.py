# -*- coding: utf-8 -*-
"""
对战记录分享面板生成器（v3 · 新版 3:4 全标题底图）
- 底图自带全部标题：顶部"鹅鸭记牌器"、标签条等由底图提供；每张图从 海报/鹅鸭杀分享背景底图-v2/ 随机选一张（坐标登记在 LAYOUTS）
- 本脚本只负责填充：大面板填 13 席位卡（5+5+3 居中）；小面板填 2~3 张"场上没有的牌"卡片
- "我的位置"：橙红底「我」角标 + 橙红序号标识，卡片边框保持真实阵营色（避免与中立金边混淆）
- 头像按非透明包围盒等比缩放居中，不同角色视觉大小一致；序号留内边距、4 字以上角色名自动缩号
- 可选圆体字体：把 TTF 放到 海报/fonts/round.ttf 自动启用（无则用微软雅黑）
- 卡池 logo 来自 原图归档/my_Q版原图/{goose,duck,neutral}/；黑名单角色（猪头）不进场
- 轮抽阵营数量上限：狼≤3、中立≤2、好人≤8 → 13 席下唯一合法组合 8好人/3鸭子/2中立
- "场上没有的牌"2~3 张，按阵营概率加权：九成为鹅营，鸭/中立罕见
- 保留：头像微锐化、官方身份互斥表 10 对角色不共局；合规：无二维码/引流元素
"""
import argparse
import json
import os
import random
import sys
import time

from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = r"D:\program\project\front\eys-image2"
LOGO_DIR = os.path.join(BASE, "原图归档", "my_Q版原图")
ROLES_JSON = os.path.join(BASE, "config", "roles.json")
OUT_DIR = os.path.join(BASE, "海报", "对战记录分享图")
BG_DIR = os.path.join(BASE, "海报", "鹅鸭杀分享背景底图-v2")

SEAT_COUNT = 13
# 「场上没有的牌」张数：2~3 张（最多 3）
EXCLUDED_RANGE = (2, 3)
# 轮抽阵营上限：狼≤3、中立≤2、好人≤8。13 席下鸭+中立必须恰好 5，唯一合法组合 8/3/2
FACTION_COUNTS = {"goose": 8, "duck": 3, "neutral": 2}
# 明置之外的随机（暗置）席位数：通常 2~3 个
HIDDEN_RANGE = (2, 3)
# 官方身份互斥表（同局发牌不能同时出现的角色对，来自鹅鸭杀身份互斥表）：
# 有士兵没有说客 ｜ 有炸弹没有丘比特 ｜ 有变形没有身份窃贼 ｜ 有乌鸦没有渡鸦（乌鸦暂不在卡池，保留防扩展）
# 有猎鹰没有鹈鹕/渡鸦 ｜ 有秃鹫没有鹈鹕/渡鸦 ｜ 有渡鸦没有鹈鹕/猎鹰 ｜ 有鹈鹕没有猎鹰/秃鹫/渡鸦 ｜ 有呆呆鸟没有决斗呆呆
# 注意：猎鹰与秃鹫可以共局，必须按"对"互斥，不能归成一组
MUTUAL_PAIRS = [
    {"士兵", "说客"},
    {"炸弹", "丘比特"},
    {"变形", "身份窃贼"},
    {"乌鸦", "渡鸦"},
    {"猎鹰", "鹈鹕"}, {"猎鹰", "渡鸦"},
    {"秃鹫", "鹈鹕"}, {"秃鹫", "渡鸦"},
    {"渡鸦", "鹈鹕"},
    {"呆呆鸟", "决斗呆呆"},
]
# 黑名单：这些角色不进入卡池（如猪头）
EXCLUDED_ROLES = {"猪头"}
# 「场上没有的牌」阵营概率权重（按比例归一）：九成是鹅营，鸭/中立罕见（放了观感奇怪）
EXCLUDED_FACTION_WEIGHTS = {"goose": 0.90, "duck": 0.05, "neutral": 0.05}

# 面板坐标（归一化，基于 768x1024 目测校准）；脚本只填卡片，标题文字一律由底图自带
LAYOUTS = {
    "底图_3比4_全标题版.png": {
        "panel_a": (0.0260, 0.2656, 0.9740, 0.7051),
        "panel_a_pill_bottom": 0.3223,
        "panel_b": (0.0260, 0.7246, 0.6094, 0.9492),
        "panel_b_pill_bottom": 0.7764,
    },
    "底图_01_复古侦探书房.png": {
        "panel_a": (0.0156, 0.2559, 0.9844, 0.6602),
        "panel_a_pill_bottom": 0.3145,
        "panel_b": (0.0156, 0.6836, 0.6771, 0.8848),
        "panel_b_pill_bottom": 0.7344,
    },
    "底图_02_梦幻星空甜梦.png": {
        "panel_a": (0.0286, 0.2441, 0.9714, 0.7002),
        "panel_a_pill_bottom": 0.2959,
        "panel_b": (0.0286, 0.7197, 0.6094, 0.9521),
        "panel_b_pill_bottom": 0.7686,
    },
    "底图_03_治愈午后咖啡.png": {
        "panel_a": (0.0156, 0.3125, 0.9792, 0.6816),
        "panel_a_pill_bottom": 0.3594,
        "panel_b": (0.0156, 0.7109, 0.6510, 0.9395),
        "panel_b_pill_bottom": 0.7598,
    },
    "底图_04_清新春日露营.png": {
        "panel_a": (0.0417, 0.2656, 0.9596, 0.7080),
        "panel_a_pill_bottom": 0.3145,
        "panel_b": (0.0391, 0.7324, 0.5885, 0.9297),
        "panel_b_pill_bottom": 0.7813,
    },
}

# 配色规范（沿用 v2）
FACTION_STYLE = {
    "goose":   {"strip": (107, 185, 126), "tint": (242, 250, 244), "border": (139, 198, 152)},
    "duck":    {"strip": (240, 138, 142), "tint": (255, 243, 243), "border": (244, 162, 166)},
    "neutral": {"strip": (238, 190, 84),  "tint": (255, 249, 235), "border": (242, 204, 116)},
}
MY_SEAT_STYLE = {"badge_bg": (255, 120, 50)}  # "我"角标底色（边框保持阵营色，避免与中立金边混淆）
RANDOM_CARD = {"bg": (247, 242, 236), "border": (228, 217, 205), "text": (172, 156, 140)}
INK = (128, 110, 94)

_FONT_CACHE = {}
CUSTOM_FONT = os.path.join(BASE, "海报", "fonts", "round.ttf")  # 可选：免费商用圆体 TTF 放这里自动启用


def get_font(size, bold=False):
    key = (int(size), bold)
    if key not in _FONT_CACHE:
        path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
        if os.path.exists(CUSTOM_FONT):
            path = CUSTOM_FONT
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, int(size))
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _find_logo(faction, name, img_basename):
    """在 LOGO_DIR/{faction} 下找 logo，依次尝试：
    1) img 字段精确文件名（如 duck_牧师_v2.png）
    2) img 同名带 _vN 后缀（如 duck_专杀.png → duck_专杀_v3.png）
    3) 角色名精确文件名（如 goose_警长.png）
    4) 角色名带 _vN 后缀（如 neutral_猎鹰 → neutral_猎鹰_v5.png）
    """
    d = os.path.join(LOGO_DIR, faction)
    if not os.path.isdir(d):
        return None
    files = os.listdir(d)
    prefixes = []
    if img_basename:
        stem = os.path.splitext(img_basename)[0]
        prefixes += [(img_basename, True), (stem + "_", False)]
    prefixes += [(f"{faction}_{name}.png", True), (f"{faction}_{name}_", False)]
    for p, exact in prefixes:
        for f in files:
            if f.endswith(".png") and (f == p if exact else f.startswith(p)):
                return os.path.join(d, f)
    return None


def load_roles():
    with open(ROLES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    roles, seen = [], set()
    for r in data["roles"]:
        name = r["name"]
        if name in seen:
            continue
        seen.add(name)
        if name in EXCLUDED_ROLES:
            continue  # 黑名单角色不进入卡池
        logo = _find_logo(r["faction"], name, os.path.basename(r.get("img", "")))
        if logo:
            roles.append({"name": name, "faction": r["faction"], "logo": logo})
        else:
            print("[警告] 未找到 logo，该角色不会进入卡池: {}".format(name))
    return roles


def pick_roles(pool, count, taken):
    available = [r for r in pool if r not in taken]
    random.shuffle(available)
    chosen = []
    for role in available:
        if len(chosen) >= count:
            break
        conflict = any(
            role["name"] in pair and any(c["name"] in pair for c in chosen)
            for pair in MUTUAL_PAIRS
        )
        if not conflict:
            chosen.append(role)
    return chosen


def pick_excluded(rest, count=None):
    """挑"场上没有的牌"：2~3 张，按阵营概率权重抽取（九成鹅营）"""
    if count is None:
        count = random.randint(*EXCLUDED_RANGE)
    chosen, pool = [], list(rest)
    for _ in range(count):
        if not pool:
            break
        factions = sorted({r["faction"] for r in pool})
        weights = [EXCLUDED_FACTION_WEIGHTS.get(f, 0.0) for f in factions]
        if sum(weights) <= 0:
            pick = random.choice(pool)
        else:
            f = random.choices(factions, weights=weights, k=1)[0]
            pick = random.choice([r for r in pool if r["faction"] == f])
        chosen.append(pick)
        pool.remove(pick)
    return chosen


def generate_match(roles, my_seat_no=None):
    duck_n = FACTION_COUNTS["duck"]
    neutral_n = FACTION_COUNTS["neutral"]
    goose_n = FACTION_COUNTS["goose"]
    assert duck_n + neutral_n + goose_n == SEAT_COUNT, "阵营数量之和必须等于席位数"

    pools = {f: [r for r in roles if r["faction"] == f] for f in ("duck", "neutral", "goose")}
    ducks = pick_roles(pools["duck"], duck_n, [])
    neutrals = pick_roles(pools["neutral"], neutral_n, ducks)
    geese = pick_roles(pools["goose"], goose_n, ducks + neutrals)

    board = ducks + neutrals + geese
    random.shuffle(board)

    if my_seat_no is None or not (1 <= my_seat_no <= SEAT_COUNT):
        my_seat_no = random.randint(1, SEAT_COUNT)

    # 随机（暗置）席位：通常 2~3 个
    hidden_n = random.randint(*HIDDEN_RANGE)
    hidden_idx = set(random.sample(range(SEAT_COUNT), hidden_n))
    if (my_seat_no - 1) in hidden_idx and random.random() < 0.7:
        hidden_idx.remove(my_seat_no - 1)

    seats = [
        {
            "no": i + 1,
            "role": None if i in hidden_idx else board[i],
            "is_me": (i + 1 == my_seat_no),
        }
        for i in range(SEAT_COUNT)
    ]

    # 未入场牌从"未发牌"的角色中挑（含暗置席在内的 13 张已发牌都不能再出现）
    dealt = {r["name"] for r in board}
    rest = [r for r in roles if r["name"] not in dealt]
    excluded = pick_excluded(rest)

    stats = {"duck": duck_n, "neutral": neutral_n, "goose": goose_n}
    return seats, excluded, stats, my_seat_no


def _load_logo(path, box):
    """加载头像：裁剪到非透明包围盒后等比缩放进 box（最长边贴边），再微锐化——保证不同角色视觉大小一致"""
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    w, h = img.size
    scale = box / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = img.resize((nw, nh), Image.LANCZOS)
    return resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=2))


def _draw_role_card(img, draw, x, y, s, seat):
    role = seat["role"]
    style = FACTION_STYLE[role["faction"]]
    is_me = seat["is_me"]
    radius = int(s * 0.14)

    # 边框/底色始终用真实阵营色；"我"只靠右上角角标 + 橙红序号标识
    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=style["tint"], outline=style["border"], width=max(2, int(s * 0.028)),
    )

    # 序号：左/上各留出约 5px 内边距，避免贴边压迫感
    fs = get_font(s * 0.17, bold=True)
    no_color = (230, 90, 40) if is_me else INK
    draw.text((x + s * 0.21, y + s * 0.17), f"{seat['no']}号", fill=no_color, font=fs, anchor="mm")

    if is_me:
        badge_w, badge_h = s * 0.32, s * 0.18
        bx1 = x + s - max(2, int(s * 0.028))
        bx0 = bx1 - badge_w
        by0 = y + max(2, int(s * 0.028))
        by1 = by0 + badge_h
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(badge_h * 0.4), fill=MY_SEAT_STYLE["badge_bg"])
        draw.text(((bx0 + bx1) / 2, (by0 + by1) / 2 + 1), "我", fill=(255, 255, 255),
                  font=get_font(s * 0.12, bold=True), anchor="mm")

    logo_s = int(s * 0.52)
    logo = _load_logo(role["logo"], logo_s)
    lw, lh = logo.size
    img.paste(logo, (int(x + (s - lw) / 2), int(y + s * 0.45 - lh / 2)), logo)

    strip_h = s * 0.23
    box = [x + s * 0.06, y + s - strip_h - s * 0.05, x + s - s * 0.06, y + s - s * 0.05]
    draw.rounded_rectangle(box, radius=int(strip_h * 0.45), fill=style["strip"])
    name = role["name"]
    fs_name = min(s * 0.155, (box[2] - box[0]) / (len(name) * 1.12))
    if len(name) >= 4:
        fs_name = min(fs_name, s * 0.135)  # 4 字以上自动缩号，左右留呼吸空间
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), name,
              fill=(255, 255, 255), font=get_font(fs_name, bold=True), anchor="mm")


def _draw_random_card(draw, x, y, s, seat):
    is_me = seat["is_me"]
    radius = int(s * 0.14)

    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=RANDOM_CARD["bg"], outline=RANDOM_CARD["border"], width=max(2, int(s * 0.028)),
    )
    fs = get_font(s * 0.15, bold=True)
    no_color = (230, 90, 40) if is_me else INK
    draw.text((x + s * 0.21, y + s * 0.17), f"{seat['no']}号", fill=no_color, font=fs, anchor="mm")

    if is_me:
        badge_w, badge_h = s * 0.32, s * 0.18
        bx1 = x + s - max(2, int(s * 0.028))
        bx0 = bx1 - badge_w
        by0 = y + max(2, int(s * 0.028))
        by1 = by0 + badge_h
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(badge_h * 0.4), fill=MY_SEAT_STYLE["badge_bg"])
        draw.text(((bx0 + bx1) / 2, (by0 + by1) / 2 + 1), "我", fill=(255, 255, 255),
                  font=get_font(s * 0.12, bold=True), anchor="mm")

    draw.text((x + s / 2, y + s * 0.52), "随机", fill=RANDOM_CARD["text"],
              font=get_font(s * 0.22, bold=True), anchor="mm")


def _draw_excluded_card(img, draw, x, y, s, role):
    style = FACTION_STYLE[role["faction"]]
    radius = int(s * 0.16)
    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=(255, 255, 255), outline=style["border"], width=max(2, int(s * 0.035)),
    )
    logo_s = int(s * 0.54)
    logo = _load_logo(role["logo"], logo_s)
    lw, lh = logo.size
    img.paste(logo, (int(x + (s - lw) / 2), int(y + s * 0.38 - lh / 2)), logo)
    strip_h = s * 0.28
    box = [x + s * 0.08, y + s - strip_h - s * 0.07, x + s - s * 0.08, y + s - s * 0.07]
    draw.rounded_rectangle(box, radius=int(strip_h * 0.45), fill=style["strip"])
    name = role["name"]
    fs_name = min(s * 0.17, (box[2] - box[0]) / (len(name) * 1.15))
    if len(name) >= 4:
        fs_name = min(fs_name, s * 0.15)
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), name,
              fill=(255, 255, 255), font=get_font(fs_name, bold=True), anchor="mm")


def render(bg_path, seats, excluded, out_path):
    img = Image.open(bg_path).convert("RGBA")
    W, H = img.size
    lay = LAYOUTS[os.path.basename(bg_path)]
    draw = ImageDraw.Draw(img)

    # ---- 面板 A："轮抽身份顺序" 13 席位 ----
    ax0, ay0, ax1, ay1 = (lay["panel_a"][0] * W, lay["panel_a"][1] * H,
                          lay["panel_a"][2] * W, lay["panel_a"][3] * H)
    pw, ph = ax1 - ax0, ay1 - ay0
    pad = pw * 0.033
    gap_x = pw * 0.019
    gap_y = pw * 0.028  # 行距大于列距，3 行卡片在面板内分布更饱满

    # 卡片尺寸：内容区 = 标签条底 → 面板底，宽高双向约束后网格整体居中
    content_top = lay["panel_a_pill_bottom"] * H + ph * 0.02
    avail_h = ay1 - pad - content_top
    card_w = (pw - pad * 2 - gap_x * 4) / 5
    card_h = (avail_h - gap_y * 2) / 3
    s = min(card_w, card_h)
    grid_w = 5 * s + 4 * gap_x
    grid_h = 3 * s + 2 * gap_y
    gx0 = ax0 + (pw - grid_w) / 2
    gy0 = content_top + max(0.0, (avail_h - grid_h) / 2)

    for i, seat in enumerate(seats):
        row, col = divmod(i, 5)
        if row == 2:
            x = gx0 + (grid_w - (3 * s + 2 * gap_x)) / 2 + col * (s + gap_x)
        else:
            x = gx0 + col * (s + gap_x)
        y = gy0 + row * (s + gap_y)
        if seat["role"]:
            _draw_role_card(img, draw, x, y, s, seat)
        else:
            _draw_random_card(draw, x, y, s, seat)

    # ---- 面板 B："场上没有的牌" 2 张 ----
    bx0, by0, bx1, by1 = (lay["panel_b"][0] * W, lay["panel_b"][1] * H,
                          lay["panel_b"][2] * W, lay["panel_b"][3] * H)
    bpw, bph = bx1 - bx0, by1 - by0
    content_top_b = lay["panel_b_pill_bottom"] * H + bph * 0.03
    avail_h_b = by1 - bph * 0.06 - content_top_b
    # 2~3 张卡片自适应：数量决定宽度约束，整体水平居中
    n_ex = max(1, len(excluded))
    ex_s = min(avail_h_b, (bpw - pad * 2 - gap_x * 1.5 * (n_ex - 1)) / n_ex)
    block_w = n_ex * ex_s + gap_x * 1.5 * (n_ex - 1)
    ex_x = bx0 + (bpw - block_w) / 2
    ex_y = content_top_b + max(0.0, (avail_h_b - ex_s) / 2)
    for j, role in enumerate(excluded):
        _draw_excluded_card(img, draw, ex_x + j * (ex_s + gap_x * 1.5), ex_y, ex_s, role)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def summarize(seats, excluded, my_seat):
    parts = []
    for s in seats:
        name = s["role"]["name"] if s["role"] else "随机"
        prefix = f"[{s['no']}我]" if s["is_me"] else f"{s['no']}"
        parts.append(f"{prefix}{name}")
    return " ".join(parts) + " ｜ 未入场: " + "、".join(r["name"] for r in excluded)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="对战记录分享图 v3（3:4 全标题底图）")
    ap.add_argument("-n", type=int, default=1, help="生成张数（每张随机选一张底图）")
    ap.add_argument("--me", type=int, default=None, help="指定我的席位 (1~13)，默认随机")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（复现用）")
    ap.add_argument("--bg", default="", help="指定底图（完整路径或文件名关键字），默认每张图随机选用底图")
    ap.add_argument("--out", default=OUT_DIR, help="输出目录")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    bg_path_fixed = None
    if args.bg:
        if os.path.exists(args.bg):
            bg_path_fixed = args.bg
        else:
            matches = [f for f in os.listdir(BG_DIR) if args.bg in f and f.lower().endswith(".png")]
            if not matches:
                print(f"[错误] 底图文件夹中没有匹配 {args.bg} 的文件")
                return
            bg_path_fixed = os.path.join(BG_DIR, matches[0])
        if os.path.basename(bg_path_fixed) not in LAYOUTS:
            print(f"[错误] 底图 {os.path.basename(bg_path_fixed)} 未在 LAYOUTS 中登记面板坐标，请先测量并补充")
            return

    pool = [f for f in os.listdir(BG_DIR) if f.lower().endswith(".png") and f in LAYOUTS]
    if not pool:
        print(f"[错误] {BG_DIR} 中没有已登记坐标的底图")
        return

    roles = load_roles()
    os.makedirs(args.out, exist_ok=True)
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    for k in range(args.n):
        bg_path = bg_path_fixed or os.path.join(BG_DIR, random.choice(pool))
        bg_name = os.path.basename(bg_path)
        seats, excluded, stats, my_seat = generate_match(roles, my_seat_no=args.me)
        stem = os.path.splitext(bg_name)[0]
        out = os.path.join(args.out, f"对战记录_{stem}_{ts}_{k + 1}.png")
        render(bg_path, seats, excluded, out)
        print(f"[{os.path.basename(out)}] {summarize(seats, excluded, my_seat)}"
              f" ｜ 好人{stats['goose']} 鸭子{stats['duck']} 中立{stats['neutral']}")


if __name__ == "__main__":
    main()
