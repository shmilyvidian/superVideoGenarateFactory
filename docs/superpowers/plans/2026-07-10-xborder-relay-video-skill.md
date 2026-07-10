# douyin-video-replication 走 X-Border 中转 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `douyin-video-replication` skill 的模型调用(Seedance 视频 + 九宫格分镜图)改走 X-Border n11-server Worker 中转,provider key 全部留在 Worker 侧,删除用户 ARK_API_KEY 直连路径,并注册到 X-Border 市场。

**Architecture:** 两个仓库。X-Border 的 n11-server(Cloudflare Worker,Hono)新增 `/video/seedance/*` 薄代理(挂 `ARK_API_KEY` 转发火山方舟)并把 `/image/ecom/edit` 扩展成多参考图;skill 的 Python 脚本改调这些中转端点。中转对客户端无鉴权(URL 混淆),对既有 MCP 工具/路由零影响。

**Tech Stack:** Cloudflare Workers + Hono + Zod + vitest(X-Border);Python 3 stdlib(`urllib`)+ unittest(skill)。

## Global Constraints

- 不影响已有 MCP skill/工具:`/image/ecom/edit` 单 string `image` 必须完全兼容;`generateImage` MCP 工具、`xborderAiImage.ts`、LinkFox 视频链路零改动。
- 新增 Worker 路由 / binding 均为加法,不动既有路由(`/image`、`/shein`、`/temu`、`/noon`、`/n11`、`/mercado`、`/ai`、`/text`、`/category`、`/site`)。
- provider key(`ARK_API_KEY` / `REPLICATE_API_TOKEN`)永不进仓库/客户端/SKILL.md/脚本/输出。
- 客户端不加鉴权。
- 保留 Seedance 2.0 全部语义:`audio_mode`、`reference_image` role、`ratio 9:16`、`duration`、`resolution`、`product-lock`。
- 生产中转基址:`https://n11-server.lfy071.workers.dev`;测试:`https://n11-server-test.lfy071.workers.dev`。
- 分镜图默认模型 `seedream-4.5`(支持显式 `aspect_ratio:9:16`)。
- 市场注册用 `registerSkillFromGitHub`(GitHub 快照),只新增一行。

---

## Part A — X-Border n11-server Worker

仓库:`/Users/shmilyvidian/code/X-Border`。所有 A 任务在该仓库新分支 `feat/seedance-relay` 上进行。测试跑在 `packages/n11-server` 下:`npm test`(= `vitest run`)。

### Task A1: `/image/ecom/edit` 多参考图扩展(向后兼容)

**Files:**
- Modify: `packages/n11-server/src/image/ecom.ts`(`ZEcomEditSchema` 第 38-44 行、`buildModelInput` 第 112-155 行,并 `export` schema)
- Test: `packages/n11-server/src/image/__tests__/ecom.test.ts`(create)

**Interfaces:**
- Produces: `buildModelInput(data)` 中 `data.image` 现可为 `string | string[]`;`image_input` 恒为数组;`qwen-edit-multiangle` 仍只用首图。`ZEcomEditSchema` 变为导出。

- [ ] **Step 1: 建分支**

Run(在 `/Users/shmilyvidian/code/X-Border`):
```bash
git checkout -b feat/seedance-relay
```

- [ ] **Step 2: 写失败测试**

Create `packages/n11-server/src/image/__tests__/ecom.test.ts`:
```ts
import { describe, it, expect } from 'vitest';
import { buildModelInput, ZEcomEditSchema } from '../ecom';

describe('ecom buildModelInput multi-image', () => {
  it('单 string image → image_input:[image](向后兼容)', () => {
    const input = buildModelInput({ image: 'u1', prompt: 'p', model: 'seedream-4.5' } as any);
    expect(input.image_input).toEqual(['u1']);
  });

  it('数组 image → image_input 原样传(nano-banana-pro)', () => {
    const input = buildModelInput({ image: ['u1', 'u2'], prompt: 'p', model: 'nano-banana-pro' } as any);
    expect(input.image_input).toEqual(['u1', 'u2']);
  });

  it('qwen-edit-multiangle 只用首图', () => {
    const input = buildModelInput({ image: ['u1', 'u2'], prompt: 'p', model: 'qwen-edit-multiangle' } as any);
    expect(input.image).toBe('u1');
  });
});

describe('ZEcomEditSchema union', () => {
  it('接受单 string image', () => {
    const r = ZEcomEditSchema.safeParse({ image: 'u1', prompt: 'p', model: 'seedream-4.5' });
    expect(r.success).toBe(true);
  });
  it('接受 string[] image', () => {
    const r = ZEcomEditSchema.safeParse({ image: ['u1', 'u2'], prompt: 'p', model: 'seedream-4.5' });
    expect(r.success).toBe(true);
  });
  it('拒绝空数组', () => {
    const r = ZEcomEditSchema.safeParse({ image: [], prompt: 'p', model: 'seedream-4.5' });
    expect(r.success).toBe(false);
  });
});
```

