# Douyin Video Replication 分享包

这个包用于把 `douyin-video-replication` 安装到 Codex，让 Codex 按固定流程做抖音电商信息流竞品视频复刻：

- 拆解竞品视频
- 提取和仿写口播/文案
- 生成实际分镜图
- 生成可复制到即梦 Seedance 2.0 的视频提示词
- 可选：使用安装者自己的火山方舟/Seedance API key 自动提交生成任务

现在 skill 内置三条链路：

- `复刻链路`：输入对标/竞品视频，按原有流程完成拆解、仿写、分镜图、Seedance 2.0 提示词和可选 API 出片。
- `强 Hook 九宫格生成出片链路`：输入商品信息、卖点、目标人群和产品图，Codex 按 `prompt_image.md` 生成强 Hook 九宫格脚本，确认后生成 9 段 image2 提示词，调用 image2 出 9 帧分镜图，再生成并可选提交 Seedance 2.0 视频。
- `九宫格成片直投链路`：输入已经做好的 9 帧分镜图和 9 段提示词，不重新生成脚本、不调用 image2，直接整理 Seedance 2.0 视频提示词并可选提交出片。

Seedance 出片支持声音配置：

- `audio_mode=ambient`：默认，保留真实环境音和动作音效，不要人声和背景音乐。
- `audio_mode=music`：环境音 + 动作音效 + 背景音乐。
- `audio_mode=voiceover`：环境音 + 动作音效 + 人声口播。
- `audio_mode=full`：环境音 + 动作音效 + 背景音乐 + 人声口播。
- `audio_mode=silent`：静音，只有用户明确要求无声音时使用。

## 重要安全说明

这个分享包不包含任何真实 API key。

没有 API key 也能正常使用主流程：生成分镜图和 Seedance 提示词后，手动上传到即梦生成视频。

如果安装者自己有火山方舟/Seedance API 权限，可以把自己的 key 配到本地私密文件里，再让 Codex 通过 API 自动提交、轮询和下载视频。

不要把真实 `seedance.env`、`ARK_API_KEY` 或任何密钥上传到 GitHub、发给别人，或放进压缩包。

## 安装

### Windows

1. 解压这个文件夹。
2. 双击 `install_windows.bat`。
3. 看到“安装和自检通过”后，重启 Codex。
4. 在 Codex 里输入：`$douyin-video-replication`

如果 Windows 拦截脚本，右键 `install_windows.bat` 选择运行，或在 PowerShell 里执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1
```

### Mac / Linux

在这个文件夹里运行：

```bash
./install.sh
```

看到“安装和自检通过”后，重启 Codex，然后在 Codex 里输入：`$douyin-video-replication`

使用时可以用自然语言触发路线，例如：

```text
$douyin-video-replication 复刻这个竞品视频，替换成我的产品。
```

```text
$douyin-video-replication 不走复刻，用prompt_image.md帮我生成强Hook九宫格脚本，确认后调image2出9帧分镜图，再调Seedance2.0出视频。
```

```text
$douyin-video-replication 我已经有9帧分镜图和9段提示词，直接走九宫格成片直投链路调用Seedance2.0。
```

```text
$douyin-video-replication 调用Seedance2.0时使用audio_mode=full，要有真实环境音、动作音效、轻快背景音乐和女生口播，不要字幕。
```

## 可选：配置自己的 API key

如果只想手动去即梦生成视频，不需要配置 API key。

如果想让 Codex 自动提交 Seedance API 任务：

### Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_seedance_key_windows.ps1
```

### Mac / Linux

```bash
./setup_seedance_key.sh
```

配置文件会写到：

```text
~/.codex/secrets/seedance.env
```

这个文件只应该留在自己的电脑上，不要分享。

## 环境依赖

- 需要 Codex。
- 需要 Python 3，用于本地自检和辅助脚本。
- 建议安装 ffmpeg，用于本地视频抽帧；没有 ffmpeg 时，视频拆解能力会受影响。
- API 自动出片需要安装者自己的火山方舟/Seedance API key、模型权限和额度。

## GitHub 分享方式

如果把这个 skill 放到 GitHub，别人也可以让 Codex 从 GitHub 目录安装：

```text
$skill-installer install https://github.com/<owner>/<repo>/tree/main/douyin-video-replication
```

安装后需要重启 Codex。
