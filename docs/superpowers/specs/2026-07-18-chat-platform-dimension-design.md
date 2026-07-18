# chat 版视频 skill · 电商平台维度设计

- 日期：2026-07-18
- 范围：仅 `chat-skill/xborder-video-chat`（不动 Codex 版 replication）
- 目标：在 prompt 层引入「电商平台」维度，让同一套强 Hook 九宫格方法论按平台切换**语言/本地化、合规红线、视频规格、卖点心智**，覆盖 Temu / Noon / Amazon / Shein / Mercado / N11 六家 + 默认档 + 空白模板。
- 硬约束：对现有抖音用法**零回归**（不指定平台 = 默认档 = 现状）。

---

## 1. 核心概念

### 1.1 两个正交维度：platform × genre

- **platform（电商平台）**：决定语言/选角/合规/心智，以及各字段的**默认值**。
- **genre（输出用途）**：决定视频形态，二选一：
  - `social-ad`：9:16 竖屏、强 Hook 停滑点（前 3 格）、默认无字幕、快节奏 KOC/生活流。**= 现状抖音打法。**
  - `listing-demo`：方屏/横屏（默认 1:1，可 16:9）、弱 Hook（前 3 秒仍抓人但走「问题→产品价值」而非猎奇痛点）、允许功能 callout 字幕、产品演示/真实使用/信任背书为主。
- **九宫格骨架 Hook→Solution→Trust 在两种 genre 下都保留**；genre 只调 Hook 力度、比例、字幕策略、节奏。
- 每个平台档带一个 `默认 genre`。**genre 可被用户运行时覆盖**（如「Amazon 但走 Inspire 竖屏」→ `social-ad` + Amazon 合规）。
- **默认映射规则（底层是「货架电商 vs 内容电商」）**：
  - **货架电商**（人找货：Amazon / Temu / Noon / Shein / Mercado / N11）→ 默认 `listing-demo`（详情页/主图视频）。
  - **内容电商**（货找人：默认档抖音/TikTok、以后的 TikTok Shop）→ 默认 `social-ad`。
  - **站外引流/联盟投放**（如 Temu 联盟投 TikTok、Amazon Inspire/Sponsored Brands）→ 由用户一句话切 `social-ad` 覆盖。
  - 交叉是常态（货架平台要投社媒、内容平台有商品卡），所以 genre 独立于 platform、可覆盖，而不是焊死在平台上。

> 为什么 genre 必须是独立字段（不是给 Amazon 建两份档）：代码证据显示同一平台服务两种产出用途，且比例合规于下游发布链路——见 §4。

### 1.2 覆盖优先级（单点解析）

```
用户运行时明确指定  >  平台档案默认  >  全局默认（social-ad / 9:16 / 中英 / 欧美女性 / 禁字幕）
```

适用于所有可覆盖字段：**比例、genre、语言、时长、字幕开关、audio_mode**。平台档只是「省得每次问」的智能默认。

### 1.3 resolve-then-materialize（让「去硬编码」真正生效的关键机制）

这些文件是喂给 LLM 的 prompt，不是代码。若把具体值 `9:16` 换成「按平台档案」这种**悬空指针**，而生成那一步平台值没被物化进上下文，输出会退化。

因此：**SKILL 第 0 步一次性把优先级解析成一个具体的「本次运行参数」块**，贯穿全流程；所有 reference 引用这个已物化的块，**不再各自 re-resolve，也不留「按档案」指针**。

```
【本次运行参数】（第 0 步解析，贯穿全流程，优先级：用户 > 平台档 > 全局）
- 电商平台：<platform | 默认档>
- 输出用途 genre：<social-ad | listing-demo>
- 视频比例：<resolved ratio>   ← generateImage.scale 与 generateSeedanceVideo.aspectRatio 都用它；Kling 用它出起始图
- 文案语言：<lang>
- 人物选角：<casting>
- 字幕策略：<禁字幕 | 功能 callout | 阿英双语 | 潮流 caption …>
- audio_mode：<ambient | music | voiceover | full | silent>
- 时长：<秒>
- 合规红线：[通用红线 + 平台专属]
- 卖点心智 / Hook 力度：<…>
```

