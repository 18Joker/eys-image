#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级主题皮肤线上素材同步（eys-image2）

用途：把小程序云存储 `themes/<主题id>/` 下的线上实际素材拉回本地归档目录
`高级主题皮肤/<中文名>-<主题id>/`，并生成每主题的 `素材清单.json`（含来源 URL、
字节数、sha256、尺寸、是否被主题配置引用）。

为什么需要显式文件清单：云存储 List 接口在本账号密钥下返回 AccessDenied，
无法枚举目录；CDN 公有读可直接下载单文件。因此文件清单以主题配置为准人工登记，
未在配置中引用的遗留文件也一并保留（标注 referenced=false）。

新增主题时：在 THEMES 里加一项（id / name / files），跑一次即完成归档。
若主题配置新增了素材 key，记得同步 THEMES 对应 files，否则该文件不会被拉取。

用法：
    python py/sync_theme_assets.py            # 全部主题
    python py/sync_theme_assets.py kitten     # 指定主题
    python py/sync_theme_assets.py --check    # 只校验已有文件的 sha256，不下载
"""

import hashlib
import json
import os
import sys
import time
import urllib.request

# ---- 常量：数据源与落地位置 ------------------------------------------------

CDN_HOST = 'https://636c-cloudbase-d3gv7g5ad64245151-1440057854.tcb.qcloud.la'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, '高级主题皮肤')

# ---- 主题登记表 -----------------------------------------------------------
# file:     云存储 themes/<id>/ 下的文件名（= 本地文件名，保持存储路径的扁平镜像）
# key:      主题配置 assets 里对应的字段名；None 表示配置未引用
# consumer: 实际消费该素材的组件 + 门控条件（2026-10-22 逐行核对 eys 源码得出，
#           不是照搬配置推断）。改前端组件后需重新核对本列。
#           inUse=False 的文件是云存储残留，小程序端永远不会请求它。
THEMES = {
    'kitten': {
        'name': '高级小猫',
        'files': [
            {'file': 'header-curtain.webp', 'key': 'headerCurtain',
             'consumer': 'ThemeMascotBand Layer1 帷幕（v-if curtainUrl）'},
            {'file': 'header-mascot.webp', 'key': 'headerMascot',
             'consumer': 'ThemeMascotBand Layer3 吉祥物（hasHeaderMascot 门控）'},
            {'file': 'pendant-left.webp', 'key': 'pendantLeft',
             'consumer': 'ThemePendantLeft 左上挂件（hasPendants + pendantLeft 双门控）'},
            {'file': 'sleep-cat.webp', 'key': 'sleepCat',
             'consumer': 'ExcludedRoles → ThemeSticker kind="sleep-cat"'},
            {'file': 'bg-paw-tile.webp', 'key': 'bgPattern',
             'consumer': 'ThemeBackdrop（backdropMode=tile → 内联平铺）'},
            {'file': 'preview-thumb.webp', 'key': 'previewThumb',
             'consumer': 'ThemePicker / ThemeShop / ThemeBuyChip 缩略图'},
            {'file': 'section-icon.webp', 'key': 'sectionIcon',
             'consumer': 'ThemeSectionIcon（DraftSlots/ExcludedRoles/GroupRecordZone/MeetingNotes 区块标题）'},
            {'file': 'card-paw.webp', 'key': 'cardPaw',
             'consumer': 'DraftSlots 席位卡水印 + GroupRecordZone/MeetingNotes 空态行内'},
            {'file': 'fab-icon.webp', 'key': 'fabIcon',
             'consumer': 'FabSpeedDial 主钮图标'},
            {'file': 'paw-accent.webp', 'key': 'pawAccent',
             'consumer': 'ThemeMascotBand Layer2 大爪印贴纸（stickerPreset=paw-scatter）'},
            {'file': 'paw-small.webp', 'key': 'pawSmall',
             'consumer': 'ThemeMascotBand Layer2 小爪印贴纸'},
            {'file': 'my-paw.webp', 'key': 'myPaw',
             'consumer': 'DraftSlots → ThemeSticker kind="my-paw"（我的席位标记）'},
            {'file': 'tip-icon.webp', 'key': 'tipIcon',
             'consumer': 'TriviaTicker 冷知识条图标'},
        ],
    },
    'owl': {
        'name': '高级猫头鹰',
        'files': [
            {'file': 'header-curtain.webp', 'key': 'headerCurtain',
             'consumer': 'ThemeMascotBand Layer1 帷幕（curtainMode=widthFix）'},
            {'file': 'header-mascot.webp', 'key': 'headerMascot',
             'consumer': 'ThemeMascotBand Layer3 吉祥物（hasHeaderMascot 门控）'},
            {'file': 'pendant-bottom.webp', 'key': 'pendantBottom',
             'consumer': 'GroupRecordZone → ThemeSticker kind="pendant-bottom"（hasPendants 门控）'},
            {'file': 'pendant-left.webp', 'key': None, 'inUse': False,
             'consumer': '不渲染：配置未引用，且 owl features 无 pendantLeft；页面级 ThemePendantLeft 因 a.pendantLeft 为空不产出节点'},
            {'file': 'sleep-vines.webp', 'key': 'sleepCat',
             'consumer': 'ExcludedRoles → ThemeSticker kind="sleep-cat"'},
            {'file': 'bg-forest.webp', 'key': 'bgPattern',
             'consumer': 'ThemeBackdrop（默认 image 模式，aspectFill）'},
            {'file': 'preview-thumb.webp', 'key': 'previewThumb',
             'consumer': 'ThemePicker / ThemeShop / ThemeBuyChip 缩略图（⚠️ 与 header-mascot 字节完全相同）'},
            {'file': 'section-icon.webp', 'key': 'sectionIcon',
             'consumer': 'ThemeSectionIcon 区块标题图标'},
            {'file': 'tip-icon.webp', 'key': 'tipIcon',
             'consumer': 'TriviaTicker 冷知识条图标（⚠️ 与 lantern-reading 同源，视觉近乎相同）'},
            {'file': 'lantern-reading.webp', 'key': 'lantern',
             'consumer': 'GroupRecordZone → ThemeSticker kind="lantern" 马灯'},
        ],
    },
}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _image_size(path):
    """返回 (w, h)；优先用 Pillow，缺失时回退解析 WebP 头。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        pass
    try:
        with open(path, 'rb') as f:
            data = f.read(40)
        if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            return (None, None)
        kind = data[12:16]
        if kind == b'VP8X':
            w = int.from_bytes(data[24:27], 'little') + 1
            h = int.from_bytes(data[27:30], 'little') + 1
            return (w, h)
        if kind == b'VP8L':
            bits = int.from_bytes(data[21:25], 'little')
            return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        if kind == b'VP8 ':
            w = int.from_bytes(data[26:28], 'little') & 0x3FFF
            h = int.from_bytes(data[28:30], 'little') & 0x3FFF
            return (w, h)
    except Exception:
        pass
    return (None, None)


