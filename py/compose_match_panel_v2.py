# -*- coding: utf-8 -*-
"""
对战记录分享面板生成器（v2 修订版，基于云端 Gemini 优化稿修复）
- 保留 v2 新特性：高亮"我的位置"（金边+「我」徽标）、标题右侧阵营统计、头像微锐化
- 修复：卡片尺寸恢复高度约束 + 内容块垂直居中，杜绝溢出空白面板
- 修复：头像 0.58s→0.52s，不再压住名称条；"盲抽"改回与小程序一致的"随机"
- 合规：二维码推广区默认关闭（--promo 且存在 海报/qrcode.png 才绘制），无引流元素
"""
import argparse
import json
import os
import random
import sys
import time

from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = r"D:\program\project\front\eys-image2"
BG_DIR = os.path.join(BASE, "海报", "鹅鸭杀分享背景")
LOGO_DIR = os.path.join(BASE, "chibi_style_v1")
ROLES_JSON = os.path.join(BASE, "config", "roles.json")
OUT_DIR = os.path.join(BASE, "海报", "对战记录分享图")
QR_CODE_PATH = os.path.join(BASE, "海报", "qrcode.png")  # 小程序码（若无则自动画占位）

SEAT_COUNT = 13
EXCLUDED_COUNT = 2
DUCK_RANGE = (2, 3)
NEUTRAL_RANGE = (1, 2)
MUTUAL_GROUPS = [{"猎鹰", "鹈鹕"}, {"呆呆鸟", "决斗呆呆"}]
LOGO_OVERRIDES = {
    "生存者": "goose_生存主义者.png",
    "牧师": "duck_牧师.png",
}

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

# 配色规范
FACTION_STYLE = {
    "goose":   {"strip": (107, 185, 126), "tint": (242, 250, 244), "border": (139, 198, 152)},
    "duck":    {"strip": (240, 138, 142), "tint": (255, 243, 243), "border": (244, 162, 166)},
    "neutral": {"strip": (238, 190, 84),  "tint": (255, 249, 235), "border": (242, 204, 116)},
}
# 我的席位高亮样式（金琥珀色）
MY_SEAT_STYLE = {
    "border": (255, 160, 30),
    "badge_bg": (255, 120, 50),
    "tint": (255, 248, 235)
}

RANDOM_CARD = {"bg": (247, 242, 236), "border": (228, 217, 205), "text": (172, 156, 140)}
INK = (128, 110, 94)
HEADER_COLOR = (146, 108, 76)
SUB_COLOR = (175, 150, 130)

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
            f"{faction}_{name}.png",
        ]
        logo = None
        for cand in candidates:
            if not cand:
                continue
            p = os.path.join(LOGO_DIR, faction, cand)
            if os.path.exists(p):
                logo = p
                break
        if logo:
            roles.append({"name": name, "faction": faction, "logo": logo})
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
            role["name"] in g and any(c["name"] in g for c in chosen)
            for g in MUTUAL_GROUPS
        )
        if not conflict:
            chosen.append(role)
    return chosen


def generate_match(roles, my_seat_no=None):
    duck_n = random.randint(*DUCK_RANGE)
    neutral_n = random.randint(*NEUTRAL_RANGE)
    goose_n = SEAT_COUNT - duck_n - neutral_n

    pools = {f: [r for r in roles if r["faction"] == f] for f in ("duck", "neutral", "goose")}
    ducks = pick_roles(pools["duck"], duck_n, [])
    neutrals = pick_roles(pools["neutral"], neutral_n, ducks)
    geese = pick_roles(pools["goose"], goose_n, ducks + neutrals)

    board = ducks + neutrals + geese
    random.shuffle(board)

    # 随机指定我的位置（若未指定）
    if my_seat_no is None or not (1 <= my_seat_no <= SEAT_COUNT):
        my_seat_no = random.randint(1, SEAT_COUNT)

    revealed_n = random.randint(SEAT_COUNT - 3, SEAT_COUNT)
    hidden_idx = set(random.sample(range(SEAT_COUNT), SEAT_COUNT - revealed_n))
    # 保证自己的席位大概率是明牌
    if (my_seat_no - 1) in hidden_idx and random.random() < 0.7:
        hidden_idx.remove(my_seat_no - 1)

    seats = [
        {
            "no": i + 1,
            "role": None if i in hidden_idx else board[i],
            "is_me": (i + 1 == my_seat_no)
        }
        for i in range(SEAT_COUNT)
    ]

    shown = {s["role"]["name"] for s in seats if s["role"]}
    rest = [r for r in roles if r["name"] not in shown]
    excluded = random.sample(rest, EXCLUDED_COUNT)

    stats = {"duck": duck_n, "neutral": neutral_n, "goose": goose_n}
    return seats, excluded, stats, my_seat_no