- [ ] **Step 3: 跑测试确认失败**

Run(在 `packages/n11-server`):
```bash
npm test -- src/image/__tests__/ecom.test.ts
```
Expected: FAIL(`buildModelInput`/`ZEcomEditSchema` 未导出或数组分支不符)。

- [ ] **Step 4: 改实现**

In `packages/n11-server/src/image/ecom.ts`,把 `ZEcomEditSchema` 定义改为(并加 `export`):
```ts
export const ZEcomEditSchema = z.object({
  image: z.union([z.string().min(1), z.array(z.string().min(1)).min(1)]), // URL/base64,单个或数组
  prompt: z.string(),
  model: z.enum(["nano-banana-pro", "qwen-edit-multiangle", "seedream-4.5"]),
  options: ZAngleChangeOptions.optional(),
  seedreamOptions: ZSeedreamOptions.optional(),
});
```
把 `buildModelInput` 改为:
```ts
export function buildModelInput(data: EcomEditInput): Record<string, any> {
  const { image, prompt, model, options } = data;
  const images = Array.isArray(image) ? image : [image];
  const firstImage = images[0];

  switch (model) {
    case "nano-banana-pro":
      return { prompt, image_input: images, aspect_ratio: "match_input_image" };

    case "qwen-edit-multiangle":
      return {
        image: firstImage,
        prompt: prompt || "",
        rotate_degrees: options?.rotate_degrees ?? 0,
        vertical_tilt: options?.vertical_tilt ?? 0,
        move_forward: options?.move_forward ?? 0,
        use_wide_angle: options?.use_wide_angle ?? false,
        go_fast: true,
        lora_scale: 1.25,
        aspect_ratio: "match_input_image",
        output_format: "webp",
        output_quality: 95,
      };

    case "seedream-4.5":
      return {
        prompt,
        image_input: images,
        size: data.seedreamOptions?.size ?? "2K",
        aspect_ratio: data.seedreamOptions?.aspect_ratio ?? "match_input_image",
        max_images: data.seedreamOptions?.max_images ?? 1,
      };

    default:
      throw new Error(`Unknown model: ${model}`);
  }
}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `npm test -- src/image/__tests__/ecom.test.ts`
Expected: PASS(6 项)。

- [ ] **Step 6: 全量回归(确保没弄坏既有测试)**

Run: `npm test`
Expected: 既有测试全绿。

- [ ] **Step 7: 提交**

```bash
git add packages/n11-server/src/image/ecom.ts packages/n11-server/src/image/__tests__/ecom.test.ts
git commit -m "feat(n11): ecom/edit 支持多参考图(单 string 向后兼容)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task A2: Seedance 视频中转路由

**Files:**
- Create: `packages/n11-server/src/video/seedance.ts`
- Create: `packages/n11-server/src/video/index.ts`
- Test: `packages/n11-server/src/video/__tests__/seedance.test.ts`(create)

**Interfaces:**
- Produces: `POST /seedance/tasks`(转发 Ark create)、`GET /seedance/tasks/:id`(转发 Ark poll);`videoRouter` 默认导出,内部 `route("/seedance", seedanceRouter)`。缺 `ARK_API_KEY` → 500。

- [ ] **Step 1: 写失败测试**

