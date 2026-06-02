#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="${CODEX_HOME:-"$HOME/.codex"}"
SRC="$PACKAGE_DIR/douyin-video-replication"
DEST_ROOT="$CODEX_DIR/skills"
DEST="$DEST_ROOT/douyin-video-replication"
SECRET_FILE="$CODEX_DIR/secrets/seedance.env"

fail() {
  echo "安装失败：$1" >&2
  exit 1
}

if [ ! -f "$SRC/SKILL.md" ]; then
  fail "找不到 douyin-video-replication/SKILL.md"
fi

for required in references scripts agents; do
  if [ ! -e "$SRC/$required" ]; then
    fail "缺少 douyin-video-replication/$required"
  fi
done

mkdir -p "$DEST_ROOT"

if [ -e "$DEST" ]; then
  backup="$DEST.backup.$(date +%Y%m%d-%H%M%S)"
  mv "$DEST" "$backup"
  echo "已备份旧版本：$backup"
fi

cp -R "$SRC" "$DEST"
find "$DEST" -name ".DS_Store" -delete 2>/dev/null || true

python_bin=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    python_bin="$candidate"
    break
  fi
done

if [ -z "$python_bin" ]; then
  fail "找不到 Python 3。请先安装 Python 3，再重新运行安装脚本。"
fi

"$python_bin" -m py_compile \
  "$DEST/scripts/extract_copy_review_frames.py" \
  "$DEST/scripts/seedance_submit.py"

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
  --prompt "电商产品短视频测试，不提交，只检查请求格式。" \
  --reference-image "$tmp_dir/ref.png" \
  --output-dir "$tmp_dir/out" \
  --duration 4 \
  --resolution 480p \
  --dry-run >/dev/null

if [ ! -f "$tmp_dir/out/request.redacted.json" ]; then
  fail "Seedance 请求格式 dry-run 没有生成预览文件"
fi

"$python_bin" "$DEST/scripts/seedance_submit.py" \
  --prompt "九宫格分镜直出视频测试，不提交，只检查请求格式。" \
  --reference-image "$tmp_dir/ref.png" \
  --reference-mode grid-storyboard \
  --output-dir "$tmp_dir/grid-out" \
  --duration 9 \
  --resolution 480p \
  --dry-run >/dev/null

if [ ! -f "$tmp_dir/grid-out/request.redacted.json" ]; then
  fail "九宫格直出请求格式 dry-run 没有生成预览文件"
fi

if command -v ffmpeg >/dev/null 2>&1; then
  echo "已检测到 ffmpeg。"
else
  echo "提醒：没有检测到 ffmpeg。主流程可以安装，但本地视频抽帧会受影响。"
fi

if [ -f "$SECRET_FILE" ] && grep -q '^ARK_API_KEY=.' "$SECRET_FILE"; then
  echo "已检测到本机私密 Seedance API 配置：$SECRET_FILE"
else
  echo "未检测到 Seedance API key。可以先手动使用提示词出片；如需 API 自动出片，请运行 ./setup_seedance_key.sh。"
fi

echo ""
echo "安装和自检通过。"
echo "请重启 Codex，然后在 Codex 里使用：\$douyin-video-replication"
