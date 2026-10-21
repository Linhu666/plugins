param()

$ErrorActionPreference = 'Stop'
$pluginRoot = Split-Path -Parent $PSScriptRoot
$modelRoot = Join-Path $pluginRoot 'runtime\models'
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$paraAsset = 'https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/assets/155854908'
$vadAsset = 'https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/assets/271935959'
$paraArchive = Join-Path $env:TEMP 'sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2'
$vadTarget = Join-Path $modelRoot 'silero_vad.onnx'
New-Item -ItemType Directory -Force -Path $modelRoot | Out-Null

& $curl --retry 3 --retry-all-errors -sS -L -m 300 -H 'User-Agent: Codex' -H 'Accept: application/octet-stream' $paraAsset -o $paraArchive
if ($LASTEXITCODE -ne 0) { throw 'Paraformer download failed' }
tar -xjf $paraArchive -C $modelRoot
if ($LASTEXITCODE -ne 0) { throw 'Paraformer extraction failed' }

& $curl --retry 3 --retry-all-errors -sS -L -m 60 -H 'User-Agent: Codex' -H 'Accept: application/octet-stream' $vadAsset -o $vadTarget
if ($LASTEXITCODE -ne 0) { throw 'Silero VAD download failed' }

$paraModel = Join-Path $modelRoot 'sherpa-onnx-paraformer-zh-small-2024-03-09\model.int8.onnx'
$expectedPara = '3EF6C19369B912F7CAF3CEF8E545C5CCD1A33D9D7EC792A46668DC41C4B229EC'
$expectedVad = '9E2449E1087496D8D4CABA907F23E0BD3F78D91FA552479BB9C23AC09CBB1FD6'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $paraModel).Hash -ne $expectedPara) { throw 'Paraformer hash mismatch' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $vadTarget).Hash -ne $expectedVad) { throw 'Silero VAD hash mismatch' }
Remove-Item -LiteralPath $paraArchive -Force -ErrorAction SilentlyContinue
Write-Output "Models ready: $modelRoot"
