# Preserved coherent Nib export rejection

The matching nontriangulated reference export completed with exit 0. It contains three assembled variants, the full 79-bone rig and seven standalone clips. The subsequent pretriangulated export stopped with native/guard exit 2 before producing a validated delivery: authored hard edges require distinct corner normals, while the earlier helper assumed one normal per vertex.

The failed output and executed recipes are preserved. No normals were smoothed, no tolerance was relaxed and no shared/runtime asset changed. Reference export success is not roundtrip or engine acceptance.

A scoped corner-provenance correction is prepared. Its seven-case numerical fixture passes valid hard-edge/UV seams and rejects changed winding, cross-face aliases, vertices, UVs, materials and missing corners. The native Blender/FBX fixture and corrected full export remain unexecuted at this checkpoint. A new continuation plan will reuse the exact successful bake/reference by hash while keeping this failed attempt intact.

Natural is 750,292 triangles (including 200,582 tagged fur triangles); that is an exporter inventory, not a frame-rate measurement. The source likeness, groom, scarf, neck shading and hand/deformation failures remain open.
