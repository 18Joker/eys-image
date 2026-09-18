# 项目文件树

```
eys-image/
├── .agents/
│   └── skills/
├── american_retro_style_v2/
│   ├── duck/
│   │   ├── duck_专杀.png
│   │   ├── duck_丘比特.png
│   │   ├── duck_刺客.png
│   │   ├── duck_变形.png
│   │   ├── duck_小丑.png
│   │   ├── duck_巫医.png
│   │   ├── duck_忍者.png
│   │   ├── duck_投毒者.png
│   │   ├── duck_掠夺者.png
│   │   ├── duck_炸弹.png
│   │   ├── duck_狙击手.png
│   │   ├── duck_超能力.png
│   │   ├── duck_间谍.png
│   │   ├── duck_隐形.png
│   │   ├── duck_食鸟鸭.png
│   │   └── duck_鸭子.png
│   ├── goose/
│   │   ├── goose_侦探.png
│   │   ├── goose_加拿大鹅.png
│   │   ├── goose_士兵.png
│   │   ├── goose_复仇.png
│   │   ├── goose_大白鹅.png
│   │   ├── goose_工程师.png
│   │   ├── goose_恶魔猎手.png
│   │   ├── goose_探测.png
│   │   ├── goose_星界.png
│   │   ├── goose_模仿者.png
│   │   ├── goose_正义使者.png
│   │   ├── goose_殡仪员.png
│   │   ├── goose_法医.png
│   │   ├── goose_猪头.png
│   │   ├── goose_肉汁.png
│   │   ├── goose_观鸟.png
│   │   ├── goose_警长.png
│   │   ├── goose_跟踪.png
│   │   └── goose_通灵.png
│   ├── neutral/
│   │   ├── neutral_乌鸦.png
│   │   ├── neutral_决斗呆呆.png
│   │   ├── neutral_呆呆鸟.png
│   │   ├── neutral_喜鹊.png
│   │   ├── neutral_布谷鸟.png
│   │   ├── neutral_渡鸦.png
│   │   ├── neutral_猎鹰.png
│   │   ├── neutral_秃鹫.png
│   │   ├── neutral_醍醐.png
│   │   └── neutral_鸽子.png
│   └── style.md
├── config/
│   └── roles.json
├── official_v3/
│   ├── duck/
│   │   ├── duck_专杀.png
│   │   ├── duck_丘比特.png
│   │   ├── duck_刺客.png
│   │   ├── duck_变形.png
│   │   ├── duck_小丑.png
│   │   ├── duck_巫医.png
│   │   ├── duck_忍者.png
│   │   ├── duck_投毒者.png
│   │   ├── duck_掠夺者.png
│   │   ├── duck_炸弹.png
│   │   ├── duck_狙击手.png
│   │   ├── duck_超能力.png
│   │   ├── duck_间谍.png
│   │   ├── duck_隐形.png
│   │   ├── duck_食鸟鸭.png
│   │   └── duck_鸭子.png
│   ├── goose/
│   │   ├── goose_侦探.png
│   │   ├── goose_加拿大鹅.png
│   │   ├── goose_士兵.png
│   │   ├── goose_复仇.png
│   │   ├── goose_大白鹅.png
│   │   ├── goose_工程师.png
│   │   ├── goose_探测.png
│   │   ├── goose_星界.png
│   │   ├── goose_模仿者.png
│   │   ├── goose_正义使者.png
│   │   ├── goose_殡仪员.png
│   │   ├── goose_法医.png
│   │   ├── goose_猪头.png
│   │   ├── goose_肉汁.png
│   │   ├── goose_观鸟.png
│   │   ├── goose_警长.png
│   │   ├── goose_跟踪.png
│   │   └── goose_通灵.png
│   ├── neutral/
│   │   ├── neutral_决斗呆呆.png
│   │   ├── neutral_呆呆鸟.png
│   │   ├── neutral_喜鹊.png
│   │   ├── neutral_布谷鸟.png
│   │   ├── neutral_渡鸦.png
│   │   ├── neutral_猎鹰.png
│   │   ├── neutral_秃鹫.png
│   │   ├── neutral_醍醐.png
│   │   └── neutral_鸽子.png
│   └── style.md
├── output/
│   ├── american_retro_style_v2/
│   │   └── goose/
│   │       ├── goose_殡仪员_1.png
│   │       ├── goose_殡仪员_2.png
│   │       ├── goose_殡仪员_3.png
│   │       ├── goose_殡仪员_4.png
│   │       ├── goose_殡仪员_5.png
│   │       └── goose_殡仪员_6.png
│   └── official_v3/
│       └── goose/
│           ├── goose_殡仪员_1.png
│           ├── goose_殡仪员_2.png
│           ├── goose_殡仪员_3.png
│           ├── goose_殡仪员_4.png
│           └── goose_殡仪员_5.png
├── 海报/
│   ├── 鹅鸭杀分享背景底图-v2/   # v3 分享图底图 5 张（compose_match_panel_v3.py 随机选用）
│   ├── 鹅鸭杀分享背景/          # 分享底图 8 张（4 普通 + 4 大留白）
│   └── 对战记录分享图/          # compose_match_panel.py 产出的对战记录分享图
└── py/
    ├── batch_tasks.json
    ├── compose_match_panel.py   # 对战记录分享面板生成器（13 席位 + 场上没有的牌）
    ├── compose_match_panel_v2.py # v2：多底图布局表 + 我的位置高亮 + 阵营统计
    ├── compose_match_panel_v3.py # v3：新版 3:4 全标题底图（标题由底图自带，只填卡片）
    ├── image_gallery.html
    ├── image_generate_v4.py
    ├── official2_gallery.html
    └── 小程序示例.jpg
```