---

## 2. 工具真实能力（探索实锤，file:line 出自 X-Border 仓库）

| 工具 | 支持比例 | 默认 | 出处 |
|---|---|---|---|
| `generateImage`（seedream-4.5） | **1:1 / 16:9 / 9:16** | `1:1` | `packages/api-server/src/mcp/server.ts:342` |
| `generateSeedanceVideo` | **16:9 / 9:16 / 1:1 / 4:3 / 3:4** | `9:16` | `mcp/server.ts:417` |
| `generateKlingVideo` | **无比例参数**，继承起始图 | — | `mcp/server.ts:433-442` |

- Amazon 1:1/16:9、Temu 1:1/3:4/16:9 **全部原生支持**，无 API 风险。
- **Kling 比例落在生成起始图的 `generateImage.scale` 上**，Kling 调用本身无比例旋钮。
- **流水线对齐约束**：`generateImage` 只出 `1:1/16:9/9:16`（无 3:4/4:3），而 `generateSeedanceVideo` 能出 3:4/4:3。为保分镜图与视频比例一致，**listing-demo 默认比例统一取 `1:1`**（Amazon 可 16:9）——这也是 Temu `{1:1,3:4,16:9}` 与 generateImage 的交集里最稳的一档。若用户坚持要 3:4/4:3 视频，分镜图用最接近的 1:1，提示词里注明会重构边框。

---

## 3. 平台档案矩阵（`references/platform-profiles.md` 内容）

顶部放【通用红线】（所有平台继承）+ 覆盖优先级总则；每平台一节按统一 schema；末尾放空白模板。

### 3.1 通用红线（继承给所有平台）

- 禁虚构功效、禁医疗/治疗承诺。
- 禁绝对化：最/第一/唯一/保证/100%/永久/立刻见效，**及各目标语言等价词**。
- 禁第三方品牌 logo / 水印 / 台标——**注意与产品保真消歧**：保留的是**本产品自身**的 logo（产品身份），禁的是**别家品牌/平台水印**。
- 全部镜头遵守真实物理；不新增九宫格/脚本没有的镜头、场景、道具（继承现有规则）。

### 3.2 六平台 + 默认档

| 平台 | 默认 genre | 默认比例 | 语言 / 选角 | 字幕策略 | 平台专属合规（叠加通用红线） | 心智 · 卖点排序 |
|---|---|---|---|---|---|---|
| **默认（抖音/TikTok，内容电商）** | social-ad | 9:16 | 用户指定，默认中/英 · 欧美女性 | 禁字幕 | （仅通用红线） | 强 Hook 痛点驱动 · 停滑点 |
| **Temu** | **listing-demo** | **1:1**（可 3:4/16:9；**禁 9:16 入主图**） | 英(US)为主/多语 · 泛欧美多元亲民生活化 | 价值卖点/功能字幕可选 | 禁误导性紧迫感、禁虚假原价/折扣（EU DSA 监管收紧） | 极致低价 + 超值 + 实用 + 即时满足 |
| **Noon** | **listing-demo** | **1:1**（可 16:9） | 阿拉伯语(MSA)+英 · 中东海湾 · 女性 modest 得体 · RTL | **阿/英双语字幕友好**（功能点） | 禁暴露/酒精/猪肉/宗教冒犯/LGBT 暗示；斋月·开斋节可 seasonal | 生活方式 + 身份 + 品质正品 + 家庭 + 送礼 |
| **Amazon** | **listing-demo** | **1:1**（默认）或 16:9（A+/Sponsored Brands 常用） | 分站点语言 · 中性专业选角 | **功能 callout 字幕鼓励** | 最严：禁价格/促销/折扣/倒计时文字 · 禁 badge（Choice/BestSeller 仿冒）· 禁竞品对比贬低 · 禁站外引流 URL · 禁伪造评价背书 · 禁时效词(sale/free shipping) | 信任 + 参数规格 + 真实使用 + 评价心智 + 解决问题 |
| **Shein** | **listing-demo**（审美偏 social/试穿，货架里的例外） | **1:1**（试穿可切 9:16 竖版） | 英为主/多语 · 年轻潮流多元 | 潮流/试穿 caption、功能字幕允许 | 美妆禁医疗功效；按市场禁不当暴露 | 潮流 + 穿搭上身 + 氛围感 + 平价 + 上新 |
| **Mercado** | **listing-demo** | **1:1**（可 16:9） | 西语(墨/阿)/葡语(巴西) · 拉美形象 | 西/葡功能字幕允许 | 绝对化西葡等价词(el mejor/garantizado)；分期(cuotas)表述须真实合规 | 实用 + 家庭 + 性价比 + 可负担分期 |
| **N11** | **listing-demo** | **1:1**（可 16:9） | 土耳其语 · 土耳其/地中海形象 · 得体 | 土语功能字幕允许 | 土耳其广告法(Reklam Kurulu)；宗教文化尊重 | 性价比 + 家庭实用 + 正品信任 |

