param(
    [switch]$SkipModel
)

$ErrorActionPreference = 'Stop'
$pluginRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $pluginRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment not found: $python"
}

$runtimeRoot = Join-Path $pluginRoot 'runtime'
$distRoot = Join-Path $runtimeRoot 'app'
$workRoot = Join-Path $runtimeRoot 'build'
$specRoot = Join-Path $runtimeRoot 'spec'
$modelSource = Join-Path $runtimeRoot 'models'
New-Item -ItemType Directory -Force -Path $distRoot, $workRoot, $specRoot | Out-Null

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name CodexOfflineVoice `
    --paths (Join-Path $pluginRoot 'src') `
    --distpath $distRoot `
    --workpath $workRoot `
    --specpath $specRoot `
    --collect-all sherpa_onnx `
    --collect-all uiautomation `
    --hidden-import sounddevice `
    --hidden-import pystray._win32 `
    --hidden-import pynput.mouse._win32 `
    (Join-Path $pluginRoot 'app_entry.py')

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$appDir = Join-Path $distRoot 'CodexOfflineVoice'
if (-not $SkipModel) {
    if (-not (Test-Path -LiteralPath $modelSource)) {
        throw "Model directory not found: $modelSource"
    }
    $modelTarget = Join-Path $appDir 'models'
    New-Item -ItemType Directory -Force -Path $modelTarget | Out-Null
    Copy-Item -Path (Join-Path $modelSource '*') -Destination $modelTarget -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $pluginRoot 'README.md') -Destination $appDir -Force
Set-Content -LiteralPath (Join-Path $appDir 'VERSION.txt') -Value '0.1.0' -Encoding utf8
Write-Output "Built: $(Join-Path $appDir 'CodexOfflineVoice.exe')"
