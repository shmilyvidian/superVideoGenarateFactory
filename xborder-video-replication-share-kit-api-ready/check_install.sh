#!/usr/bin/env bash
set -euo pipefail

CODEX_DIR="${CODEX_HOME:-"$HOME/.codex"}"
DEST="$CODEX_DIR/skills/xborder-video-replication"

fail() {
  echo "检查失败：$1" >&2
  exit 1
}

[ -f "$DEST/SKILL.md" ] || fail "没有找到已安装的 SKILL.md：$DEST/SKILL.md"
[ -d "$DEST/references" ] || fail "缺少 references/"
[ -d "$DEST/scripts" ] || fail "缺少 scripts/"
[ -f "$DEST/scripts/seedance_submit.py" ] || fail "缺少 scripts/seedance_submit.py"
[ -f "$DEST/scripts/xborder_image.py" ] || fail "缺少 scripts/xborder_image.py"

python_bin=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    python_bin="$candidate"
    break
  fi
done

[ -n "$python_bin" ] || fail "找不到 Python"

"$python_bin" -m py_compile \
  "$DEST/scripts/extract_copy_review_frames.py" \
  "$DEST/scripts/seedance_submit.py" \
  "$DEST/scripts/xborder_image.py"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

"$python_bin" - "$tmp_dir/ref.png" <<'PY'
import base64
import pathlib
import sys

png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
pathlib.Path(sys.argv[1]).write_bytes(base64.b64decode(png))
PY

"$python_bin" "$DEST/scripts/seedance_submit.py" \
  --prompt "九宫格分镜直出视频测试，不提交，只检查请求格式。" \
  --reference-image "$tmp_dir/ref.png" \
  --reference-mode grid-storyboard \
  --output-dir "$tmp_dir/grid-out" \
  --duration 9 \
  --resolution 480p \
  --dry-run >/dev/null

[ -f "$tmp_dir/grid-out/request.redacted.json" ] || fail "九宫格直出请求格式 dry-run 没有生成预览文件"

echo "API key 状态：X-Border 中转模式，零 key，无需配置。"
echo "中转地址：${XBORDER_RELAY_URL:-https://n11-server.lfy071.workers.dev}"

if command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg 状态：已安装。"
else
  echo "ffmpeg 状态：未检测到；本地视频抽帧会受影响。"
fi

echo "安装检查通过。"
