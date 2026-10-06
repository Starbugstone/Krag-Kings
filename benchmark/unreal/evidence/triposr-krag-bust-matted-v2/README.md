# Actual foreground-matted Krag reference A/B

One authorized, local A/B preserved the original crop RGB, scale and placement while replacing only the rectangular background through a reviewed U2Net alpha mask. The same TripoSR weights, FP16 forward, 256³ field and 4096-position queries produced188,352triangles. All three guarded stages exited0 and all eight actual color/clay views were inspected.

**Limited reference usefulness, not accepted character art.** The plaque is gone. Skull/brow/nose/muzzle/jaw and scarf volumes provide a useful comparison for the concept-visible sculpt. Eyes/lids, tusks, mouth interior, ears and surface detail remain fused, missing or noisy. The inferred rear invents a large armor/backpack-like block and is noncanonical. Do not transplant it as a complete head or replace authored topology/rig.

The second run has valid full-process-tree telemetry: inference peak private5,868MiB, minimum system available8,075MiB, and Torch GPU peak allocation2.53GiB. The first pilot's launcher-only memory limitation remains separately documented. These are reference-generation measurements, not game FPS. No further inference, rig adaptation, shared promotion or engine import occurred.

The review applies a display-only -90degree X correction to undo Blender's glTF Y-up conversion. Original GLB bytes remain unchanged. Both color and clay are inspected, but generated color is not accepted as PBR texture fidelity. Exact input/weights/recipes/output hashes and raw/curated log hashes are retained. The in-inference `backgroundRemoval=false` field means TSR does not repeat the separate reviewed input-matting stage.
