# Actual coherent68 Krag material preparation

All three frozen stages completed with native and guard exit 0: source snapshot, assigned-surface PBR bake, and independent saved-PBR snapshot. The isolated candidate is `4387bd3f…`, derived from the unchanged coherent mouth/motion source `fe15213d…` and current selection contract `7469b7ff…`.

The saved file retains all 26 modules, 68 bones and seven canonical clips. Rig/bind/hierarchy, geometry, skin weights, morphs, point fields, complete corrective-driver definitions, action curves and 17 sampled poses per clip compare exactly with the source. All 104 texture files reopen from the intended relative root, decode, and match their recorded bytes. Seventy-two material-role slots preserve skin/metal distinctions while sharing each module's atlas. This is a provisional material layout, not a measured runtime budget.

The bake used four CPU threads, peaked at 5,497 MiB private memory, and retained at least 6,389 MiB available memory under the unchanged guard. Head color/normal maps are 4096; other skin/Face maps 2048; remaining maps and scalar channels are 1024. Actual object-space skin and optical point fields were baked on their assigned surfaces.

No matching material renders, full five-variant/seven-clip FBXs, engine imports or shared promotion were performed in this boundary. Those gates follow this saved-file proof. The `.blend` and maps remain isolated under the recorded local candidate path; this checkpoint records exact hashes and reproducible recipes. Mouth, face, jaw overlays, hand poses and clothing remain unaccepted, and the separate 72-bone hand study is excluded.

Raw logs, memory CSVs and source/PBR contracts are retained exactly. `result.json` records the measured stage outcomes; `artifacts.json` pins these evidence files. No model or rendering quality approval is implied.
