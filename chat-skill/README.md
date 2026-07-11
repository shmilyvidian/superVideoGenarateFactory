# chat-skill/ — X-Border chat 版 skill

`douyin-video-chat/SKILL.md` 是 **chat(lobehub-xb / XBorder AI)版** 的带货视频 skill。

与仓库里的 Codex skill(`douyin-video-replication-share-kit-api-ready/`)的区别:

| | Codex skill | 本 chat skill |
|---|---|---|
| 运行环境 | Codex CLI 在本机跑 Python 脚本 | chat agent 在对话里调 MCP 工具 |
| 出分镜图 | `scripts/xborder_image.py` | `generateImage`(MCP) |
| 出视频 | `scripts/seedance_submit.py` | `generateSeedanceVideo`(MCP) |
| 图片来源 | 本地文件 → data-URI | 公网图片 URL |
| key | 零 key(经中转) | 零 key(经中转) |

两者共用同一套后端(X-Border 中转 → Replicate seedream-4.5 / seedance-2.0)。

## 依赖
- api-server 已部署带 `generateSeedanceVideo` / `getSeedanceVideoResult` MCP 工具(见 X-Border `packages/api-server`)。
- n11-server Worker 已部署 `/video/seedance/*`(含 `REPLICATE_API_TOKEN`)。
- chat 已安装 X-Border MCP 插件(工具自动发现)。

## 注册到 chat
把 `douyin-video-chat/` 作为一个 skill 注册进 X-Border 市场(`registerSkillFromGitHub` / 上传 zip),用户在 chat 里一键「安装到 XBorder AI」即可。纯新增,不影响其它 skill/agent。
