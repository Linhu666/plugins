$ErrorActionPreference = 'Stop'
$pluginRoot = Split-Path -Parent $PSScriptRoot
$dataRoot = Join-Path $env:LOCALAPPDATA 'CodexOfflineVoice'
$appTarget = Join-Path $dataRoot 'App'
$exe = Join-Path $appTarget 'CodexOfflineVoice.exe'
$model = Join-Path $appTarget 'models\sherpa-onnx-paraformer-zh-small-2024-03-09\model.int8.onnx'
$config = Join-Path $dataRoot 'config.json'
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Codex Offline Voice.lnk'
$processes = @(Get-Process -Name 'CodexOfflineVoice' -ErrorAction SilentlyContinue)
$watcherRunning = $false
$helperRunning = $false
try {
    $details = @(Get-CimInstance Win32_Process -Filter "Name='CodexOfflineVoice.exe'" -ErrorAction Stop)
    $watcherRunning = @($details | Where-Object { $_.CommandLine -match '--watch-codex' }).Count -gt 0
    $helperRunning = @($details | Where-Object { $_.CommandLine -notmatch '--watch-codex' }).Count -gt 0
} catch {
    $watcherRunning = $processes.Count -gt 0
    $helperRunning = $processes.Count -gt 1
}
$configValue = $null
if (Test-Path -LiteralPath $config) {
    try { $configValue = Get-Content -Raw -LiteralPath $config -Encoding utf8 | ConvertFrom-Json } catch { $configValue = $null }
}
[PSCustomObject]@{
    installed = Test-Path -LiteralPath $exe
    running = $processes.Count -gt 0
    processCount = $processes.Count
    watcherRunning = $watcherRunning
    helperRunning = $helperRunning
    modelPresent = Test-Path -LiteralPath $model
    configPresent = Test-Path -LiteralPath $config
    config = $configValue
    startupShortcut = Test-Path -LiteralPath $startup
    pluginRoot = $pluginRoot
} | ConvertTo-Json -Depth 6
