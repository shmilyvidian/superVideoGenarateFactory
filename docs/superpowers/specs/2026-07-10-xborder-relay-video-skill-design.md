# douyin-video-replication 走 X-Border 中转改造设计

- 日期:2026-07-10
- 状态:设计已与用户确认,待 spec review
- 涉及仓库:`superVideoGenarateFactory`(skill 本体,主交付)、`X-Border`(n11-server Worker 中转 + 市场注册)

## 1. 背景与目标

`douyin-video-replication` 是一个 Codex 短视频生成 skill,当前:

- **视频**:`scripts/seedance_submit.py` 用用户自己的 `ARK_API_KEY` 直连火山方舟 Seedance 2.0(`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`),key 由用户用 `setup_seedance_key.sh` 写到本机 `~/.codex/secrets/seedance.env`。
- **分镜图**:SKILL.md 指示 Codex 用**内置 image2** 出九宫格分镜图,没有脚本。

**目标**:模型能力(Seedance 视频 + 九宫格分镜图)全部改走 X-Border 的 n11-server Cloudflare Worker 中转;provider key(ARK / Replicate)只存在 Worker 端,用户零 key 配置;完全替换旧的 ARK_API_KEY 直连路径;并把 skill 注册到 X-Border 市场。

参考对象是 X-Border 现有的图片中转(俗称 "xborder-images"):`xborderAiImage` 服务 → `POST /image/ecom/edit`(n11-server Worker,内部走 Replicate,`REPLICATE_API_TOKEN` 只在 Worker 侧持有),同步返回图片 URL。

## 2. 硬约束

1. **不影响已有 MCP skill / 工具功能**(用户明确要求)。具体:
   - `/image/ecom/edit` 的入参改动必须对现有单 string `image` 完全向后兼容;现有 `generateImage` MCP 工具和 `packages/api-server/src/services/xborderAiImage.ts` 零改动、行为不变。
   - 不改动、不复用 LinkFox 视频链路(`generateImageToVideo` 等 MCP 工具)。
   - 市场注册只**新增**一行 skill 记录,不改动、不迁移已注册的 skill / MCP。
   - 新增的 Worker 路由与 binding 均为**加法**,不触碰既有路由(`/image/*`、`/shein`、`/temu`、`/noon`、`/n11`、`/mercado`、`/ai`、`/text`、`/category`、`/site`)。
2. provider key(ARK_API_KEY / REPLICATE_API_TOKEN)永不下发到客户端、永不出现在 SKILL.md / 脚本 / 提交 / 输出。
3. 客户端**不加鉴权**(与现有 xborder-images 一致,靠 URL 混淆)。
4. 保留 Seedance 2.0 全部语义:`audio_mode`(silent/ambient/music/voiceover/full)、`reference_image` role、`ratio 9:16`、`duration`、`resolution`、`product-lock` 等。

## 3. 架构与数据流

```
Codex skill (用户机)
  │  分镜图: POST {relay}/image/ecom/edit
  │          { image:[data-uri...], prompt, model:"seedream-4.5", seedreamOptions:{aspect_ratio:"9:16"} }
  │  视频:   POST {relay}/video/seedance/tasks       (create → {id})
  │          GET  {relay}/video/seedance/tasks/{id}  (poll → {status, content:{video_url,...}})
  ▼
n11-server Worker
  ├─ REPLICATE_API_TOKEN ─▶ Replicate (seedream-4.5 / nano-banana-pro)
  └─ ARK_API_KEY ─────────▶ 火山方舟 Seedance 2.0 (/api/v3/contents/generations/tasks)
  ▲
  客户端无鉴权(URL 混淆)
```

- 视频产物 `video_url` / `last_frame_url` 是公开 URL,skill 直接下载,不经过 key。
- 依赖是流水线式:Worker 先就绪 → skill 改调用 → 注册市场。单 spec、分 3 阶段实现。

中转基址:
- 生产:`https://n11-server.lfy071.workers.dev`
- 测试:`https://n11-server-test.lfy071.workers.dev`

## 4. 组件设计

### 4.1 X-Border n11-server Worker

文件:`packages/n11-server/src/{index.ts,type.ts,image/ecom.ts}`、`wrangler.jsonc`。

**A1. 新增 Seedance 视频中转** —— 新建 `src/video/seedance.ts`(Hono `Router<{Bindings:AppBindings}>`),在 `src/index.ts` 挂 `app.route("/video", videoRouter)`:

- `POST /video/seedance/tasks`
  - 读 body(skill 端已构建好的完整 Seedance payload:`model, content[], ratio, duration, resolution, generate_audio, watermark, seed?, return_last_frame?`)。
  - 转发到 `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`,头 `Authorization: Bearer ${c.env.ARK_API_KEY}` + `Content-Type: application/json`。
  - 原样透传 Ark 响应(`{ id, ... }`)与状态码。
