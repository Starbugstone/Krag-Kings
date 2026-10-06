# Krag weapon exterior studies

The regular Krag in concept sheet 10 is the reference. These isolated Blender studies are provisional exterior art; neither is an accepted or exported shared asset.

- `study-v1`: actual source and three renders. Review rejects visible cylinder faceting, plain box construction and sparse wear.
- `study-v2`: actual source and three renders, 34,556 triangles. Smooth shading, round shroud perforations and layered panels improve the first study. It still needs stronger material wear and equipped review. The fitted grip core retains the v9f hand dimensions; raised bindings need contact checks.

`tools/weapons/equip_krag_weapon_study.py` is a prepared, unexecuted source-copy integration. It archives the original weapon, attaches the separate mesh to `Hand_R`, derives sockets from the visible muzzle lip and checks original bind bones and seven action samples. The v2 source's inherited muzzle empty is 2 mm behind the new front lip, so it must not be used as the new socket position. Two guarded Shoot-view jobs are prepared for the resulting source. Syntax checking does not establish that this integration works.

Original sources and individual image hashes are retained in each `study.json`; independent findings are in `visual-review.json`. Existing character masters, exports and both engine packages are unchanged by these studies.