Create `packages/n11-server/src/video/__tests__/seedance.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import seedanceRouter from '../seedance';

const ENV = { ARK_API_KEY: 'test-ark-key' } as any;

describe('seedance relay', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('POST /tasks 带 Bearer 转发 Ark 并透传 body', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 'cgt-1' }), { status: 200 }),
    );
    const res = await seedanceRouter.request('/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'doubao-seedance-2-0-260128', content: [] }),
    }, ENV);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ id: 'cgt-1' });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-ark-key');
  });

  it('GET /tasks/:id 转发 Ark', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'succeeded' }), { status: 200 }),
    );
    const res = await seedanceRouter.request('/tasks/cgt-1', { method: 'GET' }, ENV);
    expect(await res.json()).toEqual({ status: 'succeeded' });
    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt-1',
    );
  });

  it('缺 ARK_API_KEY → 500', async () => {
    const res = await seedanceRouter.request('/tasks', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    }, {} as any);
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ error: 'ARK_API_KEY not configured' });
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- src/video/__tests__/seedance.test.ts`
Expected: FAIL(`../seedance` 不存在)。

- [ ] **Step 3: 写实现**

Create `packages/n11-server/src/video/seedance.ts`:
```ts
import { Hono } from "hono";
import { AppBindings } from "../type";

// 火山方舟 Seedance 2.0。key 只在 Worker 侧(ARK_API_KEY),客户端不持有。
const ARK_BASE = "https://ark.cn-beijing.volces.com";
const TASKS_PATH = "/api/v3/contents/generations/tasks";

const seedanceRouter = new Hono<{ Bindings: AppBindings }>();

// 创建任务:透传 skill 构建好的 Seedance payload
seedanceRouter.post("/tasks", async (c) => {
  const arkKey = c.env.ARK_API_KEY;
  if (!arkKey) return c.json({ error: "ARK_API_KEY not configured" }, 500);

  const body = await c.req.text(); // 原样转发,不重构
  const res = await fetch(`${ARK_BASE}${TASKS_PATH}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${arkKey}`, "Content-Type": "application/json" },
    body,
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
});

// 查询任务
seedanceRouter.get("/tasks/:id", async (c) => {
  const arkKey = c.env.ARK_API_KEY;
  if (!arkKey) return c.json({ error: "ARK_API_KEY not configured" }, 500);

  const id = c.req.param("id");
  const res = await fetch(`${ARK_BASE}${TASKS_PATH}/${id}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${arkKey}` },
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
});

export default seedanceRouter;
```
Create `packages/n11-server/src/video/index.ts`:
```ts
import { Hono } from "hono";
import { AppBindings } from "../type";
import seedanceRouter from "./seedance";

const videoRouter = new Hono<{ Bindings: AppBindings }>();

// 挂载 Seedance 视频中转
videoRouter.route("/seedance", seedanceRouter);

export default videoRouter;
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npm test -- src/video/__tests__/seedance.test.ts`
Expected: PASS(3 项)。

- [ ] **Step 5: 提交**

```bash
git add packages/n11-server/src/video
git commit -m "feat(n11): 新增 Seedance 视频中转路由

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task A3: 挂载 `/video` + AppBindings + 部署配置

**Files:**
- Modify: `packages/n11-server/src/type.ts`(`AppBindings` 加 `ARK_API_KEY`)
- Modify: `packages/n11-server/src/index.ts`(import + `app.route("/video", videoRouter)`,约第 199-201 行附近)
- Modify: `packages/n11-server/.dev.vars.example`(加 `ARK_API_KEY=` 占位)
- Test: `packages/n11-server/src/video/__tests__/mount.test.ts`(create)

**Interfaces:**
- Consumes: A2 的 `videoRouter`。
- Produces: 主 app 暴露 `/video/seedance/tasks`。

- [ ] **Step 1: 写失败测试(app 级挂载)**

Create `packages/n11-server/src/video/__tests__/mount.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import app from '../../index';

const ENV = { ARK_API_KEY: 'k', OPENROUTER_API_KEY: 'x' } as any;

describe('/video 挂载', () => {
  beforeEach(() => vi.restoreAllMocks());
  it('POST /video/seedance/tasks 命中 seedance 路由', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 'cgt-x' }), { status: 200 }),
    );
    const res = await app.request('/video/seedance/tasks', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    }, ENV);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ id: 'cgt-x' });
  });
});
```
注:`src/index.ts` `export default { fetch, ... }`,而 `app` 是模块内 `const`。为可测试,Step 3 增加 `export { app };`(具名导出,不改默认导出行为)。

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- src/video/__tests__/mount.test.ts`
Expected: FAIL(`app` 未导出 / `/video` 未挂载 → 404)。

