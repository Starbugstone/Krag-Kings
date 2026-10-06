# Isolated Nib facial review sequence

Current status: v5c and v5d sources plus diagnostic Face/Profile/ThreeQuarter
views exist and fail likeness. Both retain a false sampled oral-occlusion gate.
The separate v4b deformation repair is already validated and promoted. Current
shared assets remain pinned; no v5 art export is authorized by these results.
Launch only after root grants the serialized heavy slot, using
`benchmark/tools/Run-HeavyTask.ps1 -JobSpec`. The historical v5c sequence below
is retained as provenance, not a request to rerun or overwrite that source.
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

## Actual v5c depth evidence and prepared v5d

The preserved v5c diagnostic profile/three-quarter job has now completed with
exit 0 and a 2,631 MB peak private working allocation. Source SHA remains
`e56d8a16218562f14f0e1ba6866751abacc27ab32adaa20b347fb5b93a2d8711`.
`art/nib/v5-study/native-v5c-depth-review-result.json` records image hashes and
the failed review. The profile exposes a human nasal tip/vertical philtrum and
long lower jaw, plus jagged/open lower-neck edges. Three-quarter confirms slit
eyes and flat muzzle planes. The dark rectangular posterior patch also has a
separate cause: a mouth-material test with no upper Y bound.

`fit_head_v5d.py` keeps the legacy fit intact and prepares a bounded continuous
volume correction: broaden the alar/nose-pad loops, bring the upper lip/muzzle
toward the pad, shorten the lower face and reopen the entire ocular region.
The source code retains nostril topology and moves the existing cavity, teeth,
gums, canonical blue tongue and their pivots by the same fitted seam delta.
It is a proposal, not accepted anatomy. A lightweight raw-cage check reports a
proposed oral shift of approximately 15.17 mm forward and 7.78 mm upward; the
local eye-height probe changes from 6.77 to 10.90 mm. Those probes are not final
evaluated lid apertures or proof of visibility/closure.

`nib_neck_v5d.py` prepares an actual planar boundary and cap, conforms the lower
neck to retained body geometry, and blends Neck/Head weights. The generation
report checks for remaining open lower-neck edges after subdivision. The body
remains a separate module: a whole-character topology weld is not claimed.
No scarf geometry is added to cover the fault. The oral material is restricted
to the audited mouth face set. The cut API direction was checked against the
[Blender BMesh documentation](https://docs.blender.org/api/5.1/bmesh.ops.html#bmesh.ops.bisect_plane).

The next allocated slot starts with `native-v5d-generate.job.json`, then report
inspection and `native-v5d-face-review.job.json`. A failed gate stops dependent
exports; an explicitly labeled diagnostic image can be scheduled when needed
to interpret the actual failure. The v5d source now exists and the results below supersede its proposal-only status. New shape,
ocular materials and neck behavior need actual neutral, depth, blink, tongue
and body-action review before any PBR bake or engine handoff. Fur and clothing
still require substantial later work; neither the prior depth images nor the
prepared correction is artistic acceptance.


## Actual v5d result and next audit

`native-v5d-generate.job.json` completed, followed by the explicitly diagnostic
`native-v5d-diagnostic-depth.job.json` with Face/Profile/ThreeQuarter. Both exited
0 with completion markers. The exact source hash, image hashes, guard memory
and candid failure record are in `art/nib/v5-study/native-v5d-review-result.json`.
The false gate was preserved; no gate tolerance was relaxed. The source remains
unchanged, and no dependent export or shared promotion is queued.

Next allocated inspection is the read-only `native-v5d-material-audit.job.json`.
It records actual assigned facial material bounds, nose-mask overlap, region
normals and frontal surface-hit material IDs. This separates the flat jaw's
self-shadow from a selector fault and identifies the remaining dark neck strip.
It is prepared and syntax checked only. After its evidence, the next isolated
shape must place the compact nose ahead of a rounded continuous muzzle, curve
the upper-lip pads/smile instead of translating a flat shelf, and retain the
wider ocular aperture. Any source revision needs fresh neutral/depth and posed
closure proof before material bake. The separate provisional groom recipe is
prepared in `../v6_groom_wip/`; it must not conceal unresolved facial geometry.
