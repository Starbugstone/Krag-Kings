# Prepared v5 material transfer

Status: the first source bake (`d3b682d4…`) passed structural checks but
failed reopened rendering because its texture paths were remapped from the old
source root. The preserved failure is now followed by an actual path-only
derivative (`2a3ab470…`): all98 original maps decode with matching hashes/color
spaces, and rig/action/mesh parity passes. Three matched Face/Tongue/Front views
retain the source materials without an obvious new regression. See the
[actual repair and parity evidence](../../../../unreal/evidence/nib-coherent79-pbr-path-repair/README.md).
No new FBX/engine import or art acceptance is implied; shared v4b stays unchanged.
Use the current [isolated integration plan](../../../unreal/nib_candidate/README.md),
not historical `v5d-pbr-prepared.job.json` paths.

`prepare_runtime_pbr.py` reads an explicitly named saved source and its matching
SHA-256 report. It writes a separate compressed `Nib_Runtime_PBR.blend`, textures
and receipt under `benchmark/local/candidates`. It verifies that every source
point, shape key, polygon index and skin weight remains unchanged. Original
material sources and the untouched input `.blend` remain available for review.

The portable map contract remains BaseColor (sRGB), Normal (OpenGL tangent +Y),
Roughness and Metallic (linear). Ordinary materials stay opaque. The current
groom also uses the explicit MASK contract: BaseColor RGBA coverage in alpha,
threshold 0.45, double-sided/Flip, and OpenGL +Y tangent normals. Original atlas
PNGs are copied byte-identically via `--card-texture-dir`; alpha is not rebaked
or converted to transparent blending. Shared normal/roughness/metal filenames
remain explicit manifest paths rather than guessed per-material filenames.

| Field | Prepared transfer | Reason |
| --- | --- | --- |
| Facial skin and brown nose mask | Bake the actual neutral face into `Nib_v5_FacialSkinAtlas`: 4096² color/normal, 1024² roughness, 128² metal | `NibNoseMask` is a point attribute. A generic material tile loses its geometry-specific placement. The tool verifies the mask exists and is connected to Base Color. |
| Head fur, pale inner wisps, tawny rim fur | Separate maps evaluated over the exact original strand UV domain, 1024² color / 512² normal and roughness / 128² metal | U carries clump variation, V carries root-to-tip color. Original strand coordinates stay unchanged. |
| Masked crown/inner-ear/tawny cards | Copy the actual original RGBA atlases and shared scalar/normal maps, with source hashes | Preserve fine coverage and regional color; both engine adapters require the declared MASK/Flip fields. |
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

1. Obtain the corrected actual coherent/restorative saved source and receipt.
   Preserve the first failed wrist/cuff source and its three views. Overall face,
   axilla, cloth, groom and right-hand grip failures remain separate art gates.
2. Freeze the source SHA, all seven canonical actions, full matching 79-bone bind
   and original card atlas directory in a new isolated plan. Recipe edits do
   not repair an already saved mesh; the bake does not hide topology defects.
3. Run the guarded source snapshot, CPU/four-thread bake and saved PBR snapshot.
   The eight-GiB private-memory cap remains enforced. Require unchanged rig,
   actions, geometry, weights and morphs; UV/material transfer is intentional.
4. Read the actual field/hash receipts. Render source and baked derivative with
   identical source lighting/cameras. Compare nose location/contrast, eyelid and
   lip seams, fur color along strands, pink/tawny/pale separation, and smooth eye
   reflections. A successful file write alone is not a material-parity pass.
5. Export the same saved derivative first to its own untriangulated reference,
   then to a separate pretriangulated candidate using that reference. Pass
   `--texture-dir` explicitly. Never transport v4b normal/morph payloads to changed
   v5 topology. Run mapped UV/normal/morph, fresh bind/clip and posed checks.
6. Validate all three full variants and seven standalone takes against the
   exact source bind and sampled motion. A separate technical promotion must be
   identified honestly; structural validity does not mean artistic approval.
   Both engines need actual material/pose captures and memory/frame-time checks.

Known limits: the three sampled front views establish limited material parity,
not all back/UV seams or engine shading. Full variant/clip export and actual
engine appearance remain unverified. The prepared resolutions are tuning values, not approved asset
budgets. The proposed regional color treatment does not fix the current face
shape, flat ear construction or insufficient groom volume.

After face projection passes, the next groom proof must compare actual close-up
geometry against sheet 02: flowing crown layers around clear goggle lenses,
fuller tapered ear-rim clumps and fine inner wisps over visible pink membrane.
Keep visible mottled skin and fine body fuzz. Increasing strand width or count
alone is not an acceptance measure; do not replace fur with a solid rolled rim.
Use the same close-up/front/profile cameras for runtime and denser cinematic
representations, then measure runtime cost separately from cinematic density.

The adult identity source requires the prepared `bake_ocular.py` extension. Its two actual fitted iris surfaces receive separate small atlases from connected `Nib_IrisCoord` point attributes; the helper verifies source-report hashes and attribute retention. The original slit geometry, shell curvature, bind and weights remain subject to the existing unchanged-source gates. The uniform `Nib_IdentityOcularGlobe` uses its constant PBR field. This extension is syntax-checked only: no new iris bake, saved parity render or engine import has run. New plans pin the helper; previous executed plans/receipts are preserved.
