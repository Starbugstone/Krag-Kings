# Common filtered Nib target — native fur pilot

The six actual source/export/validation stages passed on 6 October 2026. This isolated **Natural-only** target removes exactly the 22 old head/ear card and opaque groom groups replaced by the frozen 26,000-strand native groom. All 400 remaining source mesh payloads, baked UVs/maps, 79 bind bones and seven actions remain preserved. The additional non-shading `KKGroomBindable` color attribute marks only the actual head and two ear skin surfaces.

Use `triangulated/manifest.json` with the native source/ABCs/binary sidecars in `../native-character-pilot-v1`. `delivery.json` records every retained file hash, full coordinate/bind anchors, the source lineage and validation limits. The full FBX is SHA256 `3f15ce613f116122bc756b442d5d3742ac2361c9fc405bc3789eb4f4dfe2f32a`; its manifest is `fcb616ecb5d2dadf3b33d8619573faace0e4e36caa11d2462dde82cff6e04904`.

- 295,931 vertices, 570,134 triangles, 25 morphs and 79 bones.
- Exact mapped corner normals; UV/material correspondence preserved; morph rounding remains below 1 µm.
- Actual FBX mask contains 51,374 eligible vertices and 244,557 ineligible vertices, with exact binary alpha and zero RGB.
- Fresh FBX import checks all seven embedded takes at 17 frames each. The seven standalone files are exact copies of the previously verified canonical exports.
- Source native roots still reconstruct against the PBR skin within 0.174 µm.
- Peak sampled process private memory: 2,432 MB; all native and guard exits were 0.

Raw FBX positions include a mesh-local offset; use actual imported transforms and the source anchors before attaching strands. Engine attribute-buffer import, actor mapping, animated groom binding and frame cost remain pending. The native curves are external to the FBX.

This is not an artistic acceptance or shared promotion. Retained defects include facial likeness, clothing, hard basal ear ridges and fine facial/chin control groom. The native groom itself still needs irregular clumped flow and more concept-consistent ear-border coverage. Original local files, frozen recipe, reference export and all evidence are preserved.
