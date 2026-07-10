$ErrorActionPreference = "Stop"

$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CodexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$Src = Join-Path $PackageDir "douyin-video-replication"
$DestRoot = Join-Path $CodexDir "skills"
$Dest = Join-Path $DestRoot "douyin-video-replication"

function Fail($Message) {
  Write-Host "安装失败：$Message" -ForegroundColor Red
  exit 1
}

if (-not (Test-Path (Join-Path $Src "SKILL.md"))) {
  Fail "找不到 douyin-video-replication\SKILL.md"
}

foreach ($Required in @("references", "scripts", "agents")) {
  if (-not (Test-Path (Join-Path $Src $Required))) {
    Fail "缺少 douyin-video-replication\$Required"
  }
}

New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null

if (Test-Path $Dest) {
  $Backup = "$Dest.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
  Move-Item -Path $Dest -Destination $Backup
  Write-Host "已备份旧版本：$Backup"
}

Copy-Item -Path $Src -Destination $Dest -Recurse
Get-ChildItem -Path $Dest -Filter ".DS_Store" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$PythonCandidates = @("py", "python", "python3")
$Python = $null
foreach ($Candidate in $PythonCandidates) {
  try {
    & $Candidate --version *> $null
    if ($LASTEXITCODE -eq 0) {
      $Python = $Candidate
      break
    }
  } catch {
  }
}

if (-not $Python) {
  Fail "找不到 Python。请先安装 Python 3，并确保 py 或 python 命令可用。"
}

& $Python -m py_compile `
  (Join-Path $Dest "scripts\extract_copy_review_frames.py") `
  (Join-Path $Dest "scripts\seedance_submit.py") `
  (Join-Path $Dest "scripts\xborder_image.py")
if ($LASTEXITCODE -ne 0) {
  Fail "Python 脚本语法检查失败"
}

$TmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("douyin-skill-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
try {
  $RefImage = Join-Path $TmpDir "ref.png"
  $OutDir = Join-Path $TmpDir "out"
  $PngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
  [System.IO.File]::WriteAllBytes($RefImage, [Convert]::FromBase64String($PngBase64))

  & $Python (Join-Path $Dest "scripts\seedance_submit.py") `
    --prompt "电商产品短视频测试，不提交，只检查请求格式。" `
    --reference-image $RefImage `
    --output-dir $OutDir `
    --duration 4 `
    --resolution 480p `
    --dry-run *> $null

  if ($LASTEXITCODE -ne 0) {
    Fail "Seedance 请求格式 dry-run 失败"
  }

  if (-not (Test-Path (Join-Path $OutDir "request.redacted.json"))) {
    Fail "没有生成 dry-run 请求预览"
  }

  $GridOutDir = Join-Path $TmpDir "grid-out"
  & $Python (Join-Path $Dest "scripts\seedance_submit.py") `
    --prompt "九宫格分镜直出视频测试，不提交，只检查请求格式。" `
    --reference-image $RefImage `
    --reference-mode grid-storyboard `
    --output-dir $GridOutDir `
    --duration 9 `
    --resolution 480p `
    --dry-run *> $null

  if ($LASTEXITCODE -ne 0) {
    Fail "九宫格直出请求格式 dry-run 失败"
  }

  if (-not (Test-Path (Join-Path $GridOutDir "request.redacted.json"))) {
    Fail "九宫格直出没有生成 dry-run 请求预览"
  }
} finally {
  Remove-Item -Path $TmpDir -Recurse -Force -ErrorAction SilentlyContinue
}

try {
  & ffmpeg -version *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "已检测到 ffmpeg。"
  }
} catch {
  Write-Host "提醒：没有检测到 ffmpeg。主流程可以安装，但本地视频抽帧会受影响。"
}

Write-Host "视频和图片生成均通过 X-Border 中转调用，无需配置 API key。"
Write-Host "中转地址默认 https://n11-server.lfy071.workers.dev；可通过 XBORDER_RELAY_URL 覆盖。"

Write-Host ""
Write-Host "安装和自检通过。" -ForegroundColor Green
Write-Host "请重启 Codex，然后在 Codex 里使用 `$douyin-video-replication。"