- [ ] **Step 3: 改实现**

In `packages/n11-server/src/type.ts`,`AppBindings` 加一行:
```ts
  // 火山方舟 Seedance(视频中转用),线上走 `wrangler secret put ARK_API_KEY`
  ARK_API_KEY: string;
```
In `packages/n11-server/src/index.ts`:
- 顶部与其它 router import 一起加:`import videoRouter from "./video";`
- 在 `app.route("/image", imageRouter);`(第 199 行)之后加:`app.route("/video", videoRouter);`
- 在 `const app = new Hono<{ Bindings: AppBindings }>();` 之后(或文件末尾 default export 之前)加具名导出:`export { app };`

In `packages/n11-server/.dev.vars.example` 追加一行:
```
ARK_API_KEY=
```

- [ ] **Step 4: 跑测试确认通过 + 全量回归**

Run: `npm test`
Expected: 新 mount 测试 PASS,既有测试全绿。

- [ ] **Step 5: 提交**

```bash
git add packages/n11-server/src/type.ts packages/n11-server/src/index.ts \
        packages/n11-server/.dev.vars.example packages/n11-server/src/video/__tests__/mount.test.ts
git commit -m "feat(n11): 挂载 /video 中转 + ARK_API_KEY binding

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task A4: 部署到 test 环境并验证(运行时操作,需用户 Cloudflare 凭证)

**Files:** 无代码;操作 + 记录。

- [ ] **Step 1: 注入 test 密钥**

Run(在 `packages/n11-server`,需交互输入 ARK key):
```bash
npx wrangler secret put ARK_API_KEY --env test
```

- [ ] **Step 2: 部署 test**

Run: `npm run deploy:test`
Expected: 部署到 `https://n11-server-test.lfy071.workers.dev`。

- [ ] **Step 3: 冒烟验证图片多参考图(单 string 仍通)**

Run:
```bash
curl -sS -X POST https://n11-server-test.lfy071.workers.dev/image/ecom/edit \
  -H 'Content-Type: application/json' \
  -d '{"image":"https://pub-9d51dc94160d4dfe9fefeee7a6e4e6ac.r2.dev/sample.png","prompt":"test","model":"seedream-4.5","seedreamOptions":{"aspect_ratio":"9:16"}}'
```
Expected: `{"status":"succeeded","image":"https://...","model":"seedream-4.5"}`(确认既有单图路径未被破坏)。

- [ ] **Step 4: 冒烟验证视频中转 create**

Run(payload 见 skill 端 dry-run 产物;此处仅验证 4xx/2xx 而非出片):
```bash
curl -sS -X POST https://n11-server-test.lfy071.workers.dev/video/seedance/tasks \
  -H 'Content-Type: application/json' \
  -d '{"model":"doubao-seedance-2-0-260128","content":[{"type":"text","text":"hi"}],"ratio":"9:16","duration":4,"resolution":"480p"}'
```
Expected: 返回含 `id` 的 JSON(Ark 已受理);若 Ark 报参数错也说明转发链路通。

## Part B — skill(superVideoGenarateFactory)

仓库:`/Users/shmilyvidian/code/superVideoGenarateFactory`,分支 `feat/xborder-relay-video-skill`(已存在)。skill 根:`douyin-video-replication-share-kit-api-ready/douyin-video-replication/`。测试:`python3 -m unittest discover -s douyin-video-replication-share-kit-api-ready/douyin-video-replication/tests -p "test_*.py" -v`。

### Task B1: `seedance_submit.py` 改走中转、去 key

**Files:**
- Modify: `.../scripts/seedance_submit.py`(常量第 23-29 行、`request_json` 第 113-127 行、`main` 第 303-327 行、`parse_args` 里 `--env-file`/`--base-url`)
- Test: `.../tests/test_relay_contract.py`(create)

**Interfaces:**
- Produces: `resolve_base_url(args)`(顺序 `--base-url` > `XBORDER_RELAY_URL` > 默认生产 URL);`TASKS_PATH = "/video/seedance/tasks"`;`build_task_url(base, id?)` 拼中转路径;`request_json(method, url, payload=None)`(无 api_key 参数)。

