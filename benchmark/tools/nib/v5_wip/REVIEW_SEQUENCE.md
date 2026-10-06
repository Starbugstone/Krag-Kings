# Isolated Nib facial review sequence

Current status: v5c, v5d and v5e sources plus diagnostic views exist and fail
likeness. All retain a false sampled oral-occlusion gate. The v5e Tongue extreme
also exposes a hard mouth deformation failure; topology/skinning inspection
now takes priority over additional face shaping or groom generation.
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
It has completed exit 0 and the source is unchanged. The sampled dark jaw and
neck hits are FacialSkin with strongly downward normals, not an oral-material
assignment. After that evidence, the next isolated shape must place the compact
nose ahead of a rounded continuous muzzle, curve
the upper-lip pads/smile instead of translating a flat shelf, and retain the
wider ocular aperture. Any source revision needs fresh neutral/depth and posed
closure proof before material bake. The separate provisional groom recipe is
prepared in `../v6_groom_wip/`; it must not conceal unresolved facial geometry.


## Frozen v5e sequence and actual result

1. `native-v5e-generate.job.json` uses the separate `rebuild_head_v5e.py` and
   `fit_head_v5e.py`, reading the repaired baseline. It does not overwrite v5d
   or shared assets. The wider eye fit and closed-neck helper remain intact.
2. Inspect its actual `native-head-v5e.json` coordinates, strict oral gate and
   source hash. The lightweight `shape-proposal-v5e.json` is only a raw-cage
   check: it proves the proposal changes the nose/lip relationship and leaves
   protected regions unchanged, not that the final subdivided face passes.
3. `native-v5e-depth-review.job.json` requires the matching source gate and
   renders Face/Profile/ThreeQuarter. A diagnostic override needs explicit
   scheduling if the sampled gate still fails; never erase its failure.
4. Verify actual nose lead, rounded paired pads/crease, chin silhouette, neck,
   wider eyes, neutral mouth and provisional oral placement. Blink/tongue/body
   poses follow the neutral structural review. No bake/export/groom promotion
   is queued from this prepared correction.

The frozen generation has now completed. Its strict gate still failed, so
separately named `native-v5e-diagnostic-depth.job.json` and
`native-v5e-diagnostic-expressions.job.json` preserved that failure while
producing the explicitly authorized diagnostic views. All three processes
exited 0; source hash, six image hashes and guard telemetry are preserved in
`art/nib/v5-study/native-v5e-review-result.json`. The nose now leads the lip by
2.77566 mm, but the grey flat nose, heavy chin and weak brows still fail. Tongue
frame 103 has a large rectangular skin curtain over the mouth. Blink closes
the eyes with bridge-side pinching. No asset is promoted.

The next prepared job is **read-only**:
`native-v5e-mouth-audit.job.json`. It opens the exact saved v5e source and
compares neutral, full Tongue, skeletal-only, morph-only and Jaw-only evaluated
positions. It records source-coordinate regions, weights, highest mouth-edge
stretch, frontmost skin faces and potential upper/lower lip crossings, then
checks that the source hash is unchanged. Its numerical cache stays under
`benchmark/local/`; the small JSON report goes into the art evidence folder.
It completed exit 0 at 590 MB private memory and preserved the source hash.
Jaw-only deformation reproduces the 17.45× edge stretch and pulls the nose/
upper muzzle, while morph-only maximum stretch is 1.36×. Root must allocate
the next guard slot before any repair source or render process starts.

Do not remove faces merely because the closed oral bag has no boundary edges.
Audit the actual upper/lower lip and interior surface domains, and do not
assume that a coordinate threshold describes their topology. The raw-cage
diagnostic already identifies incorrect Jaw influence on nasal/upper-muzzle
probes, but actual saved-pose decomposition is required before choosing the
repair. Preserve v5e and create a separate repaired source with neutral and
extreme expression evidence. Only then resume nose/brow/chin likeness and
the prepared regional groom candidate.

The prepared isolated repair chain is `native-v5f-jaw-repair.job.json`, then
`native-v5f-mouth-audit.job.json`, then `native-v5f-jaw-review.job.json`. These
have now completed with exit 0 and completion markers. The first reads only frozen v5e and refuses to overwrite an
existing v5f candidate. It preserves Basis topology/UVs and bind, solves Jaw
weights from actual upper/lower oral rim domains, restricts residual JawOpen
support and reproduces existing fine-fuzz geometry with corrected deformation.
Unrelated mesh components and expression keys are checked for preservation.
The second repeats the same read-only decomposition against that saved output.
The final explicitly diagnostic views are neutral Face, Tongue and Blink. Any
neutral gate failure stays in their metadata; no automatic artistic acceptance
or shared export follows a successful script exit. The actual Tongue image
confirms that the curtain is gone and the blue tongue is visible; corners
remain boxy, Blink retains bridge-side pinching, and neutral art/gate still
fail. `native-v5f-jaw-review-result.json` records the source/image hashes,
preservation checks and guard peaks. Do not rerun generation over that saved
candidate or interpret this local repair as an engine or likeness pass.


The separate **v5g shape-only recipe is prepared, not yet generated**. It preserves the v5f Jaw repair, eye assembly, mouth interiors, UVs and full scalp/ear groom while proposing a projecting brown nasal pad, continuous muzzle/cheek/chin planes and an upper orbital fold. A lightweight actual-cache check records a maximum 4.94 mm displacement, no new degenerate triangles and no triangles rotating over 90 degrees. The attempted neutral lip-curve contact is explicitly **omitted**: its separate rejected report records 43 lip/oral triangles rotating over 90 degrees. No closure or neutral oral-gate success is claimed. Source job `native-v5g-face-planes.job.json` is followed by explicitly diagnostic depth and Tongue/Blink jobs; all prior source/evidence and shared assets stay fixed. Actual native review is required before any subsequent grooming or export.


The isolated **v5g shape-only source and five actual diagnostic views now exist**. `Nib_Master_v5g_FacePlanes_WIP.blend` has SHA-256 `1586cb3a4c66897be5d1b2c5ba43fdb34a462a6fc96d6d51d90fa417dd185db9`. Generation and depth/expression jobs exited 0 at 715/2621/2651 MB private peaks. `art/nib/v5-study/native-v5g-review-result.json` records exact source, image, metadata and telemetry hashes. Repaired Jaw weights, bind, UVs and 374 unrelated components remain preserved; no contact-curve deformation was applied. Face/profile/three-quarter show raised brown nose volume and an upper orbital fold, with the rounded nose-leading profile retained. **Likeness still fails:** nose response is too glossy, the brow fold is high above narrow eye openings, cheeks/chin remain too smooth, and the unchanged groom/ears/scarf remain inadequate. Tongue retains the real aperture and visible dark-blue tongue without the old curtain, though corners and squint still fail. **Blink is a new expression failure:** a hard nasal/cheek patch appears near the binary nasal-support cutoff. The original v5f source remains a fallback; precise saved-pose attribution and a continuous topology-aware repair are next. The strict neutral oral gate remains false. No PBR bake, FBX export, groom generation, shared promotion or engine claim followed.
