# Focused zero-hold modifier run — 6 October 2026

This actual packaged run proves the **right Shift same-frame case**, but the focused sequence remains incomplete: four checks pass and the next unmodified Run check fails because its ray hits the moving Nib. Left Shift is not reached. The owned game closes, the guard exits 0, the coordinator exits 1 and the window lease is restored. No repeated launch followed.

The unchanged package is `e538b28ac26d42c665e274a9aa15ec1e1185f5f4893a2c1bd63dbdbe475b4de5`. The test submits Shift down, RMB down/up and Shift up together with Windows `SendInput` and no hold interval. At runtime frame 145, [actual logs](runtime.txt) show:

```text
KK_MOVE_PRESS walk=1 ... frame=145
KK_MOVE_DISPATCH walk=1 currentShift=0 ... hit=1 actor=StaticMeshActor...
KK_MOVE species=Nib ... walk=1
```

The actual state then reports Walk. This is the intended regression proof: the deferred callback sees Shift released, while the retained press-time intent still walks.

At frame 165 the next press and dispatch both correctly report `walk=0`. Its hit actor is the Nib itself, so the controller appropriately does not issue a move. The planned target came from the observed camera and excluded the Nib's earlier bounds, but the character moved approximately 45 cm during target computation/event preparation and crossed the ray. Camera projection itself agreed with the runtime within 0.003 pixels. This is a verifier timing defect, not evidence that unmodified input retained Shift.

The prepared verifier now waits for fresh, stable unit positions and no active Walk/Run before projecting each ground destination. It therefore tests the next command after the preceding move has settled; it does not claim an immediate active-gait transition. Its source parser/interop checks pass, but the revised native run remains pending. Game movement semantics and the package were not changed for this correction.

Character motion/likeness and the full native suite remain unaccepted. This input regression evidence does not address the separate ongoing anatomy and mocap work.