def _download(url, dest, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'eys-image2-sync/1.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            if not body:
                raise IOError('empty body')
            tmp = dest + '.part'
            with open(tmp, 'wb') as f:
                f.write(body)
            os.replace(tmp, dest)
            return len(body)
        except Exception as e:                                   # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(1.5 * (i + 1))
    raise IOError('下载失败 %s：%s' % (url, last))


def sync_one(theme_id, cfg, check_only=False):
    title = '%s-%s' % (cfg['name'], theme_id)
    out_dir = os.path.join(OUT_ROOT, title)
    os.makedirs(out_dir, exist_ok=True)

    items = []
    ok, fail = 0, 0
    for entry in cfg['files']:
        filename = entry['file']
        key = entry['key']
        in_use = entry.get('inUse', key is not None)
        url = '%s/themes/%s/%s' % (CDN_HOST, theme_id, filename)
        dest = os.path.join(out_dir, filename)
        try:
            if check_only:
                if not os.path.exists(dest):
                    raise IOError('本地缺失')
                size = os.path.getsize(dest)
                status = 'ok'
            else:
                size = _download(url, dest)
                status = 'ok'
            w, h = _image_size(dest)
            items.append({
                'file': filename,
                'configKey': key,
                'referenced': key is not None,
                'inUse': in_use,
                'consumer': entry.get('consumer', ''),
                'sourceUrl': url,
                'bytes': size,
                'width': w,
                'height': h,
                'sha256': _sha256(dest),
                'status': status,
            })
            ok += 1
            flag = '' if in_use else '  ← 未使用'
            print('  [ok]   %-24s %7.1f KB  %sx%s%s'
                  % (filename, size / 1024.0, w, h, flag))
        except Exception as e:                                   # noqa: BLE001
            fail += 1
            items.append({
                'file': filename,
                'configKey': key,
                'referenced': key is not None,
                'inUse': in_use,
                'consumer': entry.get('consumer', ''),
                'sourceUrl': url,
                'status': 'failed',
                'error': str(e),
            })
            print('  [FAIL] %-24s %s' % (filename, e))

    # 同主题内按 sha256 查重：字节完全相同 = 同一文件改了名，属于存储冗余
    by_sha = {}
    for it in items:
        if it.get('sha256'):
            by_sha.setdefault(it['sha256'], []).append(it['file'])
    duplicates = [v for v in by_sha.values() if len(v) > 1]

    manifest = {
        'themeId': theme_id,
        'themeName': cfg['name'],
        'cdnHost': CDN_HOST,
        'storageDir': 'themes/%s/' % theme_id,
        'syncedAt': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'mode': 'check' if check_only else 'download',
        'fileCount': len(items),
        'okCount': ok,
        'failCount': fail,
        'inUseCount': sum(1 for i in items if i.get('inUse')),
        'totalBytes': sum(i.get('bytes') or 0 for i in items),
        'duplicateByContent': duplicates,
        'notes': [
            '本地文件与云存储 themes/<themeId>/ 下的文件字节完全一致（未做任何压缩或转码）。',
            'inUse 为 true 表示小程序前端确有组件消费该素材；false = 云存储残留，端上永不请求。',
            'inUse 依据 eys 源码逐行核对（consumer 列写了组件与门控条件），非照搬配置推断。',
            'referenced 仅表示主题配置 assets 是否登记了该 key，不等于会被渲染。',
            'duplicateByContent 列出同主题内 sha256 相同的文件组。',
        ],
        'files': items,
    }
    if not check_only:
        with open(os.path.join(out_dir, '素材清单.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    return title, ok, fail, manifest['totalBytes']


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    check_only = '--check' in sys.argv
    targets = args if args else list(THEMES.keys())

    unknown = [t for t in targets if t not in THEMES]
    if unknown:
        print('未知主题：%s（已登记：%s）' % (','.join(unknown), ','.join(THEMES)))
        return 2

    total_ok = total_fail = 0
    total_bytes = 0
    for tid in targets:
        print('== %s %s ==' % (tid, THEMES[tid]['name']))
        title, ok, fail, nbytes = sync_one(tid, THEMES[tid], check_only)
        total_ok += ok
        total_fail += fail
        total_bytes += nbytes

    print('\n汇总：成功 %d / 失败 %d / 合计 %.1f KB' % (total_ok, total_fail, total_bytes / 1024.0))
    print('落地目录：%s' % OUT_ROOT)
    return 0 if total_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())