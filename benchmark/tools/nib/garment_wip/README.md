# Nib garment refit — actual staged source, visual review failed

The isolated `Nib_ShirtStrapsStudy_v1.blend` now exists, SHA-256
`70e06992721ac54970392bc96bc3b2f6602da566ee613f4ef1d6e0b8a5e28cf7`.
Generation and Front/Back/Shoot review exited 0, at 599 MB and 1,400 MB
private-memory peaks. The source preserves the exact 79-bone bind and every
action-curve hash from the pinned v5 motion source. It changes clothing only;
the old failed scarf remains visible and unchanged in this partial stage.
`art/nib/garment-study/v1/shirt-straps-review-result.json` records exact source,
recipe, process and image evidence. No shared assets or exports changed.

Actual views fail the clothing review: the shirt extends onto the deltoids,
leaving oversized jagged armholes and a fabric wing under the raised Shoot arm.
The new straps follow the shoulder/back but terminate bare above the belt.
The rectangular bib/pocket and old collar remain visibly inadequate. The next
source must cut a narrow sleeveless edge inside the shoulder and construct
proper strap ends at actual waist/bib anchors. Those changes are not generated.

Use the successful `build-shirt-straps-v1.job.json` only to reproduce this
preserved partial stage. Its script refuses to overwrite the saved source.
The separate old full-garment path still includes the failed scarf pattern;
do not launch it as a presumed correction. A new broad asymmetric overlapping
cowl must be authored from actual posed chin/shoulder landmarks. Root's hand
and action corrections remain independent; do not edit those meshes here.

The 42-frame shirt settle yielded 7,316 vertices / 14,640 triangles. Each fresh
closed strap has 684 vertices / 1,364 triangles. The continuous body route plus
slope-bounded shirt-clearance envelope passes its curvature gate (49.19° and
23.69° maxima). These numerical checks do not approve the garment silhouette.
Closest-body-normal diagnostics find three Shoot shirt samples below −1 mm
(minimum −5.75 mm); they are not watertight collision proofs. Face, groom and
materials remain unaccepted independently of this garment study.

## Preserved preparation and failed attempts

The following records describe earlier preparation or failures; they do not
supersede the actual status above. All five failed attempts remain recorded in
`art/nib/garment-study/v1/failure.json` with preserved scripts/logs.


The v5-pinned native attempt completed all 42 undershirt cloth frames, then
stopped at the shoulder-strap fitting gate: old-to-new radial support requested
more than 35 mm of displacement. No new source was saved or rendered. The
threshold remains unchanged. `art/nib/garment-study/v1/failure.json` preserves
the source identity, two process exits, final logs, code snapshots and memory.
The next repair needs local shoulder correspondence that preserves strap
thickness and layered placement; collision and appearance remain unverified.

This is source preparation only. No new shirt, scarf, settled fabric or garment
source has been generated. The new actual anatomical body exposes clipping in
the old sleeveless tube, shoulder straps and rigid scarf layers. Its neutral
and twist images are preserved in `art/nib/motion-study/anatomical-body-v1-renders`.

The next candidate must derive from the actual 79-bone captured-motion source,
preserving head/Jaw/eyelid geometry, dark-blue tongue, ears, body shape, joints,
hands, sole geometry and every action. It changes garment surfaces and their
skin attachment only. It must not translate anatomy to hide clothing defects.

`cloth_patterns.py` prepares a connected sleeveless undershirt from the actual
anatomical control cage. Its source-domain trim produces exactly four closed
boundary loops: neckline, waist and two arm openings. A light numerical check
on the same licensed raw cage retains 870 quads and four loops, with every
boundary vertex degree two. This is a topology check, not a native cloth test.
The boundary is relaxed before fitting at measured clearance against the actual
subdivided torso; neck/shoulder pins retain hanging cloth rather than rigidly
pinning the whole front. The waist remains aligned with the retained belt.

The scarf proposal is one continuous 2.45-turn open textile sheet with unequal
front sag, diagonal fold bias and rear/tuck pins. It replaces the three separate
annular collar layers. Initial placement must be checked against actual body,
head neck, undershirt and shoulder-strap colliders before a bounded physical
settle. Keep the pink ears and face clear. Do not widen a failed placement gate
to force a floating shape through. The final solver geometry needs real fabric
thickness and hem edges, then smooth Chest/Neck skin attachment without Jaw.

After the shirt fits, move bib/pockets/seams and crossed straps through a shared
support-surface displacement field. Preserve their relative layering and UVs;
refit buckles rigidly rather than bending their metal. The bib should retain the
concept's tapered canvas front, constructed pocket/flap and side attachment,
with folds driven by shoulder-strap and belt tension. A simple offset of the
whole old bib will not establish cloth quality.

