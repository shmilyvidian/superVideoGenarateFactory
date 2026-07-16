# chat-skill/ — X-Border chat 版 skill

`xborder-video-chat/` 是 **chat(lobehub-xb / XBorder AI)版** 的带货视频 skill,带**完整方法论**(强 Hook 九宫格 + 产品保真 + 先分镜图再出片),不是裸调模型。

```
xborder-video-chat/
├── SKILL.md                        # 编排 + 核心规则(强Hook/产品保真/流程/声音)
└── references/
    ├── prompt-image.md             # 强 Hook 九宫格创作引擎(Hook策略/前3格/prompt公式/景别运镜动作)
    ├── product-fidelity.md         # 产品保真 P0 硬门 + 逐帧 QC
    └── seedance-prompt.md          # 九宫格→Seedance 2.0 视频提示词
```

与 Codex skill(`xborder-video-replication-share-kit-api-ready/`)的区别:

| | Codex skill | 本 chat skill |
|---|---|---|
| 运行 | Codex CLI 跑 Python 脚本 | chat agent 调 MCP 工具 |
| 出分镜图 | `xborder_image.py` | `generateImage`(MCP) |
| 出视频 | `seedance_submit.py` | `generateSeedanceVideo`(MCP) |
| 图片 | 本地文件 → data-URI | 公网 URL |
| 方法论 | 全套(含竞品视频抽帧复刻、文案多源提取、飞书回写) | 强 Hook/产品保真/九宫格→出片(浓缩);竞品复刻仅限用户提供截图/文字 |
| key | 零 key | 零 key |

后端共用(X-Border 中转 → Replicate seedream-4.5 / seedance-2.0)。

## 依赖
- api-server 部署带 `generateSeedanceVideo` / `getSeedanceVideoResult` MCP 工具。
- n11-server Worker 部署 `/video/seedance/*` + `/image/ecom/edit`(含 `REPLICATE_API_TOKEN`)。
- chat 已连 X-Border MCP 插件(工具自动发现)。

## 打包与注册
市场导入器要求 **SKILL.md 在 zip 根**(不是深子目录)。两种正确姿势:
- **市场后台「登记 GitHub 来源」**:仓库 `shmilyvidian/xborder-video-skill` + **子目录 `chat-skill/xborder-video-chat`**(必须填子目录,后台会重打包到根)。
- **上传 zip**:zip 里 `SKILL.md` + `references/` 在根。打包:`cd chat-skill/xborder-video-chat && zip -r ../xborder-video-chat.zip SKILL.md references`。

需市场管理员(`developer` 角色或 `MARKET_ADMIN_USER_IDS`)。纯新增,不影响其它 skill/agent。