### 3.3 约束来源标注（避免把经验伪装成硬规则）

- **Temu 比例 = 代码强约束**：主图视频只收 `1:1 / 3:4 / 16:9`，9:16 会被发布链路预检拒绝（见 §4）。
- **其余平台的比例/字幕/合规 = 运营建议（平台惯例）**，非平台 API 强校验。档案里逐条标注来源。

### 3.4 空白模板

```
## <平台名>（<定位一句话>）
- 默认 genre：<social-ad | listing-demo>
- 语言/本地化：<目标语言｜人物选角｜审美基调｜文化 norms>
- 视频规格：<默认比例｜可选比例｜时长上限/黄金时长｜字幕策略>  （标注：代码强约束 / 运营建议）
- 合规红线：<在通用红线之上追加的平台专属禁区>
- 卖点心智：<受众心智 + 卖点排序>
- Hook 变体：<Hook 力度 + 该平台停滑点/演示打法；骨架仍 Hook→Solution→Trust>
```

---

## 4. 代码级证据：为什么 genre 与比例是「正确性必需」

X-Border 发布链路真实消费本 skill 产出的视频（Temu 主图视频注入），且强制比例：

- 常量 `TEMU_VIDEO_ALLOWED_RATIOS = ['1:1','3:4','16:9']` — `packages/api-server/src/workers/utils/videoSteps.ts:38`
- 强制预检（3 处）：`mastra/tools/apply-media-to-cleaned-product.ts:269`、`workers/utils/linkedMedia.ts:105`、`workers/clean-temu.ts:720`
- MCP 层警告：`mcp/server.ts:418`「若应用到 Temu 商品发布，必须用 1:1/3:4/16:9」

结论：Temu-listing 走 9:16 会被拒。**genre（用途）决定比例是否合规于下游发布**，故必须是独立可解析字段。仅 Temu 有此代码护栏；Noon/Shein/Mercado/N11 暂无对应常量。

---

## 5. 文件改动清单

### 5.1 新增
- `references/platform-profiles.md` — §3 全部内容（通用红线 + 优先级总则 + 六平台档 + 模板）。

### 5.2 修改
- `SKILL.md`
  1. 「三条链路」前加 **第 0 步：识别电商平台 + genre**，产出 §1.3 的「本次运行参数」块。识别策略：用户明说平台 → 直接用；提到跨境/电商但未指明哪家 → 问一次；**完全没提平台 → 静默走默认档，不打扰（保证零回归，现有抖音用户体验不变）**。
  2. 每条链路开头 **load `references/platform-profiles.md` 的对应平台节**（只 load 该节，省 token）。
  3. 工具调用去硬编码：`generateImage.scale`、`generateSeedanceVideo.aspectRatio` 改为读「运行参数.视频比例」；Kling 起始图同理。
  4. 「声音/输出规范/边界」补一句：语言与字幕遵循运行参数。
- `references/prompt-image.md`
  - persona「专注 TikTok/抖音」→「按运行参数的平台受众与审美」；人物「默认欧美女性」→「按运行参数选角」；prompt 公式里 `9:16` 与 `no subtitles` → 读运行参数（比例/字幕策略）；「夸张边界」段接【通用红线】+ 平台专属合规；Hook 自检加「Hook 力度按运行参数（social-ad 强 / listing-demo 弱）」。
