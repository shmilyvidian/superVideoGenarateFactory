#!/usr/bin/env python3
"""Submit a Seedance 2.0 video generation task through the relay (Replicate backend).

The relay forwards the request body verbatim as the Replicate `input` to
`bytedance/seedance-2.0`. No API key is required on the client side.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://n11-server.lfy071.workers.dev"
TASKS_PATH = "/video/seedance/tasks"
SUCCESS_STATUSES = {"succeeded"}
FINAL_STATUSES = SUCCESS_STATUSES | {"failed", "canceled"}
RUNNING_STATUSES = {"starting", "processing"}


GENERIC_PRODUCT_LOCK_PREFIX = """\
【通用产品外观硬约束】
产品外观唯一以产品参考图和本次产品专属约束为准。分镜图只用于参考镜头顺序、构图、人物/手部/身体局部动作、场景、光线和画面节奏，不用于参考或覆盖产品外观。
如果分镜图中的产品出现品类错误、形态错误、颜色/款式错误、比例不准、材质不准、数量错误、关键结构缺失、logo/标识/文字/花纹/吊坠/扣件/宝石/包装细节缺失或位置错误，全部视为分镜图误差，禁止继承。
所有镜头中的产品必须保持产品参考图里的真实品类、轮廓、结构、颜色、材质、纹理、比例、厚薄、边缘、连接处、包装/组合关系和可见关键识别细节。
凡是镜头看到产品参考图中应当可见的logo、标识、文字、图案、刻印、吊坠、宝石、扣件、接口、标签、纹理或其他关键识别细节，必须显示在正确物理表面，位置、大小、颜色、方向和透视随产品角度自然变化。
如果产品参考图本身没有logo或文字，禁止凭空生成logo、文字或品牌标识。只有当关键识别细节因镜头角度、遮挡、背面/非可见面、景深虚化或画面裁切而自然不可见时，才可以不显示。
禁止把关键识别细节移动到错误物理位置，禁止放到人物皮肤、衣服、鞋子、地面、背景、道具或错误包装上，禁止为了规避生成难度而删除、弱化、放大、缩小或强行摆正。
"""

GRID_STORYBOARD_PREFIX = """\
【九宫格分镜直出规则】
本次输入以用户提供的3x3九宫格分镜图和已确认的视频生成脚本为核心参考，不走竞品视频复刻拆解流程。
九宫格分镜图锁定9个镜头的读取顺序、构图、主体位置、场景、光线、人物/手部/产品动作、画面节奏和整体视觉风格。读取顺序固定为从上到下、从左到右。
视频生成脚本锁定每格镜头意图、卖点表达、口播/旁白节奏、情绪推进和转化路径。生成视频时必须逐格对应，不得跳格、重排、合并成不可辨认的新镜头，也不得新增九宫格和脚本中不存在的场景、道具、人物动作或产品呈现方式。
如果只提供九宫格图而没有单独产品图，产品外观以九宫格图中清晰可见的产品为准，不凭空替换品类、颜色、结构、包装、logo、标签、纹理或数量。
如果同时提供单独产品图或产品外观约束，则单独产品图和产品约束优先锁定产品外观；九宫格只锁镜头结构和画面节奏。
所有镜头必须符合真实物理世界逻辑：手指不能穿过产品，产品不能悬浮、变形、变色、变数量或在镜头间无故改变结构；光线、阴影、接触点、比例、重力、反射和运动连续性必须自然。
"""

AUDIO_MODE_PREFIXES = {
    "silent": "【声音配置】静音模式。不要生成环境音、动作音效、背景音乐、人声口播或旁白。",
    "ambient": "【声音配置】保留真实环境音和动作音效，例如脚步声、倒水声、开盖声、摇晃声、冰块碰撞声、包装摩擦声、产品接触声和空间氛围声；不要人声口播，不要背景音乐。",
    "music": "【声音配置】生成真实环境音、动作音效和轻快背景音乐；不要人声口播或旁白。背景音乐不能盖过关键动作音效。",
    "voiceover": "【声音配置】生成真实环境音、动作音效和人声口播/旁白；背景音乐不生成或仅保留极轻的铺底音乐。口播节奏必须贴合画面动作。",
    "full": "【声音配置】环境音、动作音效、背景音乐和人声口播全部允许。环境音要贴合画面动作，背景音乐要符合广告节奏，人声口播要清晰自然。",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_lock_prefix(args: argparse.Namespace) -> str:
    blocks: list[str] = []
    if args.reference_mode == "grid-storyboard":
        blocks.append(GRID_STORYBOARD_PREFIX.strip())
    elif args.inject_product_lock:
        blocks.append(GENERIC_PRODUCT_LOCK_PREFIX.strip())
    if args.product_lock:
        blocks.append("【本次产品专属约束】\n" + args.product_lock.strip())
    if args.product_lock_file:
        blocks.append("【本次产品专属约束】\n" + read_text(args.product_lock_file))
    return "\n\n".join(block for block in blocks if block)


def build_audio_prefix(args: argparse.Namespace) -> str:
    prefix = AUDIO_MODE_PREFIXES[args.audio_mode]
    if args.audio_instruction:
        prefix += "\n【用户声音补充要求】\n" + args.audio_instruction.strip()
    return prefix


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


def build_task_url(base_url: str, task_id: str | None = None) -> str:
    base = base_url.rstrip("/")
    if task_id:
        return f"{base}{TASKS_PATH}/{task_id}"
    return f"{base}{TASKS_PATH}"


def download_file(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as resp:
        out_path.write_bytes(resp.read())


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    prompt = args.prompt or read_text(args.prompt_file)
    audio_prefix = build_audio_prefix(args)
    lock_prefix = build_lock_prefix(args)
    if audio_prefix:
        prompt = audio_prefix + "\n\n" + prompt
    if lock_prefix:
        prompt = lock_prefix + "\n\n" + prompt
    if args.reference_note:
        prompt = args.reference_note.strip() + "\n\n" + prompt

    reference_images = [image_to_data_url(p) for p in args.reference_image]
    if reference_images:
        refs = " ".join(f"[Image{i + 1}]" for i in range(len(reference_images)))
        prompt = prompt + f"\n\n参考图顺序(产品图在前、分镜图在后):{refs}"

    payload: dict[str, Any] = {
        "prompt": prompt,
        "reference_images": reference_images,
        "aspect_ratio": args.ratio,
        "duration": args.duration,
        "resolution": args.resolution,
        "generate_audio": args.audio_mode != "silent",
    }
    if args.reference_audio_url:
        payload["reference_audios"] = args.reference_audio_url
    if args.seed is not None:
        payload["seed"] = args.seed
    return payload


def redacted_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clone = json.loads(json.dumps(payload, ensure_ascii=False))
    imgs = clone.get("reference_images", [])
    clone["reference_images"] = [
        (u.split(",", 1)[0] + ",<base64 omitted>")
        if isinstance(u, str) and u.startswith("data:image/")
        else u
        for u in imgs
    ]
    return clone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit and poll a Seedance 2.0 generation task.")
    parser.add_argument("--prompt-file", type=Path, help="Seedance prompt text file.")
    parser.add_argument("--prompt", help="Seedance prompt text.")
    parser.add_argument(
        "--reference-image",
        type=Path,
        action="append",
        default=[],
        help="Reference image path. Pass product images first, then storyboard image.",
    )
    parser.add_argument(
        "--reference-mode",
        default="replication",
        choices=["replication", "grid-storyboard"],
        help=(
            "How to interpret reference images. 'replication' expects product images first and storyboard last; "
            "'grid-storyboard' expects a user-provided 3x3 grid storyboard, with optional product images or locks."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for task status and downloaded video.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("XBORDER_RELAY_URL", DEFAULT_BASE_URL),
        help=f"X-Border relay base URL. Defaults to XBORDER_RELAY_URL or {DEFAULT_BASE_URL}.",
    )
    parser.add_argument("--ratio", default="9:16")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p", "4k"])
    parser.add_argument(
        "--audio-mode",
        default=os.environ.get("SEEDANCE_AUDIO_MODE", "ambient"),
        choices=["silent", "ambient", "music", "voiceover", "full"],
        help=(
            "Audio behavior. silent disables generated audio; ambient keeps environment/action sounds; "
            "music adds background music; voiceover adds narration; full allows environment, music, and voice."
        ),
    )
    parser.add_argument(
        "--audio-instruction",
        help="Optional custom audio direction, e.g. voice gender, music style, sound effects, or narration tone.",
    )
    parser.add_argument(
        "--reference-audio-url",
        action="append",
        default=[],
        help="Reference audio URL to pass as reference_audios. Can be provided multiple times.",
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument("--poll", action="store_true", help="Poll until the task finishes and download the video.")
    parser.add_argument("--poll-interval", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true", help="Write a redacted request preview without submitting.")
    parser.add_argument(
        "--product-lock",
        help="Optional product-specific appearance lock text, e.g. logo placement, pendant/clasp details, label details, or package structure.",
    )
    parser.add_argument(
        "--product-lock-file",
        type=Path,
        help="Optional text file containing product-specific appearance constraints generated from product images.",
    )
    parser.add_argument(
        "--no-product-lock-prefix",
        dest="inject_product_lock",
        action="store_false",
        help="Do not prepend the generic product appearance lock block.",
    )
    parser.set_defaults(inject_product_lock=True)
    parser.add_argument(
        "--reference-note",
        help="Optional short note mapping image order, e.g. '@图片1-3=产品图，@图片4=分镜图'.",
    )
    args = parser.parse_args()

    if not args.prompt and not args.prompt_file:
        parser.error("provide --prompt-file or --prompt")
    if not args.reference_image:
        parser.error("provide at least one --reference-image")
    for path in args.reference_image:
        if not path.exists():
            parser.error(f"reference image does not exist: {path}")
    if args.product_lock_file and not args.product_lock_file.exists():
        parser.error(f"product lock file does not exist: {args.product_lock_file}")
    if args.duration != -1 and not (4 <= args.duration <= 15):
        parser.error("Seedance duration must be -1 (auto) or between 4 and 15 seconds")
    return args


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
    task_id = create_result.get("id")
    if not task_id:
        raise RuntimeError(f"Seedance create response did not contain id: {create_result}")
    (args.output_dir / "create_response.json").write_text(
        json.dumps(create_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Seedance task created: {task_id}")

    if not args.poll:
        return 0

    deadline = time.time() + args.timeout
    last_status = None
    status_result: dict[str, Any] = {}
    while time.time() < deadline:
        status_result = request_json("GET", build_task_url(args.base_url, task_id))
        status_value = status_result.get("status")
        last_status = str(status_value).lower() if status_value is not None else None
        (args.output_dir / "status.json").write_text(
            json.dumps(status_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Seedance task status: {last_status}")
        if last_status in FINAL_STATUSES:
            break
        if last_status not in RUNNING_STATUSES:
            raise RuntimeError(f"Unexpected Seedance task status: {status_result}")
        time.sleep(args.poll_interval)
    else:
        raise TimeoutError(f"Seedance task did not finish within {args.timeout} seconds: {task_id}")

    if last_status not in SUCCESS_STATUSES:
        raise RuntimeError(f"Seedance task did not succeed: {status_result}")

    output = status_result.get("output")
    video_url = output if isinstance(output, str) else (output[0] if isinstance(output, list) and output else None)
    if not video_url:
        raise RuntimeError(f"Prediction succeeded but no output URL: {status_result}")
    out_video = args.output_dir / f"{task_id}.mp4"
    download_file(video_url, out_video)
    print(f"Downloaded video: {out_video}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
