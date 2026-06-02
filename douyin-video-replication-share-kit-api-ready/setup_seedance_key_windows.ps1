$ErrorActionPreference = "Stop"

$CodexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$SecretDir = Join-Path $CodexDir "secrets"
$SecretFile = Join-Path $SecretDir "seedance.env"

New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null

$SecureKey = Read-Host "请输入你自己的 ARK_API_KEY（输入时不会显示）" -AsSecureString
$Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
try {
  $ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
  Write-Host "未输入 API key，已取消。" -ForegroundColor Red
  exit 1
}

$BaseUrl = Read-Host "ARK_BASE_URL（直接回车使用默认 https://ark.cn-beijing.volces.com）"
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = "https://ark.cn-beijing.volces.com"
}

$Model = Read-Host "SEEDANCE_MODEL（直接回车使用默认 doubao-seedance-2-0-260128）"
if ([string]::IsNullOrWhiteSpace($Model)) {
  $Model = "doubao-seedance-2-0-260128"
}

$Content = @(
  "ARK_API_KEY=$ApiKey",
  "ARK_BASE_URL=$BaseUrl",
  "SEEDANCE_MODEL=$Model"
)

Set-Content -Path $SecretFile -Value $Content -Encoding UTF8

Write-Host "已保存到本机私密配置：$SecretFile" -ForegroundColor Green
Write-Host "不要把这个文件上传到 GitHub、发给别人或放进压缩包。"