def _load_logo(path, size):
    """加载头像并进行高画质微锐化，消除模糊"""
    img = Image.open(path).convert("RGBA")
    # 高清平滑缩放
    resized = img.resize((size, size), Image.LANCZOS)
    # 微锐化滤镜，突出手绘边缘线
    sharpened = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=2))
    return sharpened


def _draw_role_card(img, draw, x, y, s, seat):
    role = seat["role"]
    style = FACTION_STYLE[role["faction"]]
    is_me = seat["is_me"]
    radius = int(s * 0.14)

    # 底色与边框（如果是自己，强化边框）
    bg_color = MY_SEAT_STYLE["tint"] if is_me else style["tint"]
    border_color = MY_SEAT_STYLE["border"] if is_me else style["border"]
    border_width = max(3, int(s * 0.045)) if is_me else max(2, int(s * 0.028))

    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=bg_color, outline=border_color, width=border_width,
    )

    # 序号
    fs = get_font(s * 0.17, bold=True)
    no_color = (230, 90, 40) if is_me else INK
    draw.text((x + s * 0.16, y + s * 0.13), f"{seat['no']}号", fill=no_color, font=fs, anchor="mm")

    # 如果是我的位置：绘制右上角「我」徽标
    if is_me:
        badge_w, badge_h = s * 0.32, s * 0.18
        bx1 = x + s - border_width
        bx0 = bx1 - badge_w
        by0 = y + border_width
        by1 = by0 + badge_h
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(badge_h * 0.4), fill=MY_SEAT_STYLE["badge_bg"])
        draw.text(((bx0 + bx1)/2, (by0 + by1)/2 + 1), "我", fill=(255, 255, 255),
                  font=get_font(s * 0.12, bold=True), anchor="mm")

    # 头像：0.52s，底部不超过名称条顶边
    logo_s = int(s * 0.52)
    logo = _load_logo(role["logo"], logo_s)
    img.paste(logo, (int(x + (s - logo_s) / 2), int(y + s * 0.45 - logo_s / 2)), logo)

    # 底部名称条
    strip_h = s * 0.23
    box = [x + s * 0.06, y + s - strip_h - s * 0.05, x + s - s * 0.06, y + s - s * 0.05]
    draw.rounded_rectangle(box, radius=int(strip_h * 0.45), fill=style["strip"])
    name = role["name"]
    fs_name = min(s * 0.155, (box[2] - box[0]) / (len(name) * 1.12))
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), name,
              fill=(255, 255, 255), font=get_font(fs_name, bold=True), anchor="mm")


def _draw_random_card(draw, x, y, s, seat):
    is_me = seat["is_me"]
    radius = int(s * 0.14)
    border_color = MY_SEAT_STYLE["border"] if is_me else RANDOM_CARD["border"]
    border_width = max(3, int(s * 0.045)) if is_me else max(2, int(s * 0.028))

    draw.rounded_rectangle(
        [x, y, x + s, y + s], radius=radius,
        fill=RANDOM_CARD["bg"], outline=border_color, width=border_width,
    )
    fs = get_font(s * 0.15, bold=True)
    draw.text((x + s * 0.16, y + s * 0.13), f"{seat['no']}号", fill=INK, font=fs, anchor="mm")
    
    if is_me:
        badge_w, badge_h = s * 0.32, s * 0.18
        bx1 = x + s - border_width
        bx0 = bx1 - badge_w
        by0 = y + border_width
        by1 = by0 + badge_h
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(badge_h * 0.4), fill=MY_SEAT_STYLE["badge_bg"])
        draw.text(((bx0 + bx1)/2, (by0 + by1)/2 + 1), "我", fill=(255, 255, 255),
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
    img.paste(logo, (int(x + (s - logo_s) / 2), int(y + s * 0.38 - logo_s / 2)), logo)
    strip_h = s * 0.28
    box = [x + s * 0.08, y + s - strip_h - s * 0.07, x + s - s * 0.08, y + s - s * 0.07]
    draw.rounded_rectangle(box, radius=int(strip_h * 0.45), fill=style["strip"])
    name = role["name"]
    fs_name = min(s * 0.17, (box[2] - box[0]) / (len(name) * 1.15))
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), name,
              fill=(255, 255, 255), font=get_font(fs_name, bold=True), anchor="mm")


