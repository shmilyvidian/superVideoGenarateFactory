---
name: xborder-video-chat
description: 在 X-Border chat 里生成高转化抖音/TikTok 带货短视频。不是裸喂模型——按强 Hook 九宫格方法论:先写强停滑点分镜脚本、产品保真锁定、用 generateImage 出分镜图、再用 generateSeedanceVideo 出 Seedance 2.0 视频(9:16、原生音频)。零 key,经 X-Border 中转。用于「用这张商品图出个带货视频/做条抖音带货视频/强Hook短视频/九宫格出片」这类请求。
---

# 抖音带货短视频(chat 版 · 强 Hook 方法论)

把「产品图 + 商品信息」做成一条**高转化**的 9:16 带货短视频。核心不是把图丢给模型,而是走一套方法论:**强 Hook 分镜脚本 → 产品保真 → 分镜图 → Seedance 出片**。全程用 X-Border 内置工具,用户零 key。

裸调模型出的片很平、转化差。这个 skill 的价值就是把「强 Hook + 产品保真 + 先分镜图再出片」这套导演方法论套上去。

## 可用工具(MCP)
- **`generateImage`** — 出分镜图。传 `referenceImageUrl`(公网产品图 URL)+ `prompt`(英文分镜提示词)+ `scale:"9:16"` + `model:"seedream-4.5"`。返回图片 URL。**它是编辑型:产品图作参考,保住产品外观。**
- **`generateSeedanceVideo`** — 出视频。传 `prompt`(最终视频提示词)+ `referenceImages:[产品图URL, 分镜图URL…]`(≤9)+ `aspectRatio:"9:16"` + `duration` + `generateAudio`。异步:成功返回视频 URL,超时返回 `taskToken`。
- **`getSeedanceVideoResult`** — 用 `taskToken` 查视频结果。
- **`generateKlingVideo`** — 出视频(Kling v3.0 Pro,1080p)。传 `prompt`(最终视频提示词)+ `imageUrl`(**单张**起始图 URL:最强 Hook 帧或产品图)+ `duration`(3–15)+ `generateAudio`。**只收单张图,不吃九宫格多帧。** 异步:成功返回视频 URL,超时返回 `taskToken`。
- **`getKlingVideoResult`** — 用 `taskToken` 查 Kling 视频结果。

不跑本地脚本;不向用户要 key。

## 视频引擎选择(Seedance vs Kling)
- **Seedance(默认主力)**:收多帧参考图(产品图 + 分镜图 ≤9),契合九宫格方法论。要多帧锁镜头/构图/节奏、走完整九宫格 → 用它。
- **Kling v3.0 Pro**:只收**单张**起始图 → 1080p 视频。适合:用户只有/只想用一张主图、要 1080p、或要一条轻量单帧动起来的片。**它吃不了九宫格 9 帧**——只能取一张(最强 Hook 帧或产品图)作起始图。
- 拿不准就问用户「要走完整九宫格(Seedance)还是单张主图出片(Kling 1080p)」。两条都要产品保真。

## 三条链路(选一条)
1. **强 Hook 九宫格生成出片(默认,推荐)** — 有产品图 + 商品信息 → 写强 Hook 九宫格脚本 → 出分镜图 → 出片。**要好效果就走这条。**
2. **九宫格直投** — 用户已经有 9 帧分镜图(URL)+ 脚本 → 跳过脚本/出图,直接写 Seedance 提示词 + 出片。
3. **竞品复刻(chat 受限)** — 竞品视频的拆解要看视频帧,chat 里 agent 做不了本地抽帧。只能:用户**贴出竞品的关键截图(图片)或用文字描述镜头/文案/节奏**,agent 据此复刻。别假装能"看视频"。

## 核心流程:强 Hook 九宫格生成出片

> 详规见 references,关键步骤如下。**必须两阶段:先出中文脚本给用户确认,确认后才出图/出片。**

