# Motion study evidence

The read-only source audit and isolated ear study have completed. The exact
source, code, report, image and guard-telemetry hashes are recorded in
[the actual review receipt](ear-motion-v1-review-result.json).

`v5h-motion-source-audit.json` records saved rest frames, 49 samples of each
Idle/Walk/Run and fourteen wholly rigid ear modules. The isolated source
`../Nib_EarMotionStudy_v1.blend` adds two distal ear bones and continuous
Head/base/tip weights while retaining all previous bind matrices, neutral
geometry and non-ear curves. No new arm/body animation was authored here;
root owns the captured-human whole-body study.

Actual [rest](ear-motion-v1-renders/Nib_EarRest.png),
[left peak](ear-motion-v1-renders/Nib_EarLeftPeak.png) and
[recovery](ear-motion-v1-renders/Nib_EarLeftRecovery.png) views show a small
tip lift and return without a newly visible attachment split. They do not
prove natural timing in motion. The model's ear shape/fur, face and cloth
still fail artistic review, and the inherited oral gate remains false.
No new FBX, material bake, shared promotion or engine import exists.

The current exported arm trajectories were measured independently in
`benchmark/unreal/evidence/animation-import-audit/raw-locomotion-arms.json`.
Native character motion quality still requires direct temporal review.