Required actual review: front, three-quarter and back at neutral, then captured
Walk/Run extrema and Shoot. Check chest penetration, open armhole edges, strap
fit under shoulder motion, scarf neck/head motion and back crossed straps.
Record actual contact distances and source hashes. Keep the old garment source
as a fallback and do not export while those views fail.

After geometry, use the retained CC0 leather and textile scans with documented
physical scale, recolored into the concept's brown/tan palette. Dust/wear and
seams must follow garment regions. This preparation does not introduce blue
jeans, new equipment or approved new canon.

The executable candidate recipe and guarded source/review jobs are now prepared
and syntax checked, still unexecuted. They pin the actual v5 captured-motion
source (SHA b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da).
The v5 gaze calibration is already present and must remain unchanged by the
neutral fabric solve.

The prepared source applies 42 bounded cloth frames to the undershirt and 49 to
the wrapped scarf, retaining editable pre-solve patterns. It refits the existing
bib/pockets/seams/straps through old-to-new support-surface displacement, moves
buckles rigidly, and binds fabric to the anatomical surface. It preserves exact
bone matrices and original action-curve hashes. Front/Back/Shoot diagnostic
jobs retain signed nearest-body contact metrics alongside the actual images.
These are prepared checks, not results. Generation is limited to 4 GiB private
memory and review to 3.5 GiB, each requiring 8 GiB free headroom under the shared
guard. No process may start without the explicit heavy-slot handoff.

The numerical initial-pattern receipt is
`art/nib/garment-study/pattern-preparation-v1.json`: shirt 958 vertices / 870
quads / four closed loops; scarf 4,560 vertices / 4,302 quads, no zero corner
areas and all sampled initial normals facing radially outward. It does not
establish self-intersection clearance, solver stability or an actual cloth
appearance. Those require the queued native generation and review.


The second measured failure is preserved separately: the old back-shoulder
control lies **inside** the new body. Unconstrained nearest support returns
front-facing skin, so copying that displacement would route leather through
the torso. `strap-support-v5.json` records the actual saved Basis triangle,
normal and signed distance (−29.275 mm), not a proxy.

The next prepared recipe intentionally replaces both obsolete strap meshes
with closed 19 mm-wide / 3 mm-thick rounded leather ribbons. Front/shoulder
crest/back directions select exterior actual shirt/body surfaces; no inside
point may choose the opposite side. The crossed back has separate leather
layer clearance. Old straps stay hidden in the preserved collection. New
routing records support triangles, local clearances, curve lengths, per-row
routing changes and curvature. This is an authorized clothing fit, not a body
or canon change; the failed 35 mm old-mesh preservation assumption is no
longer applied to the intentionally rebuilt straps. A separate 90 mm region
bound and 70-degree adjacent-segment rejection catch routing jumps. These are
conservative authoring guards, not artistic acceptance. Native review remains
required. No new source from this recipe has yet been generated.


The fresh directional route's first native attempt also stopped before saving:
independent farthest-hit selection between shirt and body produced a112.23°
local kink. The actual saved-body-only route measures24.34° maximum, so the
anatomical routing is coherent; the surface-switching rule is the defect.
`strap-route-continuity-v5.json` preserves every body support row and the worst
measured angles. The next ungenerated correction retains that single body
route and adds a slope-bounded local shirt-clearance envelope, with per-row
support/offset diagnostics written before the curvature gate. It does not
relax the curvature gate or move anatomy. All failed native attempts remain in
`art/nib/garment-study/v1/failure.json`.


## Prepared v2 sewn shirt and completed strap routes

The separate v2 recipe remains ungenerated. `sewn_undershirt_v2.py` constructs
front/back panels, sewn lower sides and narrow shoulder bridges instead of
cropping a shoulder-shaped sleeve from the anatomy. Its numerical layout has
5,468 vertices, 5,308 quads and exactly four closed openings, with no zero
first-corner face area. `torso_fabric_v2.py` projects those guides onto actual
body triangles with a low anatomical arm-domain value, then transfers portable
LBS weights from the same torso region. Actual cloth settling and pose proof
remain necessary; a topology check is not a successful garment.

`shoulder_straps_v2.py` extends the crossed back straps to measured points on
the actual utility belt with a smooth final attachment adjustment. Source job
`build-shirt-straps-v2.job.json` and `review-shirt-straps-v2.job.json` preserve
the v5 input, all 79 bone binds, all action curves and independently hashed
body/head/hand data. They write only separately named v2 study outputs. Current
v1 sources and shared exports stay unchanged. No new cowl or groom is included
in this bounded correction; both remain separate pending construction work.