- [ ] **Step 1: 写失败测试**

Create `.../tests/test_relay_contract.py`:
```python
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import seedance_submit as ss  # noqa: E402

ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc"
    b"\xff\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


class RelayContractTest(unittest.TestCase):
    def test_tasks_path_is_relay_video_route(self):
        self.assertEqual(ss.TASKS_PATH, "/video/seedance/tasks")

    def test_default_base_url_is_prod_relay(self):
        self.assertEqual(ss.DEFAULT_BASE_URL, "https://n11-server.lfy071.workers.dev")

    def test_build_task_url_uses_relay(self):
        base = "https://n11-server.lfy071.workers.dev"
        self.assertEqual(
            ss.build_task_url(base), base + "/video/seedance/tasks"
        )
        self.assertEqual(
            ss.build_task_url(base, "cgt-1"), base + "/video/seedance/tasks/cgt-1"
        )

    def test_no_ark_api_key_symbols(self):
        src = (SCRIPTS / "seedance_submit.py").read_text(encoding="utf-8")
        self.assertNotIn("ARK_API_KEY", src)
        self.assertNotIn("seedance.env", src)

    def test_dry_run_needs_no_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ref = tmp_path / "grid.png"
            ref.write_bytes(ONE_PIXEL_PNG)
            out = tmp_path / "out"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "seedance_submit.py"),
                 "--prompt", "t", "--reference-image", str(ref),
                 "--reference-mode", "grid-storyboard",
                 "--output-dir", str(out), "--duration", "9",
                 "--resolution", "480p", "--dry-run"],
                check=False, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out / "request.redacted.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run(在 skill 根):
```bash
python3 tests/test_relay_contract.py -v
```
Expected: FAIL(`TASKS_PATH` 仍是 `/api/v3/...`,`ARK_API_KEY` 仍在源码)。

- [ ] **Step 3: 改实现**

In `.../scripts/seedance_submit.py`:

(a) 常量区(约 23-29 行)替换为:
```python
DEFAULT_BASE_URL = "https://n11-server.lfy071.workers.dev"
TASKS_PATH = "/video/seedance/tasks"
DEFAULT_MODEL = "doubao-seedance-2-0-260128"
SUCCESS_STATUSES = {"succeeded", "completed"}
FINAL_STATUSES = SUCCESS_STATUSES | {"failed", "cancelled", "expired"}
RUNNING_STATUSES = {"queued", "running", "pending", "processing"}
```
(删除 `DEFAULT_ENV_FILE`。)

(b) 删除 `load_env_file` 函数(约 61-72 行)。

(c) `request_json` 去掉 key(约 113-127 行):
```python
def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from X-Border relay: {detail}") from exc
```

(d) `parse_args`:删除 `--env-file` 参数;`--base-url` 的 default 改为:
```python
    parser.add_argument(
        "--base-url",
        default=os.environ.get("XBORDER_RELAY_URL", DEFAULT_BASE_URL),
        help=f"X-Border relay base URL. Defaults to XBORDER_RELAY_URL or {DEFAULT_BASE_URL}.",
    )
