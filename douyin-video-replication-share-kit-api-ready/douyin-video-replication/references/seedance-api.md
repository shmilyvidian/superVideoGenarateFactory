# X-Border 中转 API 契约

模型经 X-Border 中转调用,零 key。用户无需配置任何 Provider 密钥,无需申请 Volcano Ark 账号。

中转 Worker 地址:`https://n11-server.lfy071.workers.dev`

可通过环境变量 `XBORDER_RELAY_URL` 或脚本参数 `--base-url` 覆盖默认地址。

---

## 视频生成接口

### 创建任务

```
POST {relay}/video/seedance/tasks
```

请求体与原 Seedance 2.0 content 格式相同(文本 + 图片 reference_image 列表);中转 Worker 在服务端注入 Provider key,客户端无需传 `Authorization` header。

### 查询任务

```
GET {relay}/video/seedance/tasks/{id}
```

轮询直至 `status` 变为 `succeeded`(或失败);中转 Worker 透传 Ark 任务状态。

---

## 分镜图生成接口

```
POST {relay}/image/ecom/edit
```

- 默认模型:`seedream-4.5`
- 推荐比例:`--scale 9:16`
- 支持多个 `--reference-image`(产品图 + 可选上一帧)

---

## Reference Image 顺序(视频)

普通复刻链路:

1. 产品图 1
2. 产品图 2
3. 产品图 3(若有)
4. 更多产品图(若有)
5. 当前段分镜图

prompt 里应明确说明图片顺序。产品图是产品外观的唯一来源,分镜图只锁构图和场景。

---

## 示例命令

### 分镜图生成(逐帧调用 xborder_image.py)

```bash
python3 scripts/xborder_image.py \
  --prompt "产品白底展示图，突出瓶身曲线" \
  --reference-image inputs/product_images/product_front.jpg \
  --scale 9:16 \
  --output outputs/storyboard_images/frame_01.png
```

加上前一帧作参考(保持风格连续性):

```bash
python3 scripts/xborder_image.py \
  --prompt "手持产品特写，展示瓶盖细节" \
  --reference-image inputs/product_images/product_front.jpg \
  --reference-image outputs/storyboard_images/frame_01.png \
  --scale 9:16 \
  --output outputs/storyboard_images/frame_02.png
```

覆盖中转地址:

```bash
XBORDER_RELAY_URL=https://my-relay.example.workers.dev \
python3 scripts/xborder_image.py --prompt "..." --reference-image product.jpg --output frame.png
```

### 视频提交(seedance_submit.py,无 --env-file)

普通复刻:

```bash
python3 scripts/seedance_submit.py \
  --prompt-file outputs/seedance_video_prompts.md \
  --reference-image inputs/product_images/4X6A0367.JPG \
  --reference-image inputs/product_images/4X6A0400.JPG \
  --reference-image outputs/storyboard_images/storyboard_01.png \
  --reference-note "@图片1-2=产品图，@图片3=分镜图。产品图锁外观，分镜图只锁镜头结构。" \
  --output-dir outputs/seedance \
  --duration 15 \
  --ratio 9:16 \
  --resolution 720p \
  --audio-mode ambient \
  --poll
```

九宫格直出:

```bash
python3 scripts/seedance_submit.py \
  --prompt-file outputs/nine_grid_seedance_prompt.md \
  --reference-image inputs/storyboard_grid.png \
  --reference-mode grid-storyboard \
  --reference-note "@图片1=用户提供的3x3九宫格分镜图，按从上到下、从左到右读取。" \
  --output-dir outputs/seedance \
  --duration 9 \
  --ratio 9:16 \
  --resolution 720p \
  --audio-mode full \
  --dry-run
```

覆盖中转地址:

```bash
XBORDER_RELAY_URL=https://my-relay.example.workers.dev \
python3 scripts/seedance_submit.py \
  --prompt "测试" \
  --reference-image frame.png \
  --output-dir out \
  --dry-run
```

先 dry-run 确认请求格式,再去掉 `--dry-run` 正式提交。

---

## 声音配置

通过 `--audio-mode` 控制:

- `silent`:关闭生成音频
- `ambient`(默认):真实环境音 + 动作音效,无人声,无背景音乐
- `music`:环境音 + 动作音效 + 背景音乐
- `voiceover`:环境音 + 动作音效 + 人声口播
- `full`:环境音 + 动作音效 + 背景音乐 + 人声口播

有参考音频时使用 `--reference-audio-url`:

```bash
python3 scripts/seedance_submit.py \
  --prompt-file outputs/seedance_video_prompts.md \
  --reference-image outputs/storyboard_images/frame_01.png \
  --reference-audio-url "https://example.com/reference-music.mp3" \
  --output-dir outputs/seedance \
  --duration 9 \
  --audio-mode full \
  --audio-instruction "女生音色，轻快广告音乐，保留真实动作音效。" \
  --dry-run
```

---

## 身份细节缺失分镜的处理

如果生成分镜图中产品身份细节缺失/模糊/错位,但用户仍想测试 Seedance 出片:

- 不要将该分镜标记为产品保真通过。
- 通过 `scripts/seedance_submit.py` 的默认行为在 prompt 前置通用产品外观锁定块。
- 对需要更强措辞的产品使用 `--product-lock` 或 `--product-lock-file`。
- Seedance prompt 中明确声明分镜图里的产品细节错误不得被继承。
- 最终视频产品身份/logo QC 仍是 P0 硬门槛。

脚本默认前置通用产品锁定块,除非加 `--no-product-lock-prefix`。对身份敏感产品不要关闭此开关。

---

## 九宫格直出参考

同样走中转,无需 key。使用 `--reference-mode grid-storyboard`。详见 `references/grid-to-video-workflow.md`。