The remaining clothing list also includes loose cargo/overall trousers: the
current tight hips/thighs and separate briefs-like pelvic contour fail the
reference. Root owns the current hand reconstruction and animation changes;
those will be merged into a coherent reviewed garment source by exact bind.


Cowl construction note after directly viewing Krag's actual v9md Front: its
clearance footprint is informative, but its monotone vertical sheet with two
radial Gaussian bumps reads as a regular U-shaped bib with ledges. Do not copy
that cross-section as accepted Nib cloth. The next Nib cowl needs overlapping
free fabric edges and folds with real returned cross-sections, unequal diagonal
sag and broad relaxed flats. Measure the actual posed chin and shoulder support
first; keep the exposed face clear, and never lift the front rows wholesale to
shoulder height. A later rest-surface pass may use bounded conformance, with
physical settling refining folds only after the intended silhouette exists.
This is a construction plan, not authored or rendered new scarf geometry.


### V2 actual initial failure and corrected support preparation

The first native v2 attempt stopped before simulation/save at a missed hem ray
(PID 16248, exit 2). The exact executed recipe is preserved in
`art/nib/garment-study/v2/failed-initial-ray`, reconstructed where necessary and
verified byte-for-byte against the prelaunch readiness hashes. All actual logs
are retained. A complete lightweight actual-mesh audit found 356 ray misses:
most are loose hem/side guides outside the curved waist, while two original
shoulder bridge guides entered the neck. No full cloth solve was repeated to
locate those errors.

The corrected sewn guide uses measured shoulder/neck placement and actual
nearest torso support with explicit 8–12 mm cloth ease. A maximum 4 mm tangential
support residual prevents boundary collapse; interior fairing is capped at 2 mm
and fixes every opening edge. The complete saved-mesh numerical check now
covers 5,342 vertices: maximum fitting correction 38.15 mm, zero collapsed or
backfacing faces, minimum fitted/support normal dot 0.920. These are preparation
checks, not a native cloth or visual pass. `audit_sewn_nearest_v2.py` reproduces
them from `local/nib-actual-v5-body.json`, which is made by the read-only DNA
extractor with `--mesh-name 'Continuous Nib anatomy organic'` on the pinned v5
source. All scripts use the actual cached Basis and weights; the native fitter
reads the retained Nib_ArmDomain attribute directly and repeats geometry gates.

`build-shirt-straps-v2-support-retry1.job.json` is the single prepared corrected
native retry. Its logs are separate from the failed attempt. Source geometry,
physical settling, fitted belt anchors and Front/Back/Shoot appearance still
need actual native proof. `sewn-retry-readiness-v2.json` pins the current recipe
and complete support report. Earlier numerical layouts/receipts are historical
and do not establish that the current source was generated.


The corrected support recipe subsequently completed all 42 native cloth frames,
then stopped before saving because the final strap row requested bare-body
support below the body mesh's cropped waist. This is a distinct belt-attachment
fault; its exact source/logs are in `v2/failed-belt-support`. The prepared fix
uses the measured belt triangle and normal for that final row. The lightweight
`audit_strap_v2_all_support.py` executes the exact current route prefix through
all 65 rows on both sides, using actual saved body/belt geometry and the actual
settled-shirt cache. Both routes pass the existing curvature and clearance
gates (49.06° / 47.06° maximum bend); no native rerun or visual approval is
implied. `build-shirt-straps-v2-belt-support.job.json` is ready and additionally
saves an editable partial shirt checkpoint before accessory work.

Root has now identified a left-hand digit-proportion/bind defect and owns its
isolated anatomical correction. This clothing study retains the original v5
bind. A future coherent source requires that explicit migration once, followed
by matching clip regeneration; do not casually transfer old clips across the
changed hand bind. Earlier exact-bind merge planning is superseded for those
changed hand joints. No hand or body geometry is edited by this garment work.


### Actual v2 bounded review complete

The belt-supported native source and Front/Back/Shoot now exist, guard exit 0
with 766 / 1,401 MB private peaks. Exact evidence is in
`art/nib/garment-study/v2/shirt-straps-review-result.json`. Shoulder exposure and
belt attachment improve; the raised-arm sheet persists and requires the
prepared `review-underarm-owner-v2.job.json` attribution. Thin jagged openings,
pinched side folds, old scarf and larger character-quality failures remain.
Keep this actual source fixed for diagnostic groom composition and root's
future explicit anatomical hand migration. No shared promotion is authorized
by these technical checks or images.
