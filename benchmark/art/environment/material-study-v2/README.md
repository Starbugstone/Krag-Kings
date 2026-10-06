# Sand material v2 — actual source comparison

The four actual Cycles images compare unchanged dune geometry, identical neutral lighting and the previous procedural material against the warmer retained CC0 Sand 03 derivative. V2 adds visible grain and varied roughness while reducing the regular normal ripples. It is a candidate for engine validation, not final art acceptance.

`Dunes_ScanCandidate.blend` is the editable candidate with relative textures beside it. The original Dunes.blend and retained scan/provenance remain unchanged. Source and output hashes are preserved in the receipts. Both guarded jobs exited 0; generation/render peak private memory was 885/1015 MB.

Only the four 2K maps and environment manifest are promoted to shared for actual Unity/Unreal review. Geometry, UVs, character assets, runtime texture dimensions and shader sample count are unchanged. The old shared environment is retained in the ignored local backup recorded by the promotion receipt.
