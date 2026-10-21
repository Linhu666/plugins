---
name: codex-offline-voice
description: Install, diagnose, control, or uninstall the local Codex offline voice assistant that starts when the user long-presses the Codex composer.
---

# Codex Offline Voice

Use this skill when the user asks to install, start, pause, diagnose, inspect, or uninstall the local Codex offline voice input helper.

The plugin cannot itself attach to the Codex composer DOM. A local Windows helper performs mouse hit-testing and offline speech recognition. Never claim that this plugin alone can intercept the composer.

## Resolve paths

- Resolve the plugin root as the parent of the directory containing this `SKILL.md`, then its parent.
- The management scripts are under `<plugin-root>/scripts/`.
- The installed helper is `%LOCALAPPDATA%\CodexOfflineVoice\App\CodexOfflineVoice.exe`.

## Install

Run:

```powershell
powershell -ExecutionPolicy Bypass -File "<plugin-root>\scripts\install.ps1"
```

The installer copies the packaged helper and creates a startup shortcut that runs `CodexOfflineVoice.exe --watch-codex`. The lightweight watcher starts the tray helper only while a visible Codex window exists and stops it after Codex closes. It is safe to run repeatedly.

## Status

Run:

```powershell
powershell -ExecutionPolicy Bypass -File "<plugin-root>\scripts\status.ps1"
```

Report whether the process is running, whether the model exists, the startup shortcut state, and the current config.

## Diagnose a point

Run the installed helper with the screen coordinate under investigation:

```powershell
& "$env:LOCALAPPDATA\CodexOfflineVoice\App\CodexOfflineVoice.exe" --diagnose-point 120,340
```

The result must show an `Edit` or `Document` UIA control owned by `ChatGPT.exe` or `Codex.exe`. If not, the long-press will not trigger.

## Pause, resume, or exit

Use the tray menu. The helper exposes no keyboard shortcut by design. Recording feedback is provided by rising/falling audio cues, a bottom-center click-through overlay that never takes focus, and tray icon colors; no bottom-right Windows notification balloon is used.

## Uninstall

Run:

```powershell
powershell -ExecutionPolicy Bypass -File "<plugin-root>\scripts\uninstall.ps1"
```

Add `-KeepData` to preserve configuration and logs. Do not manually delete unrelated Codex directories.

## Privacy

The helper applies high-pass filtering, an adaptive energy gate, and chunked Silero VAD before the packaged sherpa-onnx ASR model. It has no cloud transcription request. Do not add a cloud fallback without explicit user approval.