1. **建产品保真契约(内部)** — 看产品图,列出品类/颜色/结构/材质/logo 位置大小方向。这是 P0 硬约束(详见 `references/product-fidelity.md`)。
2. **【第一阶段】写强 Hook 九宫格中文脚本** — 先判断用哪种 Hook(痛点夸张/结果前置/反常识/冲突对比/场景代入),前 3 格必须有停滑点。9 格:Hook(1-3)→ Solution(4-6)→ Trust&CTA(7-9)。先定统一视觉基调。用表格输出,**末尾问用户确认**。规则详见 `references/prompt-image.md`。
3. **确认后【第二阶段】出分镜图** — 把每格中文脚本转成英文分镜 prompt(公式:景别+运镜+主体动作+场景+光影+全局色系+`vertical format, 9:16` + 质感词 + `no timecode, no subtitles`),用 `generateImage`(产品图 URL 作 `referenceImageUrl`)逐帧出图。**至少出前 3 格 Hook 帧 + 关键 Solution/CTA 帧;要精出全 9 帧。** 产品保真:产品图锁外观。
4. **写 Seedance 视频提示词** — 按 `references/seedance-prompt.md`:9 格逐格写(时间码→景别/运镜→主体动作→卖点表达→场景→光线→质感→声音→产品一致性→物理约束),产品图优先锁产品外观,分镜图锁镜头/构图/节奏。禁字幕、禁画面文字、禁引用生成视频。
5. **出片** —
   - 九宫格多帧(默认):`generateSeedanceVideo({ prompt, referenceImages:[产品图URL, 分镜图URL…], aspectRatio:"9:16", duration, generateAudio })`。
   - 单主图/1080p:`generateKlingVideo({ prompt, imageUrl:<最强 Hook 帧或产品图 URL>, duration, generateAudio })`,提示词按 `references/kling-prompt.md`。
6. **取结果** — 超时拿 `taskToken` → `getSeedanceVideoResult` 或 `getKlingVideoResult`(按用的引擎)轮询 → 视频 URL markdown 发给用户。

## 产品保真(P0 硬门 · 摘要)
- 产品外观**唯一以产品图为准**:品类、颜色、结构、材质,logo/文字/图案的位置/大小/方向/在哪一面,都要和产品图一致。
- 不得为规避生成难度而删/弱化产品身份细节;产品图有 logo 且镜头该露出那一面,就必须在正确物理位置和比例上保留。
- 产品图没有的 logo/文字不得凭空生成。
- 分镜图若和产品图冲突,**产品图优先**;分镜图只锁镜头/构图/场景/节奏。
- 逐帧 QC:①产品保真 ②logo 物理逻辑 ③真实物理 ④和脚本一致。P0 不过(品类/颜色/形变/logo 错位)= 这帧作废,别拿去出片。

## 强 Hook(摘要)
- 前 3 格 = 短视频前 3 秒,必须有停滑点:夸张痛点 / 结果前置 / 反常识 / 冲突对比 / 场景代入。
- 分镜1 明确停滑点;分镜2 继续放大痛点或制造好奇;分镜3 产品/解决方案必须出现,不能拖到第4格。
- 前 3 格用有冲击力的运镜(quick zoom in、handheld slight shake、fast cut、dramatic close-up)。
- 允许夸张(表情/动作/前后对比/镜头冲击),**禁止虚构功效、医疗承诺、绝对化用语**(食品/美妆/健康/母婴/个护尤其)。
- 出脚本前内部做 Hook 自检(停滑冲击力/痛点清晰度/夸张度/产品转折速度/前3秒信息密度),弱就重写前 3 格。

## 声音(audio_mode)
`generateAudio:true` 默认。方向写进视频 prompt:
- `ambient`(默认):真实环境音 + 动作音效,无人声无 BGM。
- `music`:+ 背景音乐。 `voiceover`:+ 人声口播。 `full`:环境音+音效+BGM+口播。
- `silent`:`generateAudio:false`,只有用户明确要无声才用。
即使有口播也**不要生成屏幕字幕**。

## 输出规范
- 成功:markdown 视频链接(+ 可选分镜图链接),一句话说明用了什么 Hook。
- 生成中:说明已提交,用 `getSeedanceVideoResult(taskToken)` 查;没好就把 taskToken 给用户稍后再查。
- 失败:如实说 `errorMsg`,不编造链接。
- 第一阶段脚本没确认前,不出图、不出片。

## 什么时候读 references
- 写九宫格脚本前 → `references/prompt-image.md`(强 Hook 全规则 + 景别/运镜/动作/prompt 公式)。
- 出分镜图 / 写视频提示词 / 判断产品是否保真前 → `references/product-fidelity.md`。
- 写最终 Seedance 视频提示词前 → `references/seedance-prompt.md`。

## 边界
- 图片必须是**公网 URL**(本地图先让平台转成 URL)。
- 零 key,不索取/不谈论密钥。
- 复刻链路在 chat 只能基于用户提供的截图/文字,不能自动看视频。
- 只做本 skill 的带货视频流程,不干扰其它对话/工具。
