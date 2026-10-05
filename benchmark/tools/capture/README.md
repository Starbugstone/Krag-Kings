# Engine showcase capture

`prepare_ffmpeg.py` downloads the SHA-256-pinned Windows FFmpeg 8.0.1 distributor archive into ignored `benchmark/local/capture/`. Python, network access and the `7z` command are required. The existing RTX 2060 driver passed a one-second NVENC synthetic encoder check with this version. FFmpeg 9.0.2 failed because it required a newer NVENC API. These capability checks are not game footage or performance measurements.

Launch one actual packaged engine demo in its showcase/wait mode under the shared heavy-task guard. Then run the recorder from a separate PowerShell process, passing the real game process ID:

```powershell
.\benchmark\tools\capture\Capture-Demo.ps1 `
  -Engine Unreal -GameProcessId <actual-game-pid> `
  -RuntimeLog .\benchmark\unreal\evidence\runtime.log `
  -StartFlag .\benchmark\unreal\evidence\showcase-start.flag `
  -EngineAudio .\benchmark\unreal\evidence\showcase-engine-audio.wav `
  -OutputDirectory .\benchmark\unreal\evidence\showcase-review-01
```

For Unity, supply its corresponding runtime log, gate and game-only WAV paths with `-Engine Unity`. The recorder waits for the scene's `SHOWCASE_READY` marker, starts client-area capture of the explicit game HWND, then writes the gate. It records the 72-second timeline, waits for `SHOWCASE_COMPLETE` and the exported engine-only WAV, and muxes an H.264/AAC MP4. It does not capture desktop/system/microphone audio or change OBS configuration. The game remains running after capture. Existing final videos and WAV files are preserved; use a fresh output directory and archive task-owned audio before another recording.

The 30 fps recording rate is not a claim about engine frame rate. Run performance sampling separately. Capture aborts if its target loses foreground, minimizes, closes or changes client size. It produces a JSON report, logs, source video, final MP4 and eight extracted review frames. Audio alignment is estimated from the first encoded frame and the showcase gate; inspect motion, black/occluded frames and sound synchronization before accepting the result. Successful muxing alone does not establish visual acceptance.

Implementation references: [FFmpeg's Windows client-area capture source](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/libavdevice/gdigrab.c), [verified distributor release](https://github.com/GyanD/codexffmpeg/releases/tag/8.0.1).
