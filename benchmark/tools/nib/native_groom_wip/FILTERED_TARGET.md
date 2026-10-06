# Verified isolated Natural target for native groom

All six required stages completed under the guard with native/guard exit 0. Exact outputs and execution evidence are retained at `benchmark/art/nib/groom-study/native-filtered-target-v1`; `delivery.json` identifies the source, FBX, manifest, reports and original native groom. The frozen plan and original local receipts remain unchanged. This is a technically verified isolated target; engine binding and artistic acceptance remain unverified/failed respectively.

The common engine entry point is `native-filtered-target-v1/triangulated/manifest.json`, listing **Natural only**. Actual FBX: 295,931 vertices, 570,134 triangles, 79 bones, 25 morphs and all seven embedded takes. Raw corner normals are exact; UV/material correspondence passes. The added eligibility layer survives with exactly 51,374 eligible skin vertices and 244,557 excluded vertices. Fresh FBX readback checks 17 frames per take, all hierarchy/bind/material/morph/weight gates, and unchanged source bounds. Existing standalone clip bytes are reused unchanged. The largest sampled private-memory usage was 2,432 MB in triangulation.

Do not use raw FBX vertex coordinates as world positions: the source mesh transform contains the existing −32 mm translation. The imported world bounds and recorded source anchors are the coordinate authority; each engine must verify its actual actor mapping.

Input is the technically verified PBR derivative `art/nib/runtime-derivatives/coherent-neck-e1cdbd/Nib_Runtime_PBR.blend`, SHA256 `fee71393f1a41355e309994118656494b320f1284f995259a5362fa82db0b4b1`. Its maps and baked UVs already match the currently integrated Nib. The native source remains frozen at `0e60a9db…`; its original e1cdbd skin coordinates, canonical79 rig and takes are unchanged.

The isolated derivative removes exactly the **22 names** recorded in native `source.json.hiddenControlGroom`. Every retained mesh/UV/morph/weight, original vertex color layer, bone bind and action curve is checked before and after save/reopen. No facial/body fine fuzz or failed character anatomy is silently redesigned. Texture bytes are reused, not rebaked.

For Unreal root projection, one explicitly additive non-shading POINT `FLOAT_COLOR` layer named **KKGroomBindable** is added: RGB zero; alpha one on the actual Head/outer-ear skin objects used by the five native regions, alpha zero elsewhere. Existing color layers remain exact. Actual raw FBX eligibility must survive triangulation, and Unreal must prove its imported attribute buffer before using `TargetBindingAttribute`. `MatchingSection` alone is insufficient to exclude other nearby surfaces.

Before export, every native root is reconstructed from its recorded triangle indices/barycentrics against the proven PBR source and compared within 1 µm. A coordinate receipt retains the complete 79-bone bind, world transform, thirteen anatomical/socket anchors, FBX axis/unit settings and current shared Natural reference hash. Final engine actor mapping is **unverified** until Unity/Unreal compare actual imported anchors; no handedness flip is guessed.

The completed reproducible stage sequence is:

1. `filtered-source-v1.job.json`: filtered source and save/reopen/root correspondence gates.
2. `filtered-snapshot-v1.job.json`: exact source plus 17 skeletal samples per take.
3. `filtered-reference-v1.job.json`: isolated Natural FBX, byte-identical reuse of the previously verified seven standalone clips, unchanged PBR maps.
4. `filtered-triangles-v1.job.json`: disposable source-corner triangulation against its own matching filtered reference.
5. `filtered-payload-v1.job.json`: raw points/morphs/corner normal/UV/material parity and exact eligible color mask.
6. `filtered-variant-v1.job.json`: fresh actual Natural FBX bind/morph/material/pose readback.
7. `filtered-clips-v1.job.json` is optional only if new evidence warrants repeating standalone checks. The current plan reuses their exact pinned bytes after saved bind/action comparison, so no new standalone animation export is required. Full target roundtrip still checks the seven embedded takes.

Output is `benchmark/local/candidates/nib-native-groom-filtered-v1`, outside `shared/`. The new optional `export_nib.py --variants natural` limits this technical pilot to Natural; the default still exports all three Nib variants. `--reuse-animations-from` is candidate-only and requires the exact original exported source hash, preserved source rig/actions, matching canonical bone list, locomotion and animation-completion metadata/ranges before copying bytes. No shared promotion, complete-fur claim, visual acceptance or runtime binding claim is implied by prepared code.
