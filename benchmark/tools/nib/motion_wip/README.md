# Nib natural-motion and ear preparation

Prepared after the user's direct review of awkward arm orientation and their
request for natural whole-body/idle motion and Nib ear twitches. No script in
this folder has yet authored or rendered a Blender candidate.

Root owns the common captured-human torso/pelvis/clavicle/arm adaptation under
`benchmark/tools/animation/`. Do not fork another arm solver here. Preserve
the foot-contact contract and existing weapon relationship until actual source
and engine motion reviews establish the new behavior.

`audit-v5h-motion.job.json` is a read-only guarded inspection of the actual
saved v5h source. It records rest frames, 49 samples of each Idle/Walk/Run,
shoulder/elbow/wrist and foot trajectories, torso movement and current ear
weights. Dense mesh evaluation is disabled, so it cannot claim a mesh
deformation or animation-quality pass. The existing raw FBX audit in
`benchmark/unreal/evidence/animation-import-audit/raw-locomotion-arms.json`
already establishes that the current source motion reaches exported clips;
there is no arm retargeting layer in either engine that explains away it.

Current Nib source has Ear_L/R under FaceRoot, but whole ear/rim/fur modules
are rigidly assigned to one ear bone. Idle and gait use small repeated sine
sway, while Hit adds 16–18 degree rotation. Nonzero tracks do not demonstrate
the rooted, independent natural twitch requested by the user.

`ear_motion.py` prepares the following isolated change:

- Preserve existing bones and their bind matrices. Add EarTip_L/R as children
  of Ear_L/R, still inside the FaceRoot subtree.
- Blend each existing ear module continuously from Head through its base Ear
  bone to the distal child, with no changes to neutral coordinates or UVs.
- Replace old ear-only action curves with independently timed small alert
  pulses and a smaller delayed cartilage response. No simulation or repeating
  large whole-ear flap is used. Seven clip endpoints return to rest.
- Keep all other action curves, body motion, facial keys and geometry intact.

These amplitudes, timing and skinning ranges are tuning proposals. The plain
Python curve/weight checks do not establish appearance. Before promotion,
inspect actual neutral/peak/recovery geometry and temporal motion, attachment
at the skull/goggles and both ears' silhouette. Then export the full matching
rig and all standalone clips, validate their bind/ear tracks, and inspect the
same updated content in Unity and Unreal. Do not mix new 77-bone source clips
with the previous 75-bone exports or claim either count until generated.

The source facial/cloth/fur quality failures remain recorded separately in the
Nib art README. Motion work is not artistic acceptance of those surfaces.