- `GET /video/seedance/tasks/:id`
  - 转发 GET 到 `.../tasks/{id}`,带同样的 Bearer 头,原样透传 `{ status, content:{ video_url, last_frame_url }, ... }`。
- 缺 `ARK_API_KEY` → `500 { error: "ARK_API_KEY not configured" }`(与现有 `REPLICATE_API_TOKEN` 处理一致)。
- Worker 是**薄代理**:不重构 payload,不注入业务逻辑;model 默认值仍由 skill 决定(`doubao-seedance-2-0-260128`)。

**A2. 图片中转多参考图扩展** —— 改 `src/image/ecom.ts`:

- `ZEcomEditSchema.image`:`z.string().min(1)` → `z.union([z.string().min(1), z.array(z.string().min(1)).min(1)])`(已支持 base64/data-URI,现在也支持数组;单 string 仍合法 = 向后兼容)。
- `buildModelInput`:把 `image_input: [image]` 改成 `image_input: Array.isArray(image) ? image : [image]`(nano-banana-pro / seedream-4.5 两分支;qwen-edit-multiangle 分支只用单图,取 `Array.isArray(image)?image[0]:image` 保持原样)。
- 目的:同一次出图能传"产品图 + 上一帧",保住九宫格人物/产品一致性。

**bindings / 部署**:

- `src/type.ts` 的 `AppBindings` 加 `ARK_API_KEY: string;`。
- 密钥注入:`wrangler secret put ARK_API_KEY`(prod)+ `wrangler secret put ARK_API_KEY --env test`。不写进 `wrangler.jsonc` 的 `vars`。
- 本地开发:`.dev.vars` 加 `ARK_API_KEY=...`。

### 4.2 skill(superVideoGenarateFactory)

根目录:`douyin-video-replication-share-kit-api-ready/`,skill 目录:`.../douyin-video-replication/`。

**B1. 视频脚本** `scripts/seedance_submit.py`:

- `DEFAULT_BASE_URL` → 中转基址,来源顺序:`--base-url` > `XBORDER_RELAY_URL` 环境变量 > 烘焙默认生产 URL(`https://n11-server.lfy071.workers.dev`)。
- `TASKS_PATH` → `/video/seedance/tasks`。
- 删除:`ARK_API_KEY` 读取/校验、`--env-file`、`load_env_file`、`DEFAULT_ENV_FILE`、`Authorization` 头逻辑。
- 保留:payload 构建(`build_payload`/`build_lock_prefix`/`build_audio_prefix`)、轮询(`--poll`)、下载、`redacted_payload`、`audio_mode`、`--product-lock*`、`--reference-mode`、`--dry-run`。
- `request_json` 去掉 `api_key` 入参与 `Authorization` 头(中转无鉴权)。

**B2. 新增分镜图脚本** `scripts/xborder_image.py`:

- 入参:`--prompt/--prompt-file`、可多次的 `--reference-image`(本地文件 → data-URI,复用 `seedance_submit.py` 里 `image_to_data_url` 的实现,抽成共享 util 或复制)、`--model`(默认 `seedream-4.5`,因其支持显式 `aspect_ratio:9:16`)、`--scale`(默认 `9:16`)、`--output`、`--base-url`/`XBORDER_RELAY_URL`。
- 请求:`POST {relay}/image/ecom/edit`,body `{ image:[data-uri...], prompt, model, seedreamOptions:{aspect_ratio} }`(仅 seedream 传 seedreamOptions)。
- 解析 `{status,image}`,`status=="succeeded"` 时下载 `image` 到 `--output`,否则报错。

**B3. 删除旧 key 路径**:

- 删 `setup_seedance_key.sh`、`setup_seedance_key_windows.ps1`、`secrets/seedance.env.example`、`secrets/` 目录。
- 新增极简 `setup_xborder_relay.sh`(**可选**,仅当要覆盖默认中转域名时写 `XBORDER_RELAY_URL` 到 `~/.codex/secrets/xborder.env`;不含任何 key)。默认零配置即可用。

**B4. 文档/契约同步**:

- `SKILL.md`:所有"用户自己配置 API key / ARK_API_KEY / seedance.env / 私密 key"改为"走 X-Border 中转,零 key";分镜图步骤从"Codex 内置 image2"改为"调用 `scripts/xborder_image.py`,逐帧传产品图 +(可选)上一帧";视频步骤改中转。QC/重试/产品保真逻辑不变。
- `references/seedance-api.md`:改成中转契约文档(端点、请求/响应、无 key 说明)。
- `README.md`、`install.sh`、`install_windows.bat`、`install_windows.ps1`、`check_install.sh`:去掉配 key 步骤,改中转说明。
- `tests/`:改契约测试——断言脚本指向中转路径、不再要求 `ARK_API_KEY`、分镜图脚本请求体形状正确。

### 4.3 注册到 X-Border 市场

用市场既有机制(`packages/api-server/src/services/market-store.ts` + admin oRPC `packages/api-server/src/rpc/market.ts`,表 `market_skills` / `market_skill_versions`):

