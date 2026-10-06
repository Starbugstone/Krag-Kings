# Focused packaged modifier regression — PASS

All **six actual checks pass** on package `fe65cc4a…`. The owned game closes, native/guard/coordinator exit 0, and the temporary window lease is restored. No desktop or unrelated window receives test input.

The test selects the Nib, observes the wide camera, starts a normal Run, then checks zero-hold Right Shift+RMB, unmodified RMB, and Left Shift+RMB. Each ground target is projected from a fresh, settled runtime state and excluded from the units' silhouettes. These commands occur after the preceding movement settles; they do not prove a smooth active gait transition.

The real [runtime log](runtime.log) proves both modifier cases survive same-frame release: at frame **187** (Right Shift) and **376** (Left Shift), `KK_MOVE_PRESS walk=1` is followed by `KK_MOVE_DISPATCH walk=1 currentShift=0`, a terrain hit and an accepted Walk command. The unmodified press at frame **302** dispatches `walk=0 currentShift=0` and produces Run. The state predicates confirm the resulting actions.

[Input report](input-smoke-report.json), [coordinator/close result](native-input-result.json), [summary](summary.json) and [exact executed harness](executed-input_smoke.ps1) are preserved. The old failed attempts remain separate. New motion clips are not included and character art still fails acceptance.
