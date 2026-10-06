# Actual Unity video review — 6 October 2026

This is **failed visual-review footage**, preserved to show the actual issues and validate the recording pipeline. It is not the final investor demo. The video records the packaged Windows game at native 1920×1080 with the Balanced lighting profile and the current Krag v7 / Nib v4b shared assets. Build and content identities are recorded in `result.json`.

[Actual 75-second recording](unity-showcase.mp4) · [Capture validation](unity-showcase-capture.json) · [Review outcome](result.json)

Windows Graphics Capture targets only the explicit game window. The 30 FPS recording has changing frames, no detected long black intervals, and a nonzero engine-only audio track; 15 of 2,257 capture frames repeated. Recording FPS is not a game performance measurement. Audio was aligned from actual capture and engine timestamps; listening and fine synchronization review remain unfinished. The earlier GDI recording was frozen and remains rejected.

The reviewer inspected eight cue frames and additional frames during walk, melee and shooting. Selected actual frames are retained here. `action-37.70.png` exposes large Nib forehead spikes during Shoot. The raw FBX audit identifies contaminated body corrective shapes: `ShoulderRaise_R` moves forehead vertices upward by 0.154m. Smaller facial targets are bounded normally. This is an export defect that numerical morph-activation checks did not catch. The exporter repair and posed visual regression must pass before shared promotion.

The footage also shows backlit facial views, cropped Nib ears and cropped feet when the units spread. Prepared camera changes add bounds-based wide framing, a wider Nib portrait and ordinary short walks that face the existing sun before portraits. These changes are not present in this recording and still require a rebuilt runtime review. Concept likeness, cloth construction, facial forms and fur remain below the target in both current runtime models.