- 走 **`registerSkillFromGitHub`**(`source='github'`,GitHub 快照 snapshot-zip 成 version;与市场里 anthropics/skills 的方式一致)。这是我推荐并默认采用的方式(用户已 ok 整体设计)。
- 需要 `MARKET_ADMIN_USER_IDS` 含操作者 userId(developer/admin)才能注册。
- 只新增一行 skill,不动既有记录。

## 5. 中转 HTTP 契约(精确)

**视频 create** —— `POST {relay}/video/seedance/tasks`
```json
// request(skill 构建,原 Ark payload)
{ "model":"doubao-seedance-2-0-260128", "content":[{"type":"text","text":"..."},
  {"type":"image_url","image_url":{"url":"data:image/...;base64,..."},"role":"reference_image"}],
  "ratio":"9:16", "duration":15, "resolution":"720p", "generate_audio":true, "watermark":false }
// response(透传 Ark)
{ "id":"cgt-xxxxx" }
```

**视频 poll** —— `GET {relay}/video/seedance/tasks/{id}`
```json
{ "status":"succeeded", "content":{ "video_url":"https://...", "last_frame_url":"https://..." } }
```

**分镜图** —— `POST {relay}/image/ecom/edit`
```json
// request
{ "image":["data:image/png;base64,...(产品图)","data:image/png;base64,...(上一帧)"],
  "prompt":"...", "model":"seedream-4.5", "seedreamOptions":{ "aspect_ratio":"9:16" } }
// response
{ "status":"succeeded", "image":"https://replicate.delivery/...", "model":"seedream-4.5" }
```

## 6. 错误处理

- Worker:缺 key → 500 明确报错;上游(Ark / Replicate)非 2xx → 透传状态码 + detail;异常 → `500 { error, message }`(与现有 ecom 分支一致)。
- skill:中转 5xx / 超时 → 抛错并保留 `request.redacted.json`(不含 key);轮询超时沿用现有 `--timeout`/`TimeoutError`;分镜图 `status != succeeded` → 报错并给出 detail。

## 7. 向后兼容 / 非回归(MCP 约束落地)

- **`/image/ecom/edit` 兼容**:union 后单 string 仍是合法输入且 `image_input` 结果不变 → 现有 `xborderAiImage.ts` / `generateImage` MCP 工具无需改、行为不变。加一条单测锁死"单 string 入参 → `image_input:[image]`"。
- **新路由隔离**:`/video/seedance/*`、`ARK_API_KEY` binding 均为新增,不与既有路由 / binding 冲突。
- **LinkFox 不动**:视频改造只在 Worker + skill,不触碰 api-server 的 LinkFox 视频 MCP 工具。
- **市场只增不改**:注册是插入一行,既有 skill/MCP 记录、install pipeline 不变。

## 8. 测试

- Worker:`src/video/seedance.ts` 单测(mock `fetch` 到 Ark,断言转发头/路径/透传);`ecom.ts` 多图 schema 单测(数组 + 单 string 两种入参 → `image_input` 正确)。
- skill:更新 `tests/test_route_contract.py` / `test_seedance_audio_contract.py` / `test_prompt_image_contract.py`——断言中转路径、无 `ARK_API_KEY` 依赖、分镜图脚本请求体形状。
- 手工 E2E(用户机):跑一次 dry-run + 一次低成本真实出图/出片,确认中转链路通。

## 9. 安全

- provider key 只在 Worker env / `.dev.vars`,永不进仓库 / 客户端。
- skill 侧不再持有任何 key;`request.redacted.json` 继续对 base64 图片打码。
- 中转无客户端鉴权是已知取舍(URL 混淆);若日后需限流/计费,再走 api-server 组织 token 方案(本次范围外)。

## 10. 实现阶段

1. **Phase 1 — Worker 中转**:`ecom.ts` 多图扩展 + `src/video/seedance.ts` 新路由 + `AppBindings`/`wrangler` secret + 单测。部署 test 环境验证。
2. **Phase 2 — skill 改造**:`seedance_submit.py` 改中转 + 新增 `xborder_image.py` + 删旧 key 路径 + 文档/install/测试同步。对 test 中转跑通。
3. **Phase 3 — 市场注册**:`registerSkillFromGitHub` 注册 skill;确认市场列表出现且可安装。

## 11. 范围外

- LinkFox 视频链路、api-server `generateImage`/`generateImageToVideo` 行为改动。
- 中转客户端鉴权 / 计费 / 限流。
- 市场的 UI / 安装管线改动(只做注册)。

## 12. 待确认项

- 生产中转 URL 烘焙默认值用 `https://n11-server.lfy071.workers.dev`(来自 `.env.production`)——确认可作为 skill 默认基址。
- 市场注册采用 `registerSkillFromGitHub`(GitHub 快照)——默认采用,如需改本地 zip 上传(`createSkillWithZip`)请在 review 时指出。
