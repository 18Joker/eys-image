# 高级主题皮肤（小程序线上素材归档）

鹅鸭记牌器小程序**高级主题（付费皮肤）**在腾讯云开发对象存储里的线上实际素材，按主题分目录归档。
2026-10-22 建立，**未来新增高级主题一律放这里**。

## 目录结构

```
高级主题皮肤/
├── README.md                       本说明
├── 高级小猫-kitten/                 主题 id = kitten，13 个文件 + 素材清单.json
└── 高级猫头鹰-owl/                  主题 id = owl，10 个文件 + 素材清单.json
```

- 子目录命名：`<中文主题名>-<主题id>`，与小程序主题配置里的 `id` 对齐，便于双向追溯。
- 目录内文件是云存储 `themes/<主题id>/` 的**扁平镜像**：本地文件名 = 线上文件名，未做任何压缩或转码。
- 每个主题目录内 `素材清单.json` 记录：来源 URL、字节数、宽高、sha256、对应的配置字段名（`configKey`）、
  **是否真的会被小程序渲染（`inUse`）**、消费组件与门控条件（`consumer`）。

## 哪些真的在投入使用（2026-10-22 逐行核对源码）

判定口径：**只有前端存在组件消费、且门控条件成立，才算"在用"**。
配置里登记了 key 但不等于会渲染——门控条件（`features.*`）不成立时组件直接不产出节点。

| 主题 | 文件数 | 真正在用 | 云存储残留（端上永不请求） |
|---|---|---|---|
| 高级小猫 kitten | 13 | **13** | 0 |
| 高级猫头鹰 owl | 10 | **9** | 1（`pendant-left.webp`） |

### 未投入使用的文件

| 文件 | 原因 |
|---|---|
| `高级猫头鹰-owl/pendant-left.webp` | 主题配置 `assets` 没登记这个 key，且 owl 的 `features` 里没有对应开关。页面级组件 `ThemePendantLeft` 的渲染条件是 `hasPendants && assets.pendantLeft`，后者为空 → 不产出节点。owl 的页角挂件实际走 `pendantBottom`（`GroupRecordZone` 内挂载）。此文件是早期迭代残留。 |

### 内容重复（字节完全相同）

| 文件组 | 结论 |
|---|---|
| `高级猫头鹰-owl/header-mascot.webp` ≡ `preview-thumb.webp` | **是同一个文件的副本**，sha256 完全一致（`d1f56d11…`），均 900×507 / 99.0 KB。属存储冗余：缩略图直接复用了吉祥物原图，未单独做小尺寸预览图。两端都在用（缩略图走选择器/商店，吉祥物走顶部装饰），功能上各自正常，只是多存了一份同样的字节。 |

### 视觉相近但字节不同（非重复，不必处理）

| 文件组 | 说明 |
|---|---|
| `高级猫头鹰-owl/tip-icon.webp` vs `lantern-reading.webp` | 同源于"复古马灯"素材，感知哈希几乎一致（176×176 vs 176×177，差异主要在边缘）。但字节不同、用途不同：`tipIcon` 是冷知识条的 176×176 图标，`lantern` 是报团记录区右侧的 176×177 挂件。**有意复用同一母版**，不是误传。 |
| kitten 的 `section-icon` / `card-paw` / `fab-icon` / `paw-accent` | 四者同源于"爪印大"素材，按不同用途分别缩放+着色+设透明度产出（`py/` 的 `theme-asset-spec.json` 有完整规格）。属于设计上的同源派生，不是重复。 |

## 数据来源

| 项 | 值 |
|---|---|
| 云存储目录 | `themes/kitten/`、`themes/owl/` |
| CDN Host | `https://636c-cloudbase-d3gv7g5ad64245151-1440057854.tcb.qcloud.la` |
| 配置权威源 | 云数据库 `ai_config` 集合 `_id = themes_config` |
| 同步脚本 | `py/sync_theme_assets.py` |

三处口径不一致时的取用原则：**文件内容以 CDN 下载到的为准**（这里存的就是线上实际生效的图）；
素材 key 与消费位置以数据库 `themes_config` 为准（不要用工作区根目录那份 2026-09-08 的快照，
它已落后于线上）。

