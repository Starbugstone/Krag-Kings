# Nib continuous body and forearm twist study

The isolated source and three actual diagnostic renders exist. They do not
change the promoted v4b package or establish artistic acceptance. The source
is `art/nib/Nib_AnatomicalBodyStudy_v1.blend`, SHA-256
`21bae901ace9613c34c0482efc3e07b21e400cb650a6c552280e81052d05d00d`.
The complete generation, pose, memory and failure record is
`art/nib/motion-study/anatomical-body-v1-review-result.json`.

The former body was already voxel-united, but its tube-derived shoulders read
as separate capsules. Its absolute-Z elbow field put about 69% LowerArm
influence at the bind elbow and no Clavicle influence. Root's captured-human
motion aligned the free palm anatomically and exposed a severe elbow notch.

This candidate fits the official CC0 Blender Studio male body cage to the
existing Nib shoulder/elbow/wrist landmarks. It excludes the human head,
hands and legs. Connected thorax, axilla, shoulder and elbow topology carries
a source-space harmonic arm domain, Clavicle blending, and chain-relative
elbow weights. The retained control cage has 2,176 vertices / 2,094 faces;
the actual surface has 33,838 vertices / 67,008 triangles and at most four
positive influences. Matching fine body fuzz has 2,300 area-weighted roots.
The preserved body/face design remains provisional; this is construction
improvement, not an approved change of proportions or species identity.

## Skeleton and animation contract

`ForearmTwist_L/R` are children of `LowerArm_L/R`, coincident with the existing
elbow-to-wrist head/tail and rest roll. Blender local +Y is the twist axis.
`Hand_L/R` are reparented under their corresponding twist bone, with original
global bind preserved within explicitly measured float32 rounding. The maximum
translation difference is 59.6 nm and maximum rotation difference is
0.00001618 degrees. Source generation records every changed matrix rather
than claiming byte identity. Face/EarTip global bind remains unchanged.

Root's new retarget must keep captured swing/flex on LowerArm, place half the
axial pronation on ForearmTwist, and bake the full desired Hand orientation
(the remaining half contributes locally). Skin goes from LowerArm to Twist
over normalized forearm progress .10–.48, then Twist to Hand over .48–.94.
These ranges are provisional fitting values. No Blender-only DQS or constraint
is relied on; actual proof uses linear blend skinning.

The source retains old action curves. They are not fresh captured-human clips
for this 79-bone skeleton. Root owns the new motion pass and complete exports.
Do not mix this source with the old 75-bone shared FBXs or 77-bone ear clips.
This shape study replaces the Natural torso/arms only. Other restorative body
surfaces and rigid replacement modules still need their own anatomical fit.

## Actual review

Neutral and 90-degree pronation show a coherent shoulder and elbow without the
old gross notch. The 60-degree elbow / 90-degree pronation extreme still
compresses the inner elbow: minimum triangle area ratio .130, maximum edge
stretch 1.994, p99 1.147. There are no new zero-area triangles. These static
clay images do not establish temporal quality or correct engine behavior.

The new chest intersects the old garment surfaces. Neck cloth remains jagged,
the bib/straps are crude, and face/groom/material likeness still fails. Next
work must refit real garment surfaces and inspect captured motion before any
candidate promotion. The existing v5i eyelid/Jaw repairs, dark-blue tongue and
independent ear construction are preserved.

The first source attempt stopped at an unnecessary Hand matrix rewrite. The
next caught one-ULP frame rounding in an untouched finger. Both failures are
preserved. Removing the redundant matrix setter and recording explicit
float32-aware tolerances allowed the final bounded source job to pass.