```

(e) `main`(约 303-327 行)删除 env-file/key 逻辑,改为:
```python
def main() -> int:
    args = parse_args()

    payload = build_payload(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "request.redacted.json").write_text(
        json.dumps(redacted_payload(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.dry_run:
        print(f"Dry run written: {args.output_dir / 'request.redacted.json'}")
        return 0

    create_result = request_json("POST", build_task_url(args.base_url), payload)
```
并把后续所有 `request_json("GET", build_task_url(args.base_url, task_id), api_key)` 改为去掉 `api_key` 参数。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 tests/test_relay_contract.py -v`
Expected: PASS(5 项)。

- [ ] **Step 5: 提交**

```bash
git add douyin-video-replication-share-kit-api-ready/douyin-video-replication/scripts/seedance_submit.py \
        douyin-video-replication-share-kit-api-ready/douyin-video-replication/tests/test_relay_contract.py
git commit -m "feat(skill): seedance_submit 改走 X-Border 中转、去除 ARK_API_KEY

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task B2: 新增分镜图脚本 `xborder_image.py`

**Files:**
- Create: `.../scripts/xborder_image.py`
- Test: `.../tests/test_xborder_image_contract.py`(create)

**Interfaces:**
- Produces: CLI `--prompt/--prompt-file`、可多次 `--reference-image`、`--model`(默认 `seedream-4.5`)、`--scale`(默认 `9:16`)、`--output`、`--base-url`/`XBORDER_RELAY_URL`、`--dry-run`;`build_body(args)` 返回 `{image:[data-uri...], prompt, model, seedreamOptions?}`;`image_to_data_url(path)`(与 seedance_submit 同实现)。

- [ ] **Step 1: 写失败测试**

Create `.../tests/test_xborder_image_contract.py`:
```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"

ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc"
    b"\xff\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


class XBorderImageContractTest(unittest.TestCase):
    def test_dry_run_body_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            p1 = tmp_path / "prod.png"; p1.write_bytes(ONE_PIXEL_PNG)
            p2 = tmp_path / "prev.png"; p2.write_bytes(ONE_PIXEL_PNG)
            out = tmp_path / "frame.png"
            body_file = tmp_path / "request.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "xborder_image.py"),
                 "--prompt", "cell 1",
                 "--reference-image", str(p1),
                 "--reference-image", str(p2),
                 "--model", "seedream-4.5",
                 "--scale", "9:16",
                 "--output", str(out),
                 "--dry-run", "--dump-body", str(body_file)],
                check=False, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            body = json.loads(body_file.read_text(encoding="utf-8"))
            self.assertEqual(len(body["image"]), 2)
            self.assertTrue(body["image"][0].startswith("data:image/"))
            self.assertEqual(body["model"], "seedream-4.5")
            self.assertEqual(body["seedreamOptions"]["aspect_ratio"], "9:16")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 tests/test_xborder_image_contract.py -v`
Expected: FAIL(脚本不存在)。

- [ ] **Step 3: 写实现**

Create `.../scripts/xborder_image.py`:
```python
#!/usr/bin/env python3
"""Generate one storyboard frame through the X-Border image relay.

No API key on the client: the relay (n11-server Worker) holds REPLICATE_API_TOKEN.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://n11-server.lfy071.workers.dev"
EDIT_PATH = "/image/ecom/edit"
DEFAULT_MODEL = "seedream-4.5"
SEEDREAM_ASPECT = {"1:1", "16:9", "9:16"}


def image_to_data_url(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > 30 * 1024 * 1024:
        raise ValueError(f"image is larger than 30 MB: {path}")
    mime, _ = mimetypes.guess_type(path.name)
    if not mime or not mime.startswith("image/"):
        suffix = path.suffix.lower().lstrip(".")
        if suffix == "jpg":
            suffix = "jpeg"
        mime = f"image/{suffix or 'png'}"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime.lower()};base64,{encoded}"


def build_body(args: argparse.Namespace) -> dict[str, Any]:
    prompt = args.prompt or args.prompt_file.read_text(encoding="utf-8").strip()
    images = [image_to_data_url(p) for p in args.reference_image]
    body: dict[str, Any] = {"image": images, "prompt": prompt, "model": args.model}
    if args.model == "seedream-4.5" and args.scale in SEEDREAM_ASPECT:
        body["seedreamOptions"] = {"aspect_ratio": args.scale}
    return body


def request_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from X-Border relay: {detail}") from exc


def download_file(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as resp:
        out_path.write_bytes(resp.read())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a storyboard frame via X-Border relay.")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--reference-image", type=Path, action="append", default=[])
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=["seedream-4.5", "nano-banana-pro", "qwen-edit-multiangle"])
    parser.add_argument("--scale", default="9:16", choices=["1:1", "16:9", "9:16"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url",
                        default=os.environ.get("XBORDER_RELAY_URL", DEFAULT_BASE_URL))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dump-body", type=Path, help="Write the request body JSON (for tests).")
    args = parser.parse_args()
    if not args.prompt and not args.prompt_file:
        parser.error("provide --prompt or --prompt-file")
    if not args.reference_image:
        parser.error("provide at least one --reference-image")
    for p in args.reference_image:
        if not p.exists():
            parser.error(f"reference image does not exist: {p}")
    return args


def main() -> int:
    args = parse_args()
    body = build_body(args)
    if args.dump_body:
        args.dump_body.parent.mkdir(parents=True, exist_ok=True)
        args.dump_body.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.dry_run:
        print(f"Dry run: would POST {args.base_url}{EDIT_PATH} with {len(body['image'])} image(s)")
        return 0

    result = request_json(f"{args.base_url}{EDIT_PATH}", body)
    if result.get("status") != "succeeded" or not result.get("image"):
        raise RuntimeError(f"relay did not return image: {result}")
    download_file(result["image"], args.output)
    print(f"Saved frame: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 tests/test_xborder_image_contract.py -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add douyin-video-replication-share-kit-api-ready/douyin-video-replication/scripts/xborder_image.py \
        douyin-video-replication-share-kit-api-ready/douyin-video-replication/tests/test_xborder_image_contract.py
git commit -m "feat(skill): 新增 xborder_image.py 分镜图走中转(多参考图)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task B3: 删除旧 key 路径 + 同步 SKILL.md / references / README / install

**Files:**
- Delete: `.../setup_seedance_key.sh`、`.../setup_seedance_key_windows.ps1`、`.../secrets/seedance.env.example`、`.../secrets/`
- Modify: `.../douyin-video-replication/SKILL.md`、`.../references/seedance-api.md`、`.../README.md`、`.../install.sh`、`.../install_windows.bat`、`.../install_windows.ps1`、`.../check_install.sh`、顶层 `README.md`
- Modify: `.../tests/test_route_contract.py`(去掉对 ARK key 的断言,加中转断言)

**Interfaces:**
- Produces: SKILL.md 分镜图步骤引用 `scripts/xborder_image.py`;无任何 `ARK_API_KEY` / `seedance.env` / `setup_seedance_key` 残留。

- [ ] **Step 1: 写失败测试(仓库级契约)**

追加到 `.../tests/test_route_contract.py` 新方法(或建 `test_no_key_leftovers.py`):
```python
    def test_no_key_setup_leftovers(self):
        kit_root = SKILL_ROOT.parents[0]  # share-kit 根
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        api_md = (SKILL_ROOT / "references" / "seedance-api.md").read_text(encoding="utf-8")
        self.assertNotIn("ARK_API_KEY", skill_md)
        self.assertNotIn("ARK_API_KEY", api_md)
        self.assertNotIn("seedance.env", skill_md)
        self.assertIn("xborder_image.py", skill_md)
        self.assertFalse((kit_root / "setup_seedance_key.sh").exists())
        self.assertFalse((kit_root / "secrets").exists())
```
(`SKILL_ROOT.parents[0]` = `douyin-video-replication` 上一级 = share-kit 根;若层级不符按实际调整为 `SKILL_ROOT.parent`。)

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_route_contract -v`(在 skill 根,或 `python3 tests/test_route_contract.py -v`)
Expected: FAIL(仍存在 setup 脚本 / ARK_API_KEY / 未引用 xborder_image.py)。

- [ ] **Step 3: 删文件**

Run(在 share-kit 根 `douyin-video-replication-share-kit-api-ready`):
```bash
git rm setup_seedance_key.sh setup_seedance_key_windows.ps1 secrets/seedance.env.example
rmdir secrets 2>/dev/null || true
```

- [ ] **Step 4: 改文档**

- `SKILL.md`:把「用户自己配置 API key / ARK_API_KEY / `$HOME/.codex/secrets/seedance.env` / 私密 key / 不配 key 则只出 prompt」等表述,统一改为「模型经 X-Border 中转,零 key」;把「Use Codex's built-in GPT image/image2」及分镜图生成步骤改为「逐帧调用 `scripts/xborder_image.py`,传产品图 +(可选)上一帧」;Seedance 提交步骤引用中转,不再提「confirm ARK_API_KEY exists」。
- `references/seedance-api.md`:重写为中转契约——端点 `POST {relay}/video/seedance/tasks`、`GET .../tasks/:id`、图片 `POST {relay}/image/ecom/edit`;删除 Volcano Ark 直连/`Authorization: Bearer $ARK_API_KEY`/`seedance.env`/「recipient must use their own account」等;`XBORDER_RELAY_URL` 覆盖说明;示例命令用 `seedance_submit.py`(无 `--env-file`)与 `xborder_image.py`。
- `README.md`(顶层 + share-kit):把「配置 Seedance API Key」章节替换为「零 key,走 X-Border 中转;可选 `XBORDER_RELAY_URL` 覆盖」。
- `install.sh` / `install_windows.bat` / `install_windows.ps1` / `check_install.sh`:删掉配 key 步骤与对 `setup_seedance_key` / `seedance.env` 的引用;`check_install.sh` 改为校验 `scripts/seedance_submit.py`、`scripts/xborder_image.py` 存在。

- [ ] **Step 5: 跑测试确认通过 + 全量回归**

Run(skill 根):
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
Expected: 全绿(含既有 `test_seedance_audio_contract.py` / `test_prompt_image_contract.py`;若它们断言了旧 key 文案,在本步一并改到中转措辞)。

- [ ] **Step 6: 提交**

```bash
git add -A douyin-video-replication-share-kit-api-ready README.md
git commit -m "refactor(skill): 删除 ARK key 配置路径,文档/install/测试改为 X-Border 中转

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

## Part C — 注册到 X-Border 市场

### Task C1: 用 `registerSkillFromGitHub` 注册 skill(运行时操作)

**Files:** 无代码改动(除非注册需补管理脚本)。依赖:`superVideoGenarateFactory` 已推到 GitHub 且含最新中转版 skill;操作者 userId 在 `MARKET_ADMIN_USER_IDS`。

- [ ] **Step 1: 推分支 / 合并到可注册的 ref**

Run(skill 根):`git push -u origin feat/xborder-relay-video-skill`(或合并到 main 后用 main)。

- [ ] **Step 2: 确认 admin 权限**

确认 api-server 环境 `MARKET_ADMIN_USER_IDS` 含你的 userId(否则 `rpc/market.ts` 的注册方法会被 `canManageMarket` 拒绝)。

- [ ] **Step 3: 调 `registerSkillFromGitHub` 注册**

通过 X-Border 市场管理入口(系统设置 → `/settings/market-management`,developer-only)或直接调 admin oRPC `market.registerSkillFromGitHub`,入参指向 `superVideoGenarateFactory` 仓库中 `douyin-video-replication` skill 路径,`source='github'` 快照 zip 成一个 version。
- 参考:`packages/api-server/src/services/market-store.ts:188 registerSkillFromGitHub`、`packages/api-server/src/rpc/market.ts`。

- [ ] **Step 4: 验证**

在市场列表确认新 skill 出现、可下载 zip(含 checksum)、一键「安装到 XBorder AI」可拉取;确认既有 skill/MCP 记录未受影响。

---

## Self-Review

**Spec coverage:**
- 4.1 Worker A1(多图)→ Task A1 ✅;A2(Seedance 路由)→ Task A2 ✅;bindings/wrangler → Task A3 + A4 ✅
- 4.2 skill B1(seedance_submit)→ Task B1 ✅;B2(xborder_image)→ Task B2 ✅;B3(删 key)+ B4(文档/测试)→ Task B3 ✅
- 4.3 市场注册 → Task C1 ✅
- 5 HTTP 契约 → A2/B1/B2 测试覆盖端点与形状 ✅
- 6 错误处理 → A2(缺 key 500)、B1/B2(HTTPError→RuntimeError)✅
- 7 非回归 → A1 单 string 兼容测试 + A3 全量回归 + C1 只增不改 ✅
- 8 测试 → 各 Task 内含 vitest / unittest ✅
- 9 安全 → 无 key on client(B1 去 key、`test_no_ark_api_key_symbols`)✅

**Placeholder scan:** 无 TBD/TODO;所有代码步骤含完整代码与命令。

**Type consistency:** `TASKS_PATH="/video/seedance/tasks"`、`EDIT_PATH="/image/ecom/edit"`、`build_task_url`、`build_body`、`image_to_data_url`、`buildModelInput`、`ZEcomEditSchema`、`videoRouter`/`seedanceRouter` 全程一致。

**已知需实现时核对的软点:**
- B3 Step 1 的 `SKILL_ROOT.parents[0]` 层级按实际目录深度确认(share-kit 根 vs skill 目录)。
- 既有 `test_seedance_audio_contract.py` / `test_prompt_image_contract.py` 若断言旧 key 文案,在 B3 Step 5 一并改。
