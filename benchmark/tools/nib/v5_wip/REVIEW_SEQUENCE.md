# Isolated Nib v5c review sequence

Status: v5c generation and one explicit diagnostic Face render completed; the
source failed likeness and its strict numeric aperture gate remains false.
Remaining views, poses, baking and exports have not run. The immediate priority
is the separate v4b runtime morph-union repair, not promotion of this art pass.
Current shared v4b triangle exports remain pinned. Launch only after root grants
the serialized heavy slot, using `benchmark/tools/Run-HeavyTask.ps1 -JobSpec`.
Every job below uses four Blender threads, an eight-GiB private-memory cap,
`--python-exit-code 2` and a fresh completion marker.

1. `native-v5b-coordinate-audit.job.json` reads the actual failed v5b source. It
   records neutral/Idle/Tongue evaluated oral bounds, face controls and morphs,
   front/oblique mouth occlusion, visible eye samples, and source zero-area/UV
   defects. It does not rewrite that source.
2. `native-v5c-generate.job.json` creates only `Nib_Master_v5c_WIP.blend` and its
   source report. The explicit revision prevents historical jobs from silently
   producing differently named versions. The report embeds active code hashes,
   actual fitted eye centers, all retained oral parts/pivots and groom costs.
3. Read `art/nib/v5-study/native-head-v5c.json`. Its `preRenderGate` must pass for
   neutral and Idle: no sampled oral parts outside the face and visible iris
   samples on both eyes. A failing gate stops dependent render/export work;
   inspect the coordinate evidence instead of compensating by eye.
4. Run `native-v5c-face-review.job.json` and inspect the actual saved mesh beside
   original sheet 02. Only then run `native-v5c-front-review.job.json`. Each
   separately guarded job verifies the report's exact saved-source hash and
   refuses a failed gate.
5. `native-v5c-face-profile-review.job.json` and
   `native-v5c-face-three-quarter-review.job.json` inspect depth before further
   facial tuning. The reference has angled brow/cheek planes, a short projecting
   muzzle and a broad dark animal nose; a stretched human mask still fails.
6. `native-v5c-coordinate-audit.job.json` can recheck the saved v5c source and its
   expressive tongue pose. Blink, tongue, wary acting, hand/weapon grip and
   body-action renders follow only after the structural review. Existing clips
   still need full native and engine deformation review after new bind changes.

The render gates are sampled geometry checks, not artistic acceptance. Review
ear cup depth, pink exposed membrane, tawny outer/rim nap, pale inner/head wisps,
organic clump flow around the goggles, and visible mottled skin with fine fuzz.
Do not interpret finer strand radii or increased counts as a quality pass.
The dark blue tongue remains canonical; the capable adult Nib remains playful,
physically weak and a little timid. Interior designs remain provisional.

No v5c PBR bake, runtime reduction, FBX export or shared promotion is queued by
this sequence. Those require an actual reviewed source, updated materials and
matching clips, plus new engine verification.


The critical v4b morph repair has now been generated, independently validated, posed and promoted by root. The separate repaired source is `Nib_Runtime_Optimized_v4b_MorphRepair.blend`; original source remains preserved. All source shape creation is explicitly unmixed. The current generator requires new revision v5d and defaults to that repaired source. Historical v5c jobs correspond to the embedded/checkpointed source revision and must not overwrite the failed v5c evidence. Next art preparation is lightweight only while UE owns the guard. Preserved v5c profile/three-quarter diagnostic captures need explicit slot allocation before the next face warp. Smooth ocular materials are connected in the next v5d recipe but have not been generated, reviewed or baked. The separate `native-v5c-diagnostic-depth.job.json` is ready for the next allocated review slot; it preserves the failed structural gate and does not overwrite the existing Face image.

## Future changed-topology export preparation (not executed)

A v5 source cannot use the promoted v4b FBX as its normal/morph preservation reference. After a v5 source passes its actual shape/pose review and its new ocular/face/groom PBR maps are baked:

1. Export that exact saved source and matching source report to an isolated `benchmark/local/candidates/nib-v5-reference` using explicit `--texture-dir` for the new PBR set, without `--triangulate`.
2. Export the same unchanged source to a separate isolated triangle candidate with `--triangulate --baseline-dir .../nib-v5-reference`. The helper must prove identical Basis vertex coordinates/order before transporting that source's own point-domain normals. The default retains newly exported morphs; `--preserve-baseline-morphs` is reserved for an independently validated same-source conversion.
3. Run raw mapped UV/material/normal/shape checks against the new v5 reference, then fresh bind/clip/morph roundtrip and posed proof before asking root to promote.

The explicit baseline/texture CLI options are syntax-checked preparation only. They have not produced a v5 export. The validated v4b repair remains reproducible from checkpoint f85c4f6 (exporter fix introduced in 761b3af), its recorded source and tool hashes.
