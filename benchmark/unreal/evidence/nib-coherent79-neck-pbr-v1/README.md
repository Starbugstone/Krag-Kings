# Coherent Nib material transfer — actual evidence

The fresh portable bake passes saved-file validation and the four sampled
source/baked view comparisons. This is a technical material-transfer result;
character art still fails acceptance, and this candidate has not been imported
into either engine.

- Input: coherent neck source `e1cdbd030b8b4de9abd073807e93c40e9d69348e5bcf97c519656f5e3599804b`.
- Saved PBR derivative: `fee71393f1a41355e309994118656494b320f1284f995259a5362fa82db0b4b1`.
- All 79 bind bones, seven animations, 379 source mesh payloads, weights and morphs are unchanged. Idle remains six seconds; locomotion retains the actual source speed/contact metadata.
- Nine field bakes and 27 materials produce 102 texture files. All reopen, decode and match their recorded hashes. The original fine-strands RGBA atlases are copied byte-identically after checking their actual source shader bindings.
- The actual left/right iris point fields are baked on their fitted surfaces. The close-up pair retains radial amber pigment, the dark outer edge and original slit geometry.

| View | Source | Saved PBR |
| --- | --- | --- |
| Face | [Source](views/source/Nib_FaceReview.png) | [Baked](views/baked/Nib_FaceReview.png) |
| Tongue | [Source](views/source/Nib_ExpressionTongue.png) | [Baked](views/baked/Nib_ExpressionTongue.png) |
| Full body | [Source](views/source/Nib_ReviewFront.png) | [Baked](views/baked/Nib_ReviewFront.png) |
| Iris close-up | [Source](views/source-optical/EyeCloseup.png) | [Baked](views/baked-optical/EyeCloseup.png) |

All eight images were inspected. Nose placement/contrast, regional ear colors,
groom coverage and dark blue tongue remain coherent, with no obvious new
material regression in these samples. The views do not prove every side/back
UV seam or engine shading. Existing facial likeness, visible card roots, neck
shading, cloth construction and hand/axilla defects remain open.

All seven guarded jobs exited normally with their fresh completion markers.
The bake peaked at 2,863 MB private memory; the largest rendered-view job peaked
at 2,931 MB. The lowest observed system availability across the chain was
8,262 MB. These are CPU Blender resource observations, not game performance.
[Result and exact artifact hashes](result.json) preserve the executed inputs,
structural snapshots, receipts, logs and memory samples.

The matching three full-variant FBXs and seven standalone clips are next.
Shared character files and both current Windows packages remain unchanged.
