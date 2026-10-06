# Nib next-pass studies

These files distinguish the validated, promoted runtime derivative from the still-unexecuted v5 art work. The dense v4b `Nib_Master.blend` remains preserved; shared FBXs now use the measured optimized derivative after root verified all 85 files.

The head studies use the actual 3,242-vertex `GEO-head_animation_realistic` topology from Blender Studio's Human Base Meshes bundle v1.4.1. Its bundle README states CC0. The source inventory, provenance and unrelated Rain Rig license text are preserved under `benchmark/art/reference-anatomy/` and `benchmark/art/krag/anatomy-study/`. No outside anatomy was present in v4b.

`Reference_Head_*.png` and `Nib_HeadWarp_*.png` are lightweight rasterized projections of real polygon data, without Blender materials, lighting, eye objects, fur or rigging. They are diagnostic studies, not finished asset renders. `head-warp-study.json` records the actual trial geometry.

The first warp has coherent orbital, nostril and lip topology but still fails the concept: the nose/philtrum read too human, side human-ear relief must be removed, cheek/muzzle proportions need work, and its temporary neck cut is open. Do not integrate it or present it as accepted. The two large fennec ears remain the only intended ears. Reference-fitting values in `fit_head.py` are provisional modeling controls.

Next steps are to remove the source human-ear topology and rebuild the lateral skull, form a compact feline nose/upper muzzle and narrow expressive lids over properly fitted convex eyeballs, then inspect real neutral-light Blender Front/Side/Perspective/blink/closed-mouth poses. Preserve the current FaceRoot, named morphs, seven clips and portable driver contract when integrating.

The lightweight actual-FBX audits measured 1,158,384 triangles: 663,632 skin, 269,036 hair, 96,048 cloth and 41,716 workwear. Connected surfaces identify the continuous torso/arms as 570,752 triangles, the face as 48,832 and the scarf as 33,792. The FBX parser reports mesh-local bounds explicitly; these are not final world bounds.

The separate `runtime-cost-audit.job.json` loads the pinned source read-only and reports named components plus CC0 reference face-set metadata. It must run through the shared heavy-task guard only after a slot is granted.

`optimize_runtime_v4b.py` generates a separate derivative using the Krag agent's seam-protected reduction and barycentric morph transfer. It preserves current face/eye topology and finger detail. The accepted body trial retains 180k triangles per body, with measured 1.3 mm surface and 0.8 mm morph-delta limits; cloth limits are separate. Opaque fur retains every guide/root/tip and exact retained UV/weight/morph data, using adaptive segmentation that retains additional rings where curvature requires them. Omitted-ring errors are measured for every shape. These are modeling tolerances, not visual acceptance.

`posed_skin_check.py` samples actual authored bone matrices with dense mesh evaluation disabled, then compares source and derived skinning plus portable morphs at fixed rest-surface correspondences across all seven actions. It measures sampled LBS discrepancies separately from source surface and morph-transfer checks. It does not replace native engine or visual inspection.

The existing export, render and roundtrip tools accept optional source/output/report paths. Their default v4b behavior is unchanged. Exports were generated and validated in `benchmark/local/candidates/nib-v4b-optimized`, outside the Unity auto-imported shared tree, then root promoted them. Images/reports stay here. The initial 250–350k aspiration was exceeded to preserve the measured surface/deformation limits.

## Native v5 code prepared, not yet generated

`rebuild_head_v5.py` now prepares a separate `Nib_Master_v5_WIP.blend`: fitted CC0 animation-head topology and matched eye geometry, explicit removal of the two original human ears, deterministic scalp/ear guide clumps, three compressed scarf wraps and common bib/pocket shaping. It preserves the pinned source and shared exports. `--cinematic` uses the same guide field with denser strands into a separately named master; `--hands` additionally fits the CC0 coherent hand topology and corrects right finger ordering, which requires matching clip re-export.

These scripts have passed Python syntax checking only. The ear patches, eyes/blinks, lip/teeth fit, scalp clearance, cloth action clearance and hand weighting must be inspected in actual Blender output before any promotion. They are queued after the runtime derivative, not evidence that v5 exists yet.

## Promoted runtime derivative — technically validated, artistically unaccepted

`Nib_Runtime_Optimized_v4b.blend` was generated in the guarded process with peak private memory 1,287 MB. SHA-256: `6a8a65e66a4f37f799ec97cb0ecb2259073be6391fdded340667892dcb147f1f`.

- Natural: 538,642 triangles; Grip: 532,244; Leg: 533,534. The initial 350k aspiration was not reached without exceeding the geometric limits.
- Organic and grip body components each retain 180k triangles. Across 23 sampled actual action poses, their worst source/derived surface differences were 0.532 mm and 0.619 mm; scarf was 0.206 mm.
- Facial topology is unchanged. Every fur guide/root/tip remains; segments are retained adaptively where curvature needs them. The rejected uniform segmentation exceeded the 2.5 mm chord limit on a few head strands and was not accepted.
- A 40k body target exceeded the 1.3 mm rest-surface bound and was rejected. The undershirt and both trousers retain source density after their individual reductions failed the 2 mm limit.
- Front/Face/Shoot/Run/Blink renders are complete and preserve baseline appearance. The Blink image clearly fails lid occlusion because the original iris discs protrude; this is an existing art/deformation defect for the v5 replacement, not a passing facial review.
- All 64 changed components pass a separate 23-pose source/derived comparison (up to 4,000 samples per component), worst 2.287 mm on head strands. The shared barycentric helper needed float64 arithmetic to avoid cancellation on extremely thin triangles. The false-alarm report and the corrected passing report are preserved. These checks do not establish performance or artistic quality.
- All three variant FBXs and seven standalone animation FBXs passed fresh-process reimport. Each variant has one mesh, 75 bones, 25 morphs and no invalid weights. All seven clips have one skeletal take and verified varying face controls; maximum bind-matrix difference is exactly zero. Peak private memory for export was 1,507 MB and roundtrip validation was recorded in the receipt. Actual engine checks remain pending.

Failed trial reports remain in the ignored `../versions/runtime-reduction-v4b-failures/` local archive. None of these results imply artistic acceptance or measured engine performance. Root verified the 85-file receipt, normalized candidate JSONs to LF and promoted the selected derivative to shared. The receipt records the final promoted hashes.
