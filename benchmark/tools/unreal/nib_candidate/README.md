## Latest actual boundary

The original bake and saved structural snapshot pass. Matched source Face/Tongue/Front renders completed, but the first reopened baked frame fails: all98 texture paths resolve under the old source directory. [Actual failure and images](../../../unreal/evidence/nib-coherent79-pbr-reopen-failure/README.md) are preserved. No FBX/engine import occurred.

`plans/nib-coherent79-socket-pathfix-v2` is a new frozen194-input plan. It replaces `bake` with `repair-paths`, preserving the failed file and reusing all98 map bytes. The common save helper disables relative remapping, reopens and decodes each connected image, and validates its path, content hash and color space. A separate source/PBR snapshot still checks exact rig/action/geometry parity before export. This correction is prepared, not yet executed.

# Isolated coherent Nib PBR/FBX preparation

The first corrected-source snapshot and portable PBR bake now pass actual
guarded execution. See [the execution evidence](../../../unreal/evidence/nib-coherent79-pbr-first-bake/README.md).
Saved-PBR reopening, matched images, FBX exports and engine imports remain pending;
there is no artistic acceptance.

The next scheduled plan is `plans/nib-coherent79-socket-1b992e-v1`, pinned to the
actual corrected socket/wrist source SHA `1b992ebb4f759fadae2a602006c1a691d8be37d2951142bed470a1a283a20732`.
Its three source views remove the large wrist gap/exposed stump; character art
and natural grip remain unaccepted. This plan is eligible for the coordinated
technical bake boundary, with no shared promotion or engine build authorized.

The frozen diagnostic plan pins source `ba0048d08f351c9876a947bd88cc366936cac4fa1ea50ed2aeb17db23e5174be`, its actual source report, all original groom atlases/reference maps and the recipes. That source's actual Grip views fail the wrist gap and retained-skin/cuff interface. `executionReady` is false and the stage runner refuses it. After the artist supplies the corrected saved source and receipt, create a **new** plan/output name with those exact hashes; preserve this diagnostic plan. Heavy execution still follows the parent agent's explicit serialized job grant.

`prepare_plan.py` writes ten separate guarded jobs. It launches no process. The existing PBR/export scripts remain the implementation, with explicit paths overriding their old defaults. Every stage verifies frozen inputs and completed dependency hashes, preserves previous outputs, and requires its fresh completion marker. All output stays below `benchmark/local/candidates`; shared assets and current packages are untouched.

1. `snapshot-source`: capture exact 79-bone hierarchy/bind, canonical action curve hashes, geometry/weights/morph payloads, contracts and 17 skeletal poses per take.
2. `bake`: use the existing PBR bridge, retaining the original masked-card RGBA bytes. The actual face attribute is baked on its geometry; UV-only regions use the existing carrier bake.
3. `snapshot-pbr`: reopen the actual saved bake and demand unchanged rig, seven actions, geometry, weights, morphs and groom/deformation contracts. UV/material changes are expected.
4. `reference`: export all three full variants and seven standalone clips into a fresh local reference directory. New topology must never use the old shared FBX as its shading reference.
5. `triangles`: export the identical PBR source into a separate pretriangulated candidate, using that matching reference. Retain corrected morphs; do not enable the historical baseline-morph restoration flag. Check portable texture paths and original card atlas hashes, then bind the existing strict clip validator to these actual exports.
6. `validate-payload`: independent raw FBX comparison checks unchanged indexed points/morphs, mapped UV/material corners and normals, with all-triangle topology.
7. The three `validate-variant-*` jobs each start fresh and check the full 79-bone source bind/hierarchy, units, normalized skin, nonzero required morphs, material/UV contracts and all seven embedded takes at 17 source poses.
8. `validate-clips`: the existing strict motion validator compares all seven actual standalone clips against the full Natural bind and saved source poses, including duration, scale and varying facial controls.

Each Blender job uses four threads, an 8 GB private-memory cap, 10 GB available-memory preflight and Python failure exit code 2. No cap increase or automatic retry is included. Process boundaries allow interleaving scheduled art work.

The full-mesh and standalone validators restore only source `use_connect` flags inside the disposable Blender import, recording unchanged bind matrices. Installed Blender infers connected edit bones and can otherwise suppress correctly exported pelvis/tongue translation. This normalization does not change any FBX or promise engine parity.

Required follow-up after structural checks: actual matched source/baked Face, Tongue and full-body views; map/alpha/mip inspection; fresh UE Nib skeleton migration because the inserted twist bones change Hand parents; isolated Unity and UE imports; actual pose/ear/skin/fur review and measured performance. The existing cloth, mouth, axilla, right-hand grip and likeness failure gates remain. A technically valid export cannot close them.
