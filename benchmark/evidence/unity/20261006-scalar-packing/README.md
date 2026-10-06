# Nib PBR bridge: scalar resolution correction

The prepared Nib face bake uses 1024² roughness and 128² metallic maps; several region bakes use 512²/128². Unity previously rejected different array lengths while packing its HDRP mask. Unreal samples those maps separately and did not have this restriction.

The Unity importer now retains the full roughness dimensions and samples **linear metallic values** into that output. Constant metallic maps retain their exact value. Equal-size maps retain their existing samples; other sizes use pixel-center bilinear interpolation with clamped atlas boundaries. Smoothness still comes from `1 - roughness`; AO/detail remain one. Actual import logs will record both input dimensions and the output dimensions. Source textures and original masked RGBA atlases are untouched.

The [actual production sampler check](sampler-check.json) passes five focused cases: constant expansion, a nonconstant 2D gradient and edges, exact equal-size/downsampled-center values, a one-row source, and invalid dimensions. It compiles the production class without Unity rather than duplicating the algorithm in a mock. Both cached Unity assemblies also compile. **No new texture import, build or renderer has run.** Current Windows build remains d431.

The [source-only bridge audit](bridge-review.json) pins the reviewed files. Prepared MASK fields and explicit shared-map paths match both adapters; the bake/export preserve original coverage alpha. Both normal conventions agree. All rig controls are exported and all seven actions are completed before FBX baking. Unity needs those seven embedded takes; Unreal needs the matching standalone files and a fresh Skeleton for the inserted forearm twist hierarchy.

Nib's legacy Grip torso/arm still needs the artist's prepared semantic replacement migration. The new continuous organic body contains no shin; no lower-leg overlap defect was established from that object. The new UE facial-atlas material also needs its explicit Profile alternative generated at the next isolated import. New bake/export, fresh rig imports, actual alpha/backface/normal review, deformation and artistic acceptance remain pending.