def render(bg_path, seats, excluded, stats, out_path, promo=False):
    img = Image.open(bg_path).convert("RGBA")
    W, H = img.size
    fname = os.path.basename(bg_path)
    lay = BG_LAYOUTS[fname]
    px0, py0, px1, py1 = lay["panel"]
    px0, px1 = px0 * W, px1 * W
    py0, py1 = py0 * H, py1 * H
    pw, ph = px1 - px0, py1 - py0
    draw = ImageDraw.Draw(img)

    pad = pw * 0.02
    gap = pw * 0.015
    header = lay.get("header", True)
    header_h = ph * 0.065 if header else 0
    # 推广区仅在 --promo 且存在小程序码时启用（合规红线：分享图默认无引流元素）
    has_qr = promo and os.path.exists(QR_CODE_PATH)
    footer_h = ph * 0.155 if has_qr else 0

    # 卡片尺寸：宽高双向约束，保证内容不溢出空白面板
    card_w = (pw - pad * 2 - gap * 4) / 5
    card_h_limit = (ph - pad * 2 - header_h - gap * 4.3 - footer_h) / 3.78
    card_s = min(card_w, card_h_limit)

    # 内容块（标题 + 网格 + 场上没有的牌 + 推广区）在面板内垂直居中
    block_h = header_h + 3.78 * card_s + 4.3 * gap + footer_h
    gy0 = py0 + pad + max(0.0, (ph - pad * 2 - block_h) * 0.45)

    # 1. 顶部标题栏 + 阵营统计
    if header:
        title_y = gy0 + header_h * 0.5
        draw.text((px0 + pad, title_y), "轮抽身份顺序", fill=HEADER_COLOR,
                  font=get_font(ph * 0.052, bold=True), anchor="lm")
        stat_text = f"好人 {stats['goose']}  鸭子 {stats['duck']}  中立 {stats['neutral']}"
        draw.text((px1 - pad, title_y), stat_text, fill=SUB_COLOR,
                  font=get_font(ph * 0.030, bold=False), anchor="rm")
    gy0 += header_h

    # 2. 绘制 13 席位 (5 + 5 + 3 居中)
    grid_w = 5 * card_s + 4 * gap
    gx0 = px0 + (pw - grid_w) / 2
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
            _draw_random_card(draw, x, y, card_s, seat)

    # 3. 场上没有的牌
    ex_y = gy0 + 3 * (card_s + gap) + gap * 0.9
    ex_s = card_s * 0.78
    fs_label = get_font(ph * 0.046, bold=True)
    ex_cy = ex_y + ex_s / 2
    draw.text((px0 + pad, ex_cy), "场上没有的牌", fill=HEADER_COLOR, font=fs_label, anchor="lm")

    label_w = draw.textlength("场上没有的牌", font=fs_label)
    ex_x = px0 + pad + label_w + gap * 2.5
    for j, role in enumerate(excluded):
        _draw_excluded_card(img, draw, ex_x + j * (ex_s + gap * 1.5), ex_y, ex_s, role)

    # 4. 推广区：仅 --promo 且有小程序码图片时绘制，绝不画占位假框
    if has_qr:
        footer_y = ex_y + ex_s + gap * 1.4
        qr_size = int(ph * 0.12)
        qr_x = int(px0 + pad)
        qr_img = Image.open(QR_CODE_PATH).convert("RGBA").resize((qr_size, qr_size), Image.LANCZOS)
        img.paste(qr_img, (qr_x, int(footer_y)), qr_img)
        text_x = qr_x + qr_size + pw * 0.03
        draw.text((text_x, footer_y + qr_size * 0.32), "鹅鸭记牌器 · 微信小程序",
                  fill=HEADER_COLOR, font=get_font(ph * 0.038, bold=True), anchor="lm")
        draw.text((text_x, footer_y + qr_size * 0.72), "微信扫码快速记牌",
                  fill=SUB_COLOR, font=get_font(ph * 0.030, bold=False), anchor="lm")
    elif promo:
        print("[提示] 未找到小程序码 海报/qrcode.png，已跳过推广区")

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
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=1, help="生成张数（随机底图）")
    ap.add_argument("--all", action="store_true", help="每张底图各出 1 张")
    ap.add_argument("--bg", default="", help="底图文件名关键字过滤")
    ap.add_argument("--me", type=int, default=None, help="指定我的席位 (1~13)，默认随机指定")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（复现用）")
    ap.add_argument("--promo", action="store_true",
                    help="绘制小程序码推广区（需 海报/qrcode.png；注意平台引流合规风险，默认关闭）")
    ap.add_argument("--out", default=OUT_DIR, help="输出目录")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    roles = load_roles()
    bgs = sorted(f for f in os.listdir(BG_DIR) if f.lower().endswith(".png"))
    if args.bg:
        bgs = [b for b in bgs if args.bg in b]
    bgs = [b for b in bgs if b in BG_LAYOUTS]
    if not bgs:
        print("没有可用的底图！")
        return

    os.makedirs(args.out, exist_ok=True)
    targets = bgs if args.all else [random.choice(bgs) for _ in range(args.n)]
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    for k, bg in enumerate(targets):
        seats, excluded, stats, my_seat = generate_match(roles, my_seat_no=args.me)
        stem = os.path.splitext(bg)[0]
        out = os.path.join(args.out, f"对战记录_{stem}_{ts}.png")
        render(os.path.join(BG_DIR, bg), seats, excluded, stats, out, promo=args.promo)
        print(f"[{os.path.basename(out)}] {summarize(seats, excluded, my_seat)}")


if __name__ == "__main__":
    main()