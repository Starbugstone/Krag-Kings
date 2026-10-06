# Locomotion source and engine audit — 6 October 2026

The present Krag arm gait is already unusually straight and spread in the exported source. This is not an accepted animation style. The evidence supports correcting the authored movement and anatomy before changing either engine's import transforms.

[Raw measurements](raw-locomotion-arms.json) read the four current standalone Walk/Run FBXs directly, with exact input hashes and 37 samples per clip. No editor, renderer or native input was launched. Joint positions include FBX pre/post rotations and are expressed in the exported armature space. An elbow bend of zero means a straight shoulder–elbow–wrist chain.

| Source clip | Elbow bend, both sides | Other observed range |
| --- | --- | --- |
| Krag Walk | 17.48–20.74° | Wrist height 0.878–0.900 m |
| Krag Run | 17.48–27.80° | Wrist X extends 0.438–0.642 m from the character center on each side; wrist height 0.879–0.928 m |
| Nib Walk | 25.14–30.78° | Wrist height 0.566–0.574 m |
| Nib Run | 43.29–57.73° | Wrist height 0.562–0.599 m |

These are descriptive measurements, not proposed anatomical targets. Human-like motion, species weight, firearm handling and correct elbow/palm orientation need temporal visual review. The current authoring recipes apply arm swing and elbow bend through local Euler X, so the intended anatomical axes depend on bone rest orientation and roll. A rest-aware motion source or solver should replace assumptions about a universal local axis.

## Existing actual engine evidence

The [Unreal walk frame](../showcase-profile-audio-fixed/frames/action-07.7-walk.png) and [Unity walk frame](../../../evidence/unity/20261006-sand-v2-showcase/frames/action-07.7-walk.png) both show the broad, down-hanging Krag arm silhouette and separated muscle masses. The [Unreal overlap frame](../showcase-profile-audio-fixed/frames/action-14.4-overlap.png) and [Unity overlap frame](../../../evidence/unity/20261006-sand-v2-showcase/frames/action-14.4-overlap.png) also show similar upper-body poses during melee/shooting. The [Unreal melee close-up](../showcase-profile-audio-fixed/frames/action-46.0-krag-melee.png) exposes the discontinuous armpit/pectoral forms and poor hand shape clearly.

These files were decoded from actual recordings; their source hashes and measured capture offsets are in each recording's `frames/review-frame-samples.json`. Elapsed showcase time does not guarantee identical locomotion phase, position or action blend in the two engines. This review therefore establishes shared visible defects, not pixel-identical or quaternion-identical pose parity.

## Transform and runtime findings

- Unity imports these characters as **Legacy** animation, not a Humanoid Avatar. Unreal plays each variant's explicit clips on its own imported skeleton. No arm-retarget node or arm IK is present in the Unreal runtime graph. Its procedural skeletal controls affect the two legs/feet; the separate facial layer starts at `FaceRoot`.
- Mesh and animation import explicitly enable scene/unit conversion, disable forced front-X conversion and use scale 1.0. The complete character has a constant mesh-yaw adapter; this cannot selectively twist the arms.
- Installed Unreal 5.8.3 defaults use the actual bind pose: `bUseT0AsRefPose=False`, `bUpdateSkeletonReferencePose=False`. Animation defaults are `bPreserveLocalTransform=False`, automatic sample rate, exported time range and redundant-key removal. The importer does not override these fields, and no matching saved project-config override was found. These are source/config findings; the existing report did not serialize each asset's saved import options.
- The saved [actual import report](../import-report.json) records one uniform 100× armature wrapper for each species, otherwise approximately unit local bone scales. Current Walk/Run upper/lower-arm and leg translation-to-bind-length ratios stay within approximately 4.8×10⁻⁷ of one. This is evidence against a unit-conversion length error, not proof that every imported rotation is correct.
- Source standalone bind roundtrips previously passed against the corresponding assembled meshes. Existing validation does not compare complete source and engine arm rotation trajectories. That remains a bounded follow-up when revised clips exist; no speculative importer flag change was made here.
- Source Nib ear tracks already include small periodic movement, but existing rigid whole-ear weighting and repeated sine motion do not establish the newly requested natural twitch. The artist is preparing rooted ear deformation and delayed tip motion in an isolated candidate.

No model, animation, import setting or packaged build was changed by this audit. Character anatomy and motion remain rejected. The queued press-time Shift/right-click correction is separate and still needs its reserved compile/package/native proof.

## Reproduce

Run `benchmark/tools/unreal/audit_locomotion_arms.py --output <report.json>` using Python with NumPy. The installed Blender Python was used as a plain Python interpreter; Blender itself was not launched. The script reuses the project's raw FBX reader and rejects non-XYZ rotations or nonzero pivots instead of inventing their meaning.
