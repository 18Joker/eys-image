# 项目文件树

> 快照日期：**2026-09-19**（工坊制落地后重生成）。标记：✅ 入 git / ❌ gitignore 不入库。
> 结构变动后请同步本文件（AGENTS.md §2.6）。

```
eys-image2/
├── AGENTS.md                        ✅ 项目规范（§7 = 文件与产物存放规范·工坊制）
├── FILE_TREE.md                     ✅ 本文件
├── .gitignore                       ✅ 首行排除 工坊/；*.zip 一律不入库
│
├── 【基线 · 官方参考】
│   ├── official/                    ✅ 官方原版小图 51 文件
│   ├── official_camps_v3/           ✅ 官方基准 56 角色（鹅24/鸭23/中立9）—— 评估与 prompt 的唯一权威依据
│   └── 官方皮肤套图/                 ✅ 官方皮肤总览图抠图套图（2026-10-06 建，28/56 覆盖，逐格 bbox 见 裁切坐标表.md）
│       ├── 原图/                        官方皮肤总览_780x1044.jpg（唯一权威来源，禁替换）
│       ├── goose/ 鸭阵营 duck/ 中立阵营 neutral/ 抠出的单角色透明 PNG
│       ├── 裁切坐标表.md / .json         28 个角色的 bbox，抠图坐标依据
│       ├── 皮肤覆盖情况.md               已有/缺失清单 + 找素材判断
│       └── _核对/bbox核对_全图.png        红框标注核对图（临时，可删）
│
├── 【交付 · 成套产出】
│   ├── official_v4/                 ✅ 50 文件
│   ├── american_retro_style_v3/     ✅ 59 文件
│   ├── chibi_style_v1/              ✅ 57 文件
│   ├── chibi_style_v2/              ✅ 66 文件
│   ├── daidai/                      ✅ 呆呆鸟风套图 55 张（鹅24/鸭22/中立9），纯白底原图
│   ├── daidai_阵营背景/              ✅ daidai 阵营背景色版 55 张 + 预览.html（2026-10-07 建；goose #DEDEDE / duck #7A1519 / neutral #F7E7A9，脚本：工坊/脚本/评估/daidai背景色全量_20261007.py）
│   └── 海报/                        ✅ 成品海报
│       ├── 鹅鸭杀分享背景/              分享底图 8 张（4 普通 + 4 大留白）
│       ├── 鹅鸭杀分享背景底图-v2/        新版 3:4 全标题底图（compose_match_panel_v3 随机选用）
│       ├── 对战记录分享图/               compose_match_panel*.py 产出
│       ├── 鹅鸭杀记牌器_宣传图_即梦提示词.md
│       └── 即梦实例.txt
│
├── 【数据与文档】
│   ├── config/                      ✅ roles.json / roles-test.json / roles_260918_back.json
│   ├── docs/                        ✅ 用户使用手册.md（§7.4 新文档须走 00-项目规范|01-生图方案|02-评估报告 + 日期前缀）
│   └── new/                         ✅ 待评估新素材收件箱
│       ├── 20260713/  +  _clear/        ⚠️ 内含 4 张 >1MB 未压缩大图；6 张与 official/ 字节重复
│       ├── 20260827/
│       └── url/                          （空目录）
│
├── 【脚本与任务清单】
│   ├── py/                          ✅ 正式脚本
│   │   ├── image_generate_v5.py         Agnes 批量生图（推荐）；跑批在任务 JSON 同目录生成 image_gallery.html
│   │   ├── image_generate_v4.py         同功能基础并发版
│   │   ├── compress_images.py           压缩输出到新目录
│   │   ├── compress_inplace.py          就地近无损压缩，原子替换
│   │   ├── compose_match_panel{,_v2,_v3}.py  对战记录分享面板；v3 卡池读 工坊/批次/my_Q版原图/
│   │   ├── gen_cat_theme_preview.py     读 工坊/批次/cat_theme/ 生成总览 HTML
│   │   ├── check_keys.py                API Key 可用性检查
│   │   ├── run_task.bat / run_task.ps1  一键跑批
│   │   ├── batch_tasks.json  batch_tasks_logo_goose.json   任务清单
│   │   ├── image_understand/            图像理解产物
│   │   └── ⚠️ 历史遗留生成物（不再新增）：image_gallery.html、compare_hd.html、official2_gallery.html、小程序示例.jpg
│   ├── cat_theme_tasks.json         ✅ 批量生图任务清单（历史，留在根目录）
│   ├── cat_theme_tasks - 副本.json   ✅ ⚠️ 违反 §1 命名规范的手工副本，已入库，不追溯
│   ├── 风格测试任务.json              ✅
│   └── 风格测试任务_漫画系列.json      ✅
│
├── 【工坊 · git 永不收录】
│   └── 工坊/                        ❌ .gitignore 首行；约 700M / 502 文件
│       ├── README.md                    目录规则
│       ├── _台账.md                      批次一览 + 迁移记录 + 待清理清单
│       ├── 批次/                          一次生图 = 一个目录（12 个历史批次由 原图归档/ 迁入）
│       │   ├── my_Q版原图/          ❌ 56 文件 ⚠️ 被 compose_match_panel_v3.py 当卡池依赖，勿删
│       │   ├── cat_theme/           ❌ 60 文件 ⚠️ 被 gen_cat_theme_preview.py 依赖
│       │   ├── american_retro_style{,_v2}/ official_camps_v{1,2}/ official_v{2,3}/
│       │   ├── 风格测试/  巫医重设计/  巫医原创设计/  巫医锚点Q版/
│       │   └── （新批次命名 YYYYMMDD_语义名，内含 任务_*.json + images/ + gallery + README.md）
│       ├── 脚本/                      ❌ 原 临时脚本/ 迁入：生图/ 压缩/ 评估/ 预览/ 杂项/ + README.md
│       └── 待清理/                    ❌ cat_theme.zip(83M) 风格测试.zip(57M) goose_侦探.png goose_冒险家.png
│
├── 【已废弃 · 等待手工删除】
│   ├── 美术特征档案/                 ⚠️ 用户已决定删除（4 个文件在 git 里）；相关引用已在 AGENTS.md §3/§5 改指实图
│   ├── 原图归档/                      空壳（内容已迁至 工坊/）
│   └── 临时脚本/                      空壳（内容已迁至 工坊/脚本/）
│
└── 【工具与 AI 数据】
    ├── .agents/skills/              ✅ goose-duck-card-logo2/ goose-duck-card-logo3/ image-border-remover/
    ├── .workbuddy/                  ❌ AI 工作区数据 + memory 日志
    └── .idea/                       ⚠️ IDE 配置，7 个文件被 git 跟踪（建议后续加 ignore，本次不动）
```
