# Press-context package — native input, 6 October 2026

The modifier/cursor fix compiles and packages, but the full native suite is **still incomplete**. This attempt passes **34 checks**, then stops at Nib Shift+RMB because the verifier's fixed screen coordinate hits the Krag rather than ground. The owned game closes normally, the guard exits 0, the coordinator exits 1, and the window lease is restored. No repeat run followed this failure.

- Editor native compile: 72.75 seconds; [actual build evidence](../press-context-native-build/).
- BuildCookRun: 201.47 seconds, fresh completion marker; [actual package evidence](../press-context-package/).
- Executable SHA-256: `e538b28ac26d42c665e274a9aa15ec1e1185f5f4893a2c1bd63dbdbe475b4de5`.
- The package now actually bundles and hashes `Engine/Extras/Redist/en-us/vc_redist.x64.exe`. No installer was executed and no clean-machine validation is claimed.
- Source content remains the prior pinned character/environment snapshot. Art and animation acceptance remain false.

The [actual runtime log](runtime.txt) records the failing event at frame 555: `KK_MOVE_PRESS walk=1`, followed by `KK_MOVE_DISPATCH walk=1 currentShift=1`, with actor `KKBenchmarkUnit_2147482380`. The click at (1344,778) hit the other unit. Movement appropriately ignores a unit hit. This failure does **not** justify changing game click semantics or claim a new modifier defect.

The earlier settled-camera Nib Run now passes. Krag Walk, overlapping independent actions, authored discharges, variants, facial acting, and camera pan/orbit/zoom during an action also pass. The zero-hold left/right Shift probes were never reached, so this run does not yet prove the original same-frame modifier regression is fixed.

`executed-input_smoke.ps1` preserves the exact failed verifier. The prepared replacement uses projected world-ground candidates with footprint/path and conservative unit-occlusion exclusion, checking its camera projection against the runtime's actual unit projections before sending input. A focused modifier-only mode tests zero-hold right Shift, unmodified release, and left Shift before another full suite. Its native execution is pending; the pure helper and Windows interop compilation were checked without launching a game or sending input.
