param(
    [string]$SourceApp = ''
)

$ErrorActionPreference = 'Stop'
$pluginRoot = Split-Path -Parent $PSScriptRoot
if (-not $SourceApp) {
    $SourceApp = Join-Path $pluginRoot 'runtime\app\CodexOfflineVoice'
}
$SourceApp = [System.IO.Path]::GetFullPath($SourceApp)
$exeSource = Join-Path $SourceApp 'CodexOfflineVoice.exe'
if (-not (Test-Path -LiteralPath $exeSource)) {
    throw "Packaged executable not found: $exeSource"
}

$dataRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'CodexOfflineVoice'))
$appTarget = [System.IO.Path]::GetFullPath((Join-Path $dataRoot 'App'))
$localRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA)
if (-not $appTarget.StartsWith($dataRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to replace path outside CodexOfflineVoice data root: $appTarget"
}
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null

Get-Process -Name 'CodexOfflineVoice' -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path -LiteralPath $appTarget) {
    Remove-Item -LiteralPath $appTarget -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $appTarget | Out-Null
Copy-Item -Path (Join-Path $SourceApp '*') -Destination $appTarget -Recurse -Force

$exeTarget = Join-Path $appTarget 'CodexOfflineVoice.exe'
$startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
$shortcutPath = Join-Path $startupDir 'Codex Offline Voice.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exeTarget
$shortcut.Arguments = '--watch-codex'
$shortcut.WorkingDirectory = $appTarget
$shortcut.Description = 'Codex 离线语音输入'
$shortcut.Save()

Start-Process -FilePath $exeTarget -ArgumentList '--watch-codex' -WorkingDirectory $appTarget -WindowStyle Hidden
Write-Output "Installed: $exeTarget"
Write-Output "Startup shortcut: $shortcutPath"