## 未来新增高级主题怎么放

1. 在 `py/sync_theme_assets.py` 的 `THEMES` 里加一项：`id`、`name`（中文名）、`files`（`(文件名, 配置字段名)` 列表）。
2. 跑 `python py/sync_theme_assets.py <新主题id>`，脚本会自动建 `<中文名>-<id>/` 目录、下载全部文件、生成 `素材清单.json`。
3. 在本 README 的目录结构里补一行。

> ⚠️ 云存储的 List 接口在本账号密钥下返回 `AccessDenied`，**无法枚举目录**，所以文件清单靠 `THEMES` 显式登记。
> 主题配置新增素材 key 时，务必同步更新 `THEMES`，否则该文件不会被拉取。

## 已知差异（以本目录的线上版本为准）

| 文件 | 本地旧产物 | 线上（本目录） | 说明 |
|---|---|---|---|
| `高级小猫-kitten/card-paw.webp` | 4008 B | 2670 B | 同 120×120；线上是 2026-08-30 加深配色后的版本（暖橙 #C06840 / alpha 60%），本地 `kitten_raw_v6_dist/` 仍是加深前的旧图 |
| `高级猫头鹰-owl/preview-thumb.webp` | 450×975（竖版，38.9 KB） | 900×507（横版 2:1，99.0 KB） | 线上是重制后的正确 2:1 缩略图，本地 `猫头鹰/processed/` 为早期竖版作废稿 |

其余 21 个文件与小程序仓库 `eys/access/kitten_raw_v6_dist/`、`eys/access/猫头鹰/processed/` 的对应文件 **sha256 完全一致**。

## 遗留文件

`高级猫头鹰-owl/pendant-left.webp`（200×200，12.9 KB）在云存储中仍可访问，但**小程序端不会渲染它**，
详见上文「未投入使用的文件」。保留在此仅作追溯；是否从云存储清理由人工决定，AI 不代为删除。

## 素材用途速查

| configKey | kitten 文件 | owl 文件 | 消费位置 |
|---|---|---|---|
| `headerCurtain` | header-curtain.webp | header-curtain.webp | 顶部帷幕（ThemeMascotBand Layer1） |
| `headerMascot` | header-mascot.webp | header-mascot.webp | 顶部吉祥物（ThemeMascotBand Layer3） |
| `pendantLeft` | pendant-left.webp | —（未使用） | 左上角挂件（ThemePendantLeft） |
| `pendantBottom` | — | pendant-bottom.webp | 页角挂件（GroupRecordZone 内 ThemeSticker） |
| `sleepCat` | sleep-cat.webp | sleep-vines.webp | 空态装饰（ExcludedRoles） |
| `bgPattern` | bg-paw-tile.webp | bg-forest.webp | 背景层：kitten 平铺 / owl 整图（ThemeBackdrop） |
| `previewThumb` | preview-thumb.webp | preview-thumb.webp（= mascot 副本） | 主题选择器 / 商店 / 直购卡缩略图 |
| `sectionIcon` | section-icon.webp | section-icon.webp | 区块标题图标（ThemeSectionIcon） |
| `cardPaw` | card-paw.webp | — | 席位卡水印 + 空态行内爪印 |
| `fabIcon` | fab-icon.webp | — | 悬浮主按钮图标（FabSpeedDial） |
| `pawAccent` / `pawSmall` | 同名 .webp | — | 顶部爪印贴纸 ×6（stickerPreset=paw-scatter） |
| `myPaw` | my-paw.webp | — | 我的席位标记爪印（DraftSlots） |
| `tipIcon` | tip-icon.webp | tip-icon.webp | 冷知识条提示图标（TriviaTicker） |
| `lantern` | — | lantern-reading.webp | 报团记录区右侧复古马灯（GroupRecordZone） |

预览：打开同目录 `预览.html`（直接 `<img>` 引用原图，无内嵌缩略图；未使用/重复文件有角标标注）。