- `references/seedance-prompt.md`
  - persona 去抖音化；「全局设定」的 `9:16 竖屏`、「禁字幕」→ 读运行参数；「强约束」段接【通用红线】+ 平台合规；口播语言按运行参数。
- `references/kling-prompt.md`
  - 明确 Kling 无比例参数，比例由起始图（`generateImage.scale`）决定；`禁字幕`/`绝对化` → 读运行参数字幕策略与【通用红线】。
- `references/product-fidelity.md`
  - **仅加一行消歧**：保留的是本产品自身 logo；第三方品牌 logo/水印按合规红线禁止。主体不动。

### 5.3 新增合规自检 gate
在「出图前」与「出片前」各插一个轻量自检：对照「运行参数.合规红线」逐条扫（尤其 listing-demo/Amazon：价格/促销/倒计时文字、第三方 logo/水印、绝对化、站外 URL、badge 仿冒）。命中 → 修正或不出片，**不硬出**。写进 SKILL.md 流程与 product-fidelity 相邻。

---

## 6. 验收标准

- **零回归**：无平台输入 → 运行参数 = 默认档 → 9:16 / 强 Hook / 无字幕 / 欧美女性 / 抖音 persona 原味，与现状**逐字一致**。默认档必须逐字保留现有 persona 风味。
- **货架六家默认 `listing-demo` / 1:1**；投社媒/联盟时用户显式切 `social-ad` / 9:16 才走竖屏强 Hook。
- **Temu**：产出比例 ∈ `{1:1,3:4,16:9}`，可过 `TEMU_VIDEO_ALLOWED_RATIOS` 预检；9:16 会被发布链路拒。
- **Amazon**：1:1（或 16:9）+ 功能字幕允许 + 无价格/促销/URL/badge。
- **Noon**：listing-demo/1:1 + 阿/英 + modest 选角 + 双语字幕 + 文化红线生效。
- **Shein**：listing-demo/1:1（试穿审美，可切 9:16 竖版）+ 语言/选角/合规按档案。
- **Mercado / N11**：listing-demo/1:1 + 语言/选角/字幕/合规按档案生效。
- 全平台：`generateImage.scale`、`generateSeedanceVideo.aspectRatio` 取值来自运行参数；Kling 起始图按运行参数比例出。
- 用户覆盖任一字段（比例/语言/时长/字幕/audio_mode/genre）时，覆盖生效。

---

## 7. 实现前置 / 风险

- scale/aspectRatio 支持已验证（§2），无阻塞。
- 合规红线是**软约束**（prompt + 自检 gate），除 Temu 比例外无平台 API 强校验；Amazon 合规最终仍需发布端/人工把关，skill 尽最大努力降风险。
- 「去硬编码」的成败全系于 §1.3 的运行参数块被正确物化并贯穿——这是实现重点，reference 里禁止残留悬空「按档案」指针。

---

## 8. 非目标（YAGNI）

- 不改 Codex 版 `xborder-video-replication`（本次只 chat）。
- 不给 Amazon 建两份档（用 genre 覆盖解决）。
- 不做平台 API 实时合规校验（除既有 Temu 比例护栏）。
- **不扩视频引擎**：保持 Seedance（多帧九宫格泳道，产品保真 P0 主力）+ Kling（单图 1080p 泳道）。中转站现仅接这两个（`packages/n11-server/src/video/`，Replicate 固定版本）。「引擎维度」与本次「平台维度」正交——扩引擎（候选：Veo 3.1 高端 listing-demo / MiniMax Hailuo 02 + Wan 2.5 低成本走量 / Runway Gen-4 可控演示，均在 Replicate、relay 加一条 router 即可）另开 spec，不进本次。
- 不加 Lazada / TikTok Shop / Ozon（留空白模板，按需照抄新增）。
- 不重写 `product-fidelity.md` 主体（仅加一行 logo 消歧）。
</content>
</invoke>
