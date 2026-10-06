# Whole-body motion studies

These are isolated source studies addressing the user's rejected rigid torso and unnatural locomotion arms. The running engine assets have not yet been replaced by these files.

| Study | Actual evidence | Remaining failures |
| --- | --- | --- |
| Krag v1 | Saved source, 24 actual front/side clay poses, unchanged geometry/bind checks | Open free hand, imperfect ground contact, noisy captured running knee |
| Krag v2 | Guarded calculation stopped before source save | Initial running contact interval forced an excessive pelvis correction; failure preserved |
| Krag v2b | Saved source, 228 actual clay frames across Walk/Run/Idle, loop-joint error under 0.5 µm | Bone marker grounding did not establish actual boot contact: subsequent rigid-surface audit found 9.4 mm walking and 39.7 mm running sole penetration. Hand posture needs refinement. |
| Nib v2b | Saved source and 24 actual clay poses, existing 77-bone ear rig retained | Free palm faces upward in some poses; shoulder construction/deformation, clothing, face and groom remain below the concepts |
| Krag v3b | Saved source and 24 actual clay poses; actual rigid boot clouds used in grounding; preserved mesh/bind | Whole-loop temporal review, residual swing scuffing, action/grip integration and final likeness remain open |
| Nib v3 | Saved source and 24 actual clay poses, v5i orbital repair, reauthored ear tracks and relaxed fingers | Medial palm correction exposes an elbow twist/pinch; continuous anatomical weighting is required before promotion |
| Nib v4 | Saved 79-bone anatomical source and 204 actual full-cycle front/side clay frames; continuous body and distributed forearm twist | Old head calibration looks down during Walk and up during Run; cupped free hand, clothing and likeness still fail |
| Nib v5 | Saved source and 24 actual poses with forward gaze; seven standalone FBX takes pass the corrected 79-bone roundtrip | Free fingers need a consistent flexion plane/looser fist, clothing/groom and final likeness remain open; full matching engine mesh/skeleton integration is pending |
| Nib v6 | Saved source, completed neutral channels and 18 hand poses | Adding curl to the already bent bind overcurled the fingers; hand web and old glove details remained distorted |
| Nib hand skinning v1 | Saved source with topology-based digit domains and 18 hand poses | Better influence isolation did not undo the old cage warp or overcurled action |
| [Nib v7](nib-human-motion-v7/README.md) | Saved source, 204 full-cycle frames, 18 hand poses and an actual Blender motion video; curl now accounts for existing bind bend | Whole-body motion is improved; hand shape, clothing, groom, face and engine integration remain unfinished |
| [Nib anatomical hand fit v1](nib-hand-fit-v1/README.md) | Original licensed hand cage fitted through separate anatomical digit domains; saved source and 18 poses | Rounder fingers and reduced web stretching; old floating glove details required a separate correction |
| [Nib fitted glove v1](nib-glove-fit-v1/README.md) | Saved dorsal panel, fitted wrist band and four surface-supported rivets; 18 poses | Floating rivets are corrected in inspected views; forearm wraps, action grip, right hand and material review remain open |

The six-second idle contains restrained breathing, pelvis/torso weight transfer, attentive head motion and planted feet. Walk/run facial and finger curves are carried from the sources. Neither retargeting nor a saved action proves the facial performance is accepted.

Sources and frozen recipes are preserved per study. Contact and speed values are provisional. Clay frames reveal silhouette and motion; they do not validate final materials or lighting. Native engine import, transition smoothness, slope behavior, bionic fit and performance must be checked after integration.

The v3 recipe uses actual audited rigid boot surfaces instead of approximate sole markers, corrects the free palm orientation and authors relaxed free fingers. The first Krag v3 calculation stopped on a Blender keyframe-collection handle error before saving; v3b fixes the collection iteration. Saved v3b/v3 sources now exist. Ground and loop residuals are under 0.001 mm in their source numerical checks, which do not establish motion quality or imported engine contact. Idle blinks retain the prior closure speed instead of being stretched across the longer standing clip.

Nib v4/v5 retain the source's connected anatomical body, 79 authored bones, unchanged bind and geometry. The two forearm twist controls distribute pronation through LowerArm → ForearmTwist → Hand. The idle remains six seconds; Walk is 0.8 seconds at a proposed 0.8796 m/s and Run is 0.6 seconds at 2.5300 m/s. Actual boot-based swing clearance is fitted before export. Head/neck mean pitch in v5 is deliberately recalibrated for forward attention, retaining cyclic capture variation; it is not an unchanged recording of the actor's gaze.

The first v5 roundtrip **failed** four positional checks. A read-only diagnostic proved that Blender 5.2 automatically connected coincident child bones and suppressed correctly imported translation channels, including Pelvis bounce and TongueTip extension. The [preserved raw failure](nib-human-motion-v5/fbx/roundtrip.json) and [actual attribution](nib-human-motion-v5/fbx/position-diagnostic.json) remain available. The [corrected validation](nib-human-motion-v5/fbx-v2/roundtrip.json) explicitly restores the source connection flags and verifies unchanged bind matrices/hierarchy before comparing 17 poses per clip. All seven takes pass; the maximum sampled head-position error is 0.000724 mm and angular error is 0.000614 degrees. This is Blender FBX fidelity, not Unity/Unreal playback or artistic acceptance.

Exports exclude archived study actions, enforce saved-source cadence, reset unkeyed channels and complete neutral transform tracks. The v6/v7 editable masters now also contain complete canonical transform channels. These are actual generated sources; the current engines still use the earlier shared assets. Frozen recipes beside each study distinguish executed code from subsequent preparations.
