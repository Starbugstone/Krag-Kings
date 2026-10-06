# Prepared v5 material transfer

Status: source code and guarded job recipe only. No bake, v5d source, v5d
render, FBX or engine import has been produced by these tools. Face shape review
comes first. The current corrected v4b shared files remain unchanged.

`prepare_runtime_pbr.py` reads an explicitly named saved source and its matching
SHA-256 report. It writes a separate compressed `Nib_Runtime_PBR.blend`, textures
and receipt under `benchmark/local/candidates`. It verifies that every source
point, shape key, polygon index and skin weight remains unchanged. Original
material sources and the untouched input `.blend` remain available for review.

The portable map contract remains BaseColor (sRGB), Normal (OpenGL tangent +Y),
Roughness and Metallic (linear), using opaque materials. No custom engine shader
or alpha dependency is introduced.

| Field | Prepared transfer | Reason |
| --- | --- | --- |
| Facial skin and brown nose mask | Bake the actual neutral face into `Nib_v5_FacialSkinAtlas`: 4096² color/normal, 1024² roughness, 128² metal | `NibNoseMask` is a point attribute. A generic material tile loses its geometry-specific placement. The tool verifies the mask exists and is connected to Base Color. |
| Head fur, pale inner wisps, tawny rim fur | Separate maps evaluated over the exact original strand UV domain, 1024² color / 512² normal and roughness / 128² metal | U carries clump variation, V carries root-to-tip color. Original strand coordinates stay unchanged. |
| Pink inner skin and tawny outer undercoat | Separate maps over their audited UV domain | Regional assignments and exposed skin color must remain distinct. |
| Smooth opaque eye globe and iris | Separate maps for `Nib_OcularGlobe` and `Nib_OcularIris` | Ocular materials remove inherited skin/leather normal maps and skin subsurface response. Their actual appearance remains unreviewed. |
| Unchanged legacy equipment/body materials | Copy the explicit existing maps by material name | Reuse retained sources without silently replacing new field-dependent shaders. A missing map stops preparation. |

The face receives a packed atlas UV layer. All original shader UV references,
including explicit Normal Map layer names, are redirected to a separate source
UV layer during baking. That temporary layer is then removed from the portable
derivative, leaving the atlas as UV0. The editable input still retains its
original UVs and attributes. Other region maps use a unit UV carrier only after
the connected graph has been checked: attributes, object/generated coordinates,
geometry-dependent inputs, bump gradients, non-tangent normal fields and node
groups are rejected rather than silently flattened. Source region UVs must lie
within the carrier's 0–1 domain. Any future iris pigment based on anatomical
attributes instead requires an actual-eye atlas and cannot use this carrier.

Run order, after the serialized heavy slot is allocated:

1. Inspect the preserved v5c profile/three-quarter and complete the bounded v5d
   muzzle, nose-pad and eyelid correction. Review actual neutral/action/blink and
   tongue geometry before spending time on material detail.
2. Localize the inherited source surface defects and repair a separately saved
   source if required. Recipe fixes in `create_nib.py` do not modify saved meshes.
   The bake tool deliberately does not mutate topology to hide these defects.
3. Review the exact source and report paths in `v5d-pbr-prepared.job.json`.
   Those v5d inputs do not exist yet. Run one CPU/four-thread guarded bake only;
   its eight-GiB private-memory cap remains enforced.
4. Read the actual field/hash receipts. Render source and baked derivative with
   identical source lighting/cameras. Compare nose location/contrast, eyelid and
   lip seams, fur color along strands, pink/tawny/pale separation, and smooth eye
   reflections. A successful file write alone is not a material-parity pass.
5. Export the same saved derivative first to its own untriangulated reference,
   then to a separate pretriangulated candidate using that reference. Pass
   `--texture-dir` explicitly. Never transport v4b normal/morph payloads to changed
   v5 topology. Run mapped UV/normal/morph, fresh bind/clip and posed checks.
6. Root reviews/promotes only the validated candidate. Both engines then need
   actual material/pose captures and memory/frame-time measurements.

Known limits: atlas UV packing/overlap, sampled color parity, bake operator
behavior on this exact source and engine appearance have not been executed or
verified. The prepared resolutions are tuning values, not approved asset
budgets. The proposed regional color treatment does not fix the current face
shape, flat ear construction or insufficient groom volume.

After face projection passes, the next groom proof must compare actual close-up
geometry against sheet 02: flowing crown layers around clear goggle lenses,
fuller tapered ear-rim clumps and fine inner wisps over visible pink membrane.
Keep visible mottled skin and fine body fuzz. Increasing strand width or count
alone is not an acceptance measure; do not replace fur with a solid rolled rim.
Use the same close-up/front/profile cameras for runtime and denser cinematic
representations, then measure runtime cost separately from cinematic density.
