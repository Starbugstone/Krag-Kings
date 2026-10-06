# Post-v9f studies — ungenerated

The frozen `v9f-prepared-recipe.json` does not import this directory. Its actual four initial views are now recorded in `v9f-source-review.json`: head proportions and grip improve, while face and scarf still fail. This separate wrapper has not run. Neutral Front/Head and profile must be reviewed early, followed by Blink/OpenMouth and raised-arm cloth clearance; these preparations do not imply a completed mesh or artistic acceptance.

The approved sheet still differs from actual v9f in these major ways:

- The paired brow must carry heavy bony pads into a short projecting nasal bridge. Current face reads smooth and shallow. Preserve the working ocular fit; every fit change must apply to the eyes, mouth, control pivots and morph fields together.
- A broad muzzle needs a visible nasolabial fold and flatter cheek-to-jaw planes. The lower lip must not become the principal projecting cushion. Bring the continuous mandibular/chin volume forward instead. `face_planes.py` prepares that study on the existing continuous topology; numerical amounts are provisional.
- The exposed tusks are too small. The current 34 mm pre-transform tooth is largely buried under the upper muzzle. The prepared curved 58 mm tooth restores more visible ivory, but closed/open-mouth fitting must be reviewed before accepting it.
- The shoulder armor needs distinct overlapping steel plates with visible stepped edges, angular clipped corners, local formed rims and attachment straps. The current broad ellipsoidal shell hides the layer construction. Retain the approved teal scrap-metal identity; avoid adding unrelated spikes or motifs.
- The new v9f scarf must show broad cloth flats separated by irregular folds. Check front, side and back silhouette and raised-arm clearance before weave/detail. An apparent soft material cannot rescue a tubular or intersecting surface.
- Hands need isolated digit weighting, correctly seated knuckles and a compact wrapped grip. V9f refits actual source centers and fields. If the distal finger still looks rigid, retain a later third-phalange joint requirement rather than masking it with tip-only IK.
- Trousers need real baggy ease above boots/knees, shaped side cargo pockets, belt loops and asymmetric tension folds. Current smooth straight legs and flat patch pockets do not match the sheet.
- Boots need a constructed tongue, overlapping vamp/quarter panels, stitched leather seams, thicker ankle straps and worn metal toe-cap edges. Preserve the useful low ground-contact sole and avoid the old spherical steel toes.

Material detail follows those silhouettes and construction. The retained CC0 woven cloth/leather sources can contribute actual weave/grain and roughness after tinting and physical-scale fitting. The face needs quieter central microstructure with shaped creases, then larger broken skin scales outside; simply copying one cracked-mud tile over the whole character is not a likeness solution.

The firearm's capped bore and absent trigger/guard are recorded for a later prop-construction pass. The exact visible bore/socket alignment must remain checked after every geometry or mount change.

`build_v9g.py` applies in-memory overrides to the unchanged v9f generator: one common facial fit for skin/eyes/oral/control coordinates, replacement curved tusks, and `scarf_cloth.build`. The wrapper and exact patch sources are embedded into the final saved study. The existing firearm and v9f hand/proportion helpers are unchanged; root owns a separate reviewed weapon replacement.

The cloth helper prepares one broad asymmetric wrapped sheet, with diagonal unequal folds, rear-neck/shoulder tuck pins, 54 frames of gravity, self-collision and copied actual body/head cage colliders. It checks finite geometry and neck/chest bounds, applies the simulated mesh, then adds subdivision and physical thickness. These solver settings are provisional and unexecuted. They do not prove natural drape, no intersections or animation clearance. The failed terrace scarf remains preserved in v9f.
