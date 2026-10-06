# Native Nib groom — actual source and isolated engine target

The user requested native fur evaluation. Further card refinement is paused; the prepared `surface_layers_wip` root-blend recipe is retained without execution. Native strands do not yet have an accepted appearance or measured game cost.

## Actual Blender 5.2 fixture

`probe-native-hair-v1.job.json` completed under the existing guard on 6 October 2026. Installed Blender identified itself as **5.2.0 LTS, fbe6228777e7**. Three native Hair Curves objects were saved/reopened and individually exported through Blender's native Alembic writer. Every file contains four curves and 36 points. Native Alembic import returns modern `CURVES`; positions and radii have **zero measured error** for this fixture.

Evidence: `benchmark/art/nib/groom-study/native-hair-fixture-v1/fixture.json`, editable `.blend`, three regional `.abc` files and copied execution records. This is a synthetic interchange fixture, not a character groom, engine import, animation proof or artistic acceptance.

The installed/release 5.2 writer exports positions and per-point standard Alembic widths (`2 × radius`). It **does not export arbitrary `groom_group_id`, `groom_root_uv` or `groom_color` attributes**. The actual readback confirms those attributes are absent. Upstream main already differs; its generic-attribute support must not be attributed to installed 5.2. The first pilot will therefore use separate regional ABCs/materials and explicit binary sidecars.

**Unreal fixture exposed a second limitation:** the 5.2 writer fills the varying width array but never explicitly sets its geometry scope. Unreal's actual importer classified the fixture as constant/uniform and reduced it to one strand width, losing taper. Blender's exact array readback therefore does **not** establish tapered Unreal interchange. The engine agent is investigating an isolated schema/sidecar adaptation. The original fixture files remain unchanged, and per-point radii are also supplied in the character sidecar. No uniform-width import is accepted as parity.

## Frozen character pilot contract

Parent approved the first pilot on `identity-study/neck-junction-native-v1/Nib_Coherent_NeckJunction_v1.blend`, SHA256 `e1cdbd030b8b4de9abd073807e93c40e9d69348e5bcf97c519656f5e3599804b`, matching the current 79-bone engine skeleton. This derivative must preserve all non-groom mesh positions/morphs/weights, bind matrices and seven canonical actions. Existing card render is the control. Only replaced groom groups become hidden in the pilot; they remain preserved in the original source. No shared source is changed.

- Authoring/sidecar: metres, Blender right-handed X right / Y rear / Z up, character faces **−Y**. Object/world and armature transforms are explicitly recorded.
- Native ABC writer maps Blender `(x,y,z)` to `(x,z,−y)`; standard widths are diameters in metres. Engine import must validate scale/axis/radii rather than accept the Unreal 1 cm fallback.
- Sidecar: little-endian float32 position XYZ and radius, int32 curve counts; JSON declares byte hashes, count, axis, units, region and root/point layout. Root surface object, triangle vertex indices, barycentrics, rest UV and inherited bone weights are separate data. Color is explicitly linear RGB.
- Attachment: actual surface deformation must follow ear/ear-tip and facial changes. Native `Deform Curves on Surface` requires a surface object, stable UV attachment, `surface_uv_coordinate` per curve and a surface `rest_position` attribute. Actual save/reopen and posed root error must be measured. Physics simulation is outside this pilot.
- Unreal: separate regional Groom assets initially. `MatchingSection` alone does not exclude existing card geometry from root projection. UE agent is investigating `TargetBindingAttribute` or an isolated matching skin-only target; actual binding remains unverified.
- Unity: root owns its native strand provider. It consumes the same authored curves directly, not newly generated cards. Rendering first is insufficient; skin/ear/facial motion remains a required gate.

Planned coverage remains concept-directed: visible mottled skin and fine fuzz, fuller cream head/inner-rim tufts and tawny ear exterior, visible inner membrane. Density/radius budgets are provisional until actual closeups and RTX 2060 timing/VRAM evidence exist.

## Primary source record

Small upstream source files and URL/hash receipts are under `art/nib/research/native-groom-20261006/`. The installed 5.2 code and actual fixture take precedence over newer upstream APIs.

- [Blender 5.2 Alembic curves writer](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/io/alembic/exporter/abc_writer_curves.cc)
- [Blender 5.2 native Hair Curves API](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/makesrna/intern/rna_curves_api.cc)
- [Blender 5.2 surface-deformation node](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/nodes/geometry/nodes/node_geo_deform_curves_on_surface.cc)
- [Epic Alembic groom interchange](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-alembic-for-grooms-in-unreal-engine)
- [Epic groom scalability and performance](https://dev.epicgames.com/documentation/unreal-engine/groom-scalability-and-performance-with-unreal-engine)

Current status: **native fixture and coherent character source/posed attachment passed; Neutral/Profile inspected with a local fiber-quality improvement but failed overall likeness. Both engine imports and game performance remain pending.**

`generate-native-character-v1.job.json` has now completed guard/native 0. The actual source is `art/nib/groom-study/native-character-pilot-v1/Nib_NativeGroom_Pilot_v1.blend`, SHA256 `0e60a9dbd59a88c64befbf3f05bd543d051d47d23857e31478f3bce8f9ab0cf7`. It contains five native curve regions with 26,000 total strands and 234,000 points. All 422 original mesh payloads, 79 bind bones and existing takes are preserved. Actual rest/Idle/Run/Blink/Tongue attachment plus an isolated ear-tip perturbation has maximum root error **0.419 µm**, with 21.52 mm ear-tip root movement. Saved/reopened and native ABC readbacks pass (maximum position-component difference 0.954 µm, radius difference zero). Sampled process private memory peaked at 1,324 MB.

`neutral-native-character-v1.job.json` and `profile-native-character-v1.job.json` are the bounded first views; their results must be inspected separately. Original meshes remain in the derivative with exact payload hashes; replaced card/opaque head-ear groups are hidden rather than deleted. Existing fine facial/body fuzz remains unchanged in this first pilot. **No engine import, tapered UE interchange, visual acceptance or game-performance claim is implied.**

Both views completed guard/native 0 and were inspected against sheet 02. The head strands are visibly finer and softer and no longer expose broad rectangular card roots. Profile reveals an overly regular straight bob/comb instead of irregular clumped fur. Inner-ear fiber mass and tawny exterior coverage remain insufficient; flat ear geometry, hard tan basal ridges, rectangular retained chin fuzz, facial likeness and scarf remain failed. Root reviewed and showed Neutral to the user as an unfinished first native test. The next boundary is engine rendering/binding, not more card refinement or an accepted character claim.

The common isolated Natural binding target is now generated, triangulated and freshly reimported successfully. See `FILTERED_TARGET.md` and `art/nib/groom-study/native-filtered-target-v1/delivery.json`. It removes exactly the 22 replaced head/ear groom objects, retains 400 original mesh payloads and all rig/action/PBR data, and adds the explicit `KKGroomBindable` alpha attribute. No shared files changed. The separate Unreal width adapter has now passed its actual tiny import and fresh-process reload (maximum per-point diameter error 3.87e−10 cm); that fixes the demonstrated width-scope problem for the fixture, but does not prove character binding or rendering. Both engines must use this same cleaned target and exact native sidecars for their next character test.
