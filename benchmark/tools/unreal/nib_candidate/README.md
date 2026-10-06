# Isolated coherent Nib PBR/FBX preparation

The newest actual neck/fine-atlas source `e1cdbd03…` now has a fresh saved PBR
candidate `fee71393…`. Its 102 maps reopen/decode/hash correctly, all 79 bones,
seven actions and source geometry/weights/morphs match, and eight matched
Face/Tongue/Front/EyeCloseup images were inspected without an obvious new
material-transfer regression. See the [actual current evidence](../../../unreal/evidence/nib-coherent79-neck-pbr-v1/README.md).
The frozen plan is `plans/nib-coherent79-neck-e1cdbd-v1`. Its reference export
completed (three variants, 79 bones, seven standalone clips), but explicit
triangulation stopped with exit 2 because the new source has authored split
corner normals. See the [preserved export failure](../../../unreal/evidence/nib-coherent79-export-corner-failure-v1/README.md).
The corner correction now passes a real Blender/FBX hard-edge fixture and the
full corrected pipeline in `plans/nib-coherent79-neck-corners-v2`. All three
variants and seven standalone takes pass fresh 79-bone roundtrips; mapped
normals are exact and maximum dense morph rounding is 0.839241µm. See the
[actual technical delivery](../../../unreal/evidence/nib-coherent79-corners-v2/README.md).
`prepare_export_resume.py` creates a fresh attempt that pins
the completed bake/reference receipts and outputs without rebaking or replacing
the failed attempt. The verified payload is now technically promoted with an
exact previous-payload backup and explicitly recorded provenance normalization.
Current engine import and artistic acceptance remain pending.


The original saved-path failure and v2 Windows-basename validation failure are preserved. Path-only v3 candidate `2a3ab470…` now passes reopened98-map path/hash/color/decode checks and exact79-bone/seven-action/mesh parity. All three matched baked views were inspected against the original source, without an obvious new material-transfer regression. [Actual repair/parity evidence](../../../unreal/evidence/nib-coherent79-pbr-path-repair/README.md) contains the images and failures. No maps were rebaked and shared assets remain unchanged.

`plans/nib-coherent79-socket-pathfix-v3` preserves the executed 194-input plan.
Its `repair-paths` stage copied exact map bytes from the earlier socket bake.
That older source is not the next export target: the newer adult face and
anatomical iris require a fresh actual-surface bake. Full 79-bone mesh/seven-clip
exports and actual engine imports remain required after the next coherent-art
handoff. This technical check does not approve likeness, anatomy, groom or
hand/clothing.

The first source snapshot and bake belong to
`plans/nib-coherent79-socket-1b992e-v1`, pinned to the corrected socket/wrist
source `1b992ebb4f759fadae2a602006c1a691d8be37d2951142bed470a1a283a20732`.
Its original execution and saved-path failure remain preserved; do not rerun
or reinterpret it as a successful new-source delivery.

The frozen diagnostic plan pins source `ba0048d08f351c9876a947bd88cc366936cac4fa1ea50ed2aeb17db23e5174be`, its actual source report, all original groom atlases/reference maps and the recipes. That source's actual Grip views fail the wrist gap and retained-skin/cuff interface. `executionReady` is false and the stage runner refuses it. After the artist supplies the corrected saved source and receipt, create a **new** plan/output name with those exact hashes; preserve this diagnostic plan. Heavy execution still follows the parent agent's explicit serialized job grant.

`prepare_plan.py` writes ten separate guarded jobs. It launches no process. The existing PBR/export scripts remain the implementation, with explicit paths overriding their old defaults. Every stage verifies frozen inputs and completed dependency hashes, preserves previous outputs, and requires its fresh completion marker. All output stays below `benchmark/local/candidates`; shared assets and current packages are untouched.

For the next source, pass its actual atlas directory through
`--card-texture-dir`. The prepared bake gate follows connected source shader
images and requires their exact hashes to match those supplied files, including
packed-image bytes and linked-library paths. Reusing older map filenames is not
sufficient. These gates and the actual-iris adapter now pass the executed
e1cdbd source bake and reopened-image checks. Older frozen plans and executed
recipe hashes remain unchanged.

The prepared `review_pbr_optical.py` adds a separate matched EyeCloseup pair
after the saved-PBR snapshot. It uses the exact existing adult-review camera:
1500 × 900, 0.18 m orthographic span, centered between the two animated eye
bones with the same camera offset. Both inputs, both review recipes and the
saved snapshot outputs must be pinned. This supplements Face/Tongue/Front so
the new actual-iris atlas can be judged at useful scale. The actual e1cdbd
source/baked optical pair has been inspected; no obvious new field-transfer
regression was seen, while source likeness remains failed.

1. `snapshot-source`: capture exact 79-bone hierarchy/bind, canonical action curve hashes, geometry/weights/morph payloads, contracts and 17 skeletal poses per take.
2. `bake`: use the existing PBR bridge, retaining the original masked-card RGBA bytes. The actual face attribute is baked on its geometry; UV-only regions use the existing carrier bake.
3. `snapshot-pbr`: reopen the actual saved bake and demand unchanged rig, seven actions, geometry, weights, morphs and groom/deformation contracts. UV/material changes are expected.
4. `reference`: export all three full variants and seven standalone clips into a fresh local reference directory. New topology must never use the old shared FBX as its shading reference.
5. `triangles`: export the identical PBR source into a separate pretriangulated candidate, using that matching reference. Retain corrected morphs; do not enable the historical baseline-morph restoration flag. Check portable texture paths and original card atlas hashes, then bind the existing strict clip validator to these actual exports.
6. `validate-payload`: independent raw FBX comparison checks unchanged indexed points/morphs, mapped UV/material corners and normals, with all-triangle topology.
7. The three `validate-variant-*` jobs each start fresh and check the full 79-bone source bind/hierarchy, units, normalized skin, nonzero required morphs, material/UV contracts and all seven embedded takes at 17 source poses.
8. `validate-clips`: the existing strict motion validator compares all seven actual standalone clips against the full Natural bind and saved source poses, including duration, scale and varying facial controls.

Each Blender job uses four threads, an 8 GB private-memory cap, 10 GB available-memory preflight and Python failure exit code 2. No cap increase or automatic retry is included. Process boundaries allow interleaving scheduled art work.

Candidate/PBR file hashes now stream in 1 MiB chunks instead of allocating a
second entire source or FBX payload. All nine helper implementations compile
and reproduce the exact committed reference GLB digest. This limits transient
hashing allocations; it does not reclaim OS file cache or establish a new
native bake/import memory measurement. Executed older recipes stay preserved.

The full-mesh and standalone validators restore only source `use_connect` flags inside the disposable Blender import, recording unchanged bind matrices. Installed Blender infers connected edit bones and can otherwise suppress correctly exported pelvis/tongue translation. This normalization does not change any FBX or promise engine parity.

Required follow-up after structural checks: actual matched source/baked Face, Tongue and full-body views; map/alpha/mip inspection; fresh UE Nib skeleton migration because the inserted twist bones change Hand parents; isolated Unity and UE imports; actual pose/ear/skin/fur review and measured performance. The existing cloth, mouth, axilla, right-hand grip and likeness failure gates remain. A technically valid export cannot close them.
