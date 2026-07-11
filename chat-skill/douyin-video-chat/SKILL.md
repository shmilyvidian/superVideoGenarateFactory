---
name: douyin-video-chat
description: 在 X-Border chat 里一句话生成抖音带货短视频。用户给产品图 URL + 简短商品信息,自动写强 Hook 提示词并用 generateImage 出分镜图、generateSeedanceVideo 出片(Seedance 2.0,9:16,原生音频)。零 key,全部经 X-Border 中转。用于「用这张商品图出个带货视频/出片/做条抖音视频」这类请求。
---

# 抖音带货短视频(chat 版)

在对话里把「一张产品图 + 一句话商品信息」变成一条 9:16 抖音带货短视频。全部通过 X-Border 内置工具完成,**用户无需任何 API key**(provider key 在服务端)。

## 可用工具(MCP,直接调用)

- **`generateImage`** —— 出分镜图/参考图。必须传 `referenceImageUrl`(公网产品图 URL);建议 `scale:"9:16"`、`model:"seedream-4.5"`。返回图片 URL。
- **`generateSeedanceVideo`** —— 出视频(Seedance 2.0)。传 `prompt` + `referenceImages:[图片URL...]`(产品图/分镜图,最多 9 张)、`aspectRatio:"9:16"`、`duration`、`generateAudio`。同步等待成功时返回视频 URL;超时返回 `taskToken`。
- **`getSeedanceVideoResult`** —— 用 `taskToken` 查询视频结果。

不要跑任何本地脚本;不要向用户索取或谈论 API key。

## 三种节奏(默认走「一句话出片」)

### A. 一句话出片(默认,最快)
用户给「产品图 URL + 一句话(商品名/卖点/场景)」时:
1. 直接写一条强 Hook 的 Seedance 提示词(见下方规则),产品外观以产品图为准。
2. 调 `generateSeedanceVideo({ prompt, referenceImages:[产品图URL], aspectRatio:"9:16", duration:5, generateAudio:true })`。
3. 拿到视频 URL → 用 markdown 给用户;返回 `taskToken` → 调一次 `getSeedanceVideoResult(taskToken)`,好了就给,没好就把 taskToken 交给用户稍后再查。

### B. 先出分镜图再出片(想更可控时)
1. 先 `generateImage({ prompt:<单帧分镜描述>, referenceImageUrl:产品图URL, scale:"9:16", model:"seedream-4.5" })` 出 1 张锁定构图/人物的分镜图。
2. 再 `generateSeedanceVideo({ prompt, referenceImages:[产品图URL, 分镜图URL], aspectRatio:"9:16" })`。**产品图锁外观,分镜图锁构图/镜头。**

### C. 强 Hook 九宫格(用户明确要多帧/九宫格时)
前 3 格必须有停滑点(强 Hook):放大痛点或制造好奇,第 3 格前要出现产品/解决方案。逐格用 `generateImage` 出分镜图,再 `generateSeedanceVideo` 出片。只有用户明确要求时才走这条。

## 产品保真(P0 硬规则)
- 产品外观**唯一以产品图为准**:品类、颜色、结构、材质,以及 logo/文字/图案的位置、大小、方向,都必须与产品图一致。
- 不得凭空改产品品类/颜色/结构;产品图没有的 logo/文字不得凭空生成,产品图有的不得删除或挪到错误位置。
- prompt 里明确写:「产品外观以参考图为准,分镜只锁镜头/构图/动作」。

## Seedance 提示词规则
- 9:16 竖屏;遵守真实物理逻辑(重力、接触点、手部动作、镜头与场景连续性合理)。
- 默认有**原生音频**(真实环境音 + 动作音效)。要背景音乐/口播时在 prompt 里说明;用户明确要静音才 `generateAudio:false`。
- 默认**不加字幕/画面文字**,除非用户明确要。
- 多张参考图时,可在 prompt 里用 `[Image1]`、`[Image2]` 引用(产品图在前、分镜图在后)。
- `duration` 默认 5 秒;用户要更长可加(按模型上限),`-1` 为智能时长。

## 输出规范
- 成功:用 markdown 给出**视频链接**(和可选的分镜图链接),配一句简短说明。
- 仍在生成:告诉用户已提交,调一次 `getSeedanceVideoResult(taskToken)`;仍未完成就把 `taskToken` 交给用户,让其稍后再查。
- 失败:如实说明失败原因(来自工具返回的 `errorMsg`),不要假装成功、不要编造链接。

## 边界与安全
- 图片必须是**公网 URL**。若用户只上传了本地图,先让平台把它变成 URL 再用。
- 不生成、不索取、不谈论任何密钥。
- 只负责本 skill 的带货视频流程,不改动、不干扰其它对话、agent 或工具。
