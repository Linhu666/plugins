param(
    [switch]$KeepData
)

$ErrorActionPreference = 'Stop'
$dataRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'CodexOfflineVoice'))
$localRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA)
if (-not $dataRoot.StartsWith($localRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside LocalAppData: $dataRoot"
}

Get-Process -Name 'CodexOfflineVoice' -ErrorAction SilentlyContinue | Stop-Process -Force
$startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$shortcutPath = Join-Path $startupDir 'Codex Offline Voice.lnk'
if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
}

if (Test-Path -LiteralPath $dataRoot) {
    if ($KeepData) {
        $appTarget = Join-Path $dataRoot 'App'
        if (Test-Path -LiteralPath $appTarget) {
            Remove-Item -LiteralPath $appTarget -Recurse -Force
        }
    } else {
        Remove-Item -LiteralPath $dataRoot -Recurse -Force
    }
}
Write-Output 'Codex Offline Voice uninstalled.'
