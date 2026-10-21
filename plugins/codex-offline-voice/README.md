# Codex Offline Voice

完全离线的 Codex 语音输入助手。用户按住 Codex 输入框约 200 ms 后开始录音，松开鼠标后停止录音，本地模型完成转写并把文字粘贴到当前光标位置。

## 特点

- 不需要键盘快捷键。
- 开始录音时播放上升双音，松开鼠标时播放下降双音。
- 随 Codex 可见窗口自动启动，Codex 关闭后自动停止助手。
- 录音和转写时显示底部居中悬浮状态条，不显示右下角系统通知弹窗。
- 悬浮窗鼠标穿透、不会抢走 Codex 输入焦点。
- 不调用云端识别接口。
- 使用高通滤波、能量门控和 Silero VAD 过滤低音量环境噪声。
- 不保存原始录音。
- 不自动发送消息。
- 使用官方 sherpa-onnx Paraformer Small 中文 int8 模型，支持中英混说和多种中文口音。
- 空闲时不占用音频设备，不进行识别推理。

## 技术边界

Codex 插件 API 不能拦截输入框鼠标事件，因此本插件负责管理和诊断，真正的长按监听由本地 Windows 助手完成。助手使用 Win32 窗口/进程/底部输入区快速判定，并用专用 UI Automation 线程提供诊断，避免高 DPI 和鼠标钩子线程导致误判。

## 使用方法

1. 安装插件并运行 `scripts/install.ps1`。
2. 安装后由后台监护器自动等待；Codex 打开时助手才启动并驻留托盘，Codex 关闭后自动停止。
3. 在 Codex 输入框内按住鼠标左键约 200 ms。
4. 开始说话，说完后松开鼠标。
5. 等待“正在本地转写”，文字会自动粘贴到 Codex 输入框。
6. 助手不会按 Enter，确认后由你自行发送。

## 诊断

查看安装状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\status.ps1
```

检查任意屏幕坐标的 UI Automation 控件：

```powershell
& "$env:LOCALAPPDATA\CodexOfflineVoice\App\CodexOfflineVoice.exe" --diagnose-point 120,340
```

只有命中 `Edit` 或 `Document` 控件，且所属进程为 `ChatGPT.exe` 或 `Codex.exe` 时才会触发。

## 配置

配置文件位于 `%LOCALAPPDATA%\CodexOfflineVoice\config.json`。默认配置：

```json
{
  "hold_ms": 200,
  "max_record_seconds": 60,
  "sample_rate": 16000,
  "threads": 2,
  "auto_paste": true,
  "restore_clipboard": true,
  "audio_cues": true,
  "noise_filter": true,
  "vad_threshold": 0.45,
  "min_voice_rms_dbfs": -50.0,
  "input_device": null
}
```

## 卸载

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

保留配置和历史数据：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1 -KeepData
```

## 从源码构建

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download-models.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

## 开发验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m codex_voice --transcribe-file .\tests\fixtures\zh_16k.wav
```
