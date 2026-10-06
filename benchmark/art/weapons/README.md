# Krag weapon exterior studies

The regular Krag in concept sheet 10 is the reference. These isolated Blender studies are provisional exterior art; neither is an accepted or exported shared asset.

- `study-v1`: actual source and three renders. Review rejects visible cylinder faceting, plain box construction and sparse wear.
- `study-v2`: actual source and three renders, 34,556 triangles. Smooth shading, round shroud perforations and layered panels improve the first study. It still needs stronger material wear and equipped review. The fitted grip core retains the v9f hand dimensions; raised bindings need contact checks.

The [actual equipped v2b study](study-v2/equipped-review.json) is saved on a separate v9f character copy and has two inspected Shoot-frame renders. The first integration failed visually because appended objects exposed stale transforms; both failed source and images are preserved. A dependency update before reading transforms fixes that fault. The corrected rigid transplant preserves 17,608 vertex positions within 0.172 micrometers, leaves unrelated bind matrices unchanged and keeps the visible muzzle within 0.623 micrometers of its socket in 21 samples across seven clips. The socket derives from the visible mesh, correcting the separate prop's earlier 2 mm reference-empty offset.

The gun now stays connected and fits the existing grip in the inspected firing pose. Full hand-contact/intersection review and other posed views are still incomplete; surface wear remains too clean. No shared export or artistic acceptance is claimed. `tools/weapons/equip_krag_weapon_study.py` and the v2b jobs reproduce the corrected isolated integration; repeated runs require a fresh output to preserve evidence.

Original sources and individual image hashes are retained in each `study.json`; independent findings are in `visual-review.json`. Existing character masters, exports and both engine packages are unchanged by these studies.

`tools/weapons/refine_weapon_surfaces.py` and `surface-study-v3-job.json` prepare a separate material-only study with irregular roughness, fine abrasion and geometry-dependent seam/edge wear. It has not run in Blender yet. These fields require a unique actual-mesh PBR atlas before export; the existing tiled-material bake is insufficient. Geometry and source preservation checks are part of the prepared job.
