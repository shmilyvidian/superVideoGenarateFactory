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


# 独立实现,与 seedance_submit.py 一致。两个脚本各自独立分发/运行(Codex 逐个调用),
# 刻意不共享内部模块,保持单文件可移植。
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
