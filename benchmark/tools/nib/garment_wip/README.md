# Nib garment refit — first native attempt failed

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
