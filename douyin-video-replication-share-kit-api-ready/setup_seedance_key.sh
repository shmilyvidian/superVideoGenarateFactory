#!/usr/bin/env bash
set -euo pipefail

CODEX_DIR="${CODEX_HOME:-"$HOME/.codex"}"
SECRET_DIR="$CODEX_DIR/secrets"
SECRET_FILE="$SECRET_DIR/seedance.env"

mkdir -p "$SECRET_DIR"

printf "请输入你自己的 ARK_API_KEY（输入时不会显示）："
IFS= read -r -s api_key
printf "\n"

if [ -z "$api_key" ]; then
  echo "未输入 API key，已取消。"
  exit 1
fi

read -r -p "ARK_BASE_URL（直接回车使用默认 https://ark.cn-beijing.volces.com）：" base_url
read -r -p "SEEDANCE_MODEL（直接回车使用默认 doubao-seedance-2-0-260128）：" model

base_url="${base_url:-https://ark.cn-beijing.volces.com}"
model="${model:-doubao-seedance-2-0-260128}"

umask 077
{
  printf 'ARK_API_KEY=%s\n' "$api_key"
  printf 'ARK_BASE_URL=%s\n' "$base_url"
  printf 'SEEDANCE_MODEL=%s\n' "$model"
} > "$SECRET_FILE"

chmod 600 "$SECRET_FILE" 2>/dev/null || true

echo "已保存到本机私密配置：$SECRET_FILE"
echo "不要把这个文件上传到 GitHub、发给别人或放进压缩包。"
