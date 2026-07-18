# chat-skill/ — X-Border chat 版 skill

`xborder-video-chat/` 是 **chat(lobehub-xb / XBorder AI)版** 的带货视频 skill,带**完整方法论**(强 Hook 九宫格 + 产品保真 + 先分镜图再出片),不是裸调模型。

**支持电商平台维度**(2026-07 新增):按 Temu / Noon / Amazon / Shein / Mercado / N11 切换语言、合规、比例、卖点;**没指定平台时 = 抖音/TikTok 默认档,行为与原来完全一致(零回归)**。

```
xborder-video-chat/
├── SKILL.md                        # 编排 + 第0步平台/genre解析 + 核心规则(强Hook/产品保真/流程/声音)
└── references/
    ├── platform-profiles.md        # 电商平台维度档案库(语言/合规/比例/字幕/心智 + 运行参数块 + genre)
    ├── prompt-image.md             # 强 Hook 九宫格创作引擎(Hook策略/前3格/prompt公式/景别运镜动作;含 listing-demo 分支)
    ├── product-fidelity.md         # 产品保真 P0 硬门 + 逐帧 QC
    ├── seedance-prompt.md          # 九宫格→Seedance 2.0 视频提示词
    └── kling-prompt.md             # 单图→Kling v3.0 Pro 视频提示词(1080p)
```

## 平台维度(2026-07 新增)

同一套方法论按**电商平台**切换内容点,**交互流程不变**(两阶段确认、三条链路、Seedance/Kling 引擎选择都不动),只有随平台×模型变的功能点(比例/语言/合规/字幕/卖点/选角)会变:

- **覆盖平台**:Temu / Noon / Amazon / Shein / Mercado / N11 + 默认档(抖音/TikTok)。
- **两个正交字段**:`platform`(语言/合规/比例/卖点心智) × `genre`——`social-ad`(社媒广告,9:16 竖屏、强 Hook 停滑点)/ `listing-demo`(货架详情页/主图视频,1:1、弱 Hook、允许功能字幕)。**六家货架默认 `listing-demo`**,内容电商(默认档)默认 `social-ad`;站外引流/联盟投放由用户切 `social-ad`。
- **覆盖优先级**:用户运行时指定 > 平台档默认 > 全局默认。四维度(语言/合规/规格/心智)均已接进会影响输出的指令。
- **机制**:SKILL 第 0 步解析出「本次运行参数」块贯穿全流程(resolve-then-materialize),各文件引用它,不留悬空指针。
- ⚠️ **Temu 主图视频只收 `1:1/3:4/16:9`**(代码强约束,9:16 会被 X-Border 发布链路 `TEMU_VIDEO_ALLOWED_RATIOS` 拒);其余平台比例为运营建议(平台惯例)。
- **工具比例能力**:`generateImage.scale ∈ {1:1,16:9,9:16}`;`generateSeedanceVideo.aspectRatio ∈ {9:16,1:1,16:9,4:3,3:4}`;`generateKlingVideo` 无比例参数(继承起始图)。
- 详见 `references/platform-profiles.md` 与设计文档 `docs/superpowers/specs/2026-07-18-chat-platform-dimension-design.md`。

## 与 Codex skill 的区别

与 Codex skill(`xborder-video-replication-share-kit-api-ready/`)的区别:

| | Codex skill | 本 chat skill |
|---|---|---|
| 运行 | Codex CLI 跑 Python 脚本 | chat agent 调 MCP 工具 |
| 出分镜图 | `xborder_image.py` | `generateImage`(MCP) |
| 出视频 | `seedance_submit.py` | `generateSeedanceVideo` / `generateKlingVideo`(MCP) |
| 图片 | 本地文件 → data-URI | 公网 URL |
| 方法论 | 全套(含竞品视频抽帧复刻、文案多源提取、飞书回写) | 强 Hook/产品保真/九宫格→出片(浓缩);竞品复刻仅限用户提供截图/文字 |
| 平台维度 | — | 六家电商平台 × genre(见上) |
| key | 零 key | 零 key |

后端共用(X-Border 中转 → Replicate seedream-4.5 / seedance-2.0 / kling-v3)。

## 依赖
- api-server 部署带 `generateSeedanceVideo` / `getSeedanceVideoResult` / `generateKlingVideo` / `getKlingVideoResult` / `generateImage` MCP 工具。
- n11-server Worker 部署 `/video/seedance/*` + `/video/kling/*` + `/image/ecom/edit`(含 `REPLICATE_API_TOKEN`)。
- chat 已连 X-Border MCP 插件(工具自动发现)。

## 打包与注册
市场导入器要求 **SKILL.md 在 zip 根**(不是深子目录)。两种正确姿势:
- **市场后台「登记 GitHub 来源」**:仓库 `shmilyvidian/xborder-video-skill` + **子目录 `chat-skill/xborder-video-chat`**(必须填子目录,后台会重打包到根)。
- **上传 zip**:zip 里 `SKILL.md` + `references/` 在根。打包:`cd chat-skill/xborder-video-chat && zip -r ../xborder-video-chat.zip SKILL.md references`。

需市场管理员(`developer` 角色或 `MARKET_ADMIN_USER_IDS`)。纯新增,不影响其它 skill/agent。
</content>
