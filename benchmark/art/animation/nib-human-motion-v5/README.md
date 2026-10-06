# Nib v5 forward-gaze and portable-motion review

Actual source: `Nib_HumanMotion_Study_v5.blend`, SHA256 `b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da`.

The 24 actual clay poses preserve v4's anatomical rig/motion while correcting the inherited head/neck calibration. Inspected Walk/Run side views now face forward. This remains a source study: the free hand still reads too cupped, clothing intersects the new body, and face/groom/material likeness remains unaccepted.

`fbx/` preserves the actual first seven-clip export, failed roundtrip and read-only position diagnosis. Blender's inferred connected-bone flags suppress pelvis and tongue translation during its playback; the FBX channels themselves retain those translations. `fbx-v2/` contains a separately generated export with explicit source hierarchy/connection metadata and a passing corrected roundtrip. The validator restores source connection flags without changing bind matrices or FBX files, then checks all 79 bones, parent relationships, full rest matrices, duration, 17 sampled positions/rotations/scales per clip and varying local facial controls. All seven clips pass, with sampled maximum position error 0.724 µm. This does not establish native engine import, actual skin deformation, slope contacts or final quality.

Each actual recipe is frozen and hash-matched to its report. Guarded source, pose review, export, failed roundtrip and diagnostic peaks were 690, 1,301, 489, 313 and 554 MiB respectively. The lightweight root jobs used a 2.5 GiB worker limit and 8 GiB minimum start RAM after those measured workloads; the global guard remained unchanged. Shared engine assets were not replaced.
