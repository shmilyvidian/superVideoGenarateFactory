# Super Video Generate Factory

这是一个用于 Codex 的电商短视频生成 skill 分享仓库，核心 skill 是 `douyin-video-replication`。

它支持三条视频生产链路：

1. **复刻链路**：上传对标视频和产品图，Codex 拆解镜头、文案和节奏，再替换成你的产品生成分镜和 Seedance 2.0 视频。
2. **强 Hook 九宫格生成出片链路**：输入商品信息、卖点、目标人群和产品图，Codex 根据 `prompt_image.md` 生成强 Hook 九宫格脚本，再调用 image2 生成 9 帧分镜图，最后调用 Seedance 2.0 出片。
3. **九宫格成片直投链路**：你已经有 9 帧分镜图和 9 段提示词时，Codex 跳过脚本和 image2，直接整理 Seedance 2.0 提示词并出片。

## 目录结构

```text
.
├── demo.md
├── prompt_image.md
├── docs/
│   └── codex-video-skill-usage.md
└── douyin-video-replication-share-kit-api-ready/
    ├── README.md
    ├── install.sh
    ├── install_windows.bat
    ├── install_windows.ps1
    ├── check_install.sh
    ├── setup_seedance_key.sh
    ├── setup_seedance_key_windows.ps1
    ├── secrets/
    │   └── seedance.env.example
    └── douyin-video-replication/
        ├── SKILL.md
        ├── scripts/
        ├── references/
        ├── agents/
        └── tests/
```

## 安装

### macOS / Linux

```bash
cd douyin-video-replication-share-kit-api-ready
./install.sh
```

安装后重启 Codex，然后在 Codex 中使用：

```text
$douyin-video-replication
```

### Windows

解压或克隆仓库后，双击：

```text
douyin-video-replication-share-kit-api-ready/install_windows.bat
```

或者在 PowerShell 中运行：

```powershell
cd douyin-video-replication-share-kit-api-ready
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1
```

## 配置 Seedance API Key

这个仓库 **不会包含真实 API key**。

如果需要自动调用 Seedance 2.0 出片，请在自己的电脑上配置私密 key：

### macOS / Linux

```bash
cd douyin-video-replication-share-kit-api-ready
./setup_seedance_key.sh
```

### Windows

```powershell
cd douyin-video-replication-share-kit-api-ready
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_seedance_key_windows.ps1
```

脚本会把 key 写到本机私密文件：

```text
~/.codex/secrets/seedance.env
```

请不要把真实 `seedance.env`、`ARK_API_KEY` 或任何密钥上传到 GitHub、发给别人或放进压缩包。

## 使用说明

详细使用方式见：

- [Codex 视频生成 Skill 使用说明](docs/codex-video-skill-usage.md)
- [Demo 对话模板](demo.md)
- [分享包 README](douyin-video-replication-share-kit-api-ready/README.md)

## 常用启动模板

### 强 Hook 九宫格生成出片

```text
$douyin-video-replication

走强 Hook 九宫格生成出片链路。
我会上传产品图，下面是商品信息。
请先根据 prompt_image.md 生成强 Hook 9 宫格中文分镜脚本，前三格必须有停滑点。
脚本确认后，再生成 9 段 image2 提示词，调用 image2 出 9 帧分镜图，最后调用 Seedance 2.0 出视频。

商品名称：
核心卖点：
目标人群：
使用场景：
视频语言：
视频时长：
视觉风格：
声音模式：ambient / music / voiceover / full / silent
```

### 九宫格成片直投

```text
$douyin-video-replication

走九宫格成片直投链路。

我会上传 9 帧分镜图和 9 段提示词。
这些提示词是根据 prompt_image.md 生成的。
不要重新生成脚本，不要调用 image2。
请直接根据这 9 帧图和 9 段提示词整理 Seedance 2.0 视频提示词，并调用 Seedance 2.0 出视频。
```

### 对标视频复刻

```text
$douyin-video-replication

走复刻链路。

我会上传一个对标视频和我的产品图。
请先拆解对标视频的镜头、动作、文案和节奏，再替换成我的产品。
生成分镜图和 Seedance 2.0 视频提示词，最后调用 Seedance 2.0 出视频。
```

## 声音模式

Seedance 出片支持 `audio_mode`：

- `ambient`：默认，保留真实环境音和动作音效，不要人声和背景音乐。
- `music`：环境音 + 动作音效 + 背景音乐。
- `voiceover`：环境音 + 动作音效 + 人声口播。
- `full`：环境音 + 动作音效 + 背景音乐 + 人声口播。
- `silent`：静音，只有用户明确要求无声音时使用。

示例：

```text
调用 Seedance 2.0 时使用 audio_mode=full，要有真实环境音、动作音效、轻快背景音乐和女生口播，不要字幕。
```

## 安全说明

- 仓库只包含 `secrets/seedance.env.example` 占位示例。
- 不要提交真实 `seedance.env`。
- 不要在 Markdown、脚本、测试或 issue/PR 中粘贴真实 key。
- 如果 key 曾经出现在聊天、截图或日志中，建议在火山方舟后台轮换新 key。
