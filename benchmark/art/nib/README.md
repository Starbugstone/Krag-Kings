# Nib benchmark asset work

**Current handoff: pretriangulated optimized v4b, structurally validated and artistically unaccepted.** Root promoted the measured runtime derivative into the three shared variants and seven standalone clips after checking all 85 file hashes. The dense `Nib_Master.blend` remains preserved. Neither version meets the requested concept likeness or finished hero-quality bar.

The dense v4b pipeline was checkpointed in `c523810`. `create_nib.py` incorporates the scarf fitting, neutral-lid cleanup and lossless saves; `patch_nib_v4.py` records the equivalent changes applied to the saved v4 source. `source-report.json` retains original generation hashes, patch hash and reproduction-code hashes. The measured reduction, pose checks, matched captures and export receipt are in `v5-study/`; the authoring tools are in `tools/nib/v5_wip`. Separate native v5 and v5b art builds both exist and failed visual review. Corrective v5c scripts are explicitly ungenerated and do not change the preserved masters or shared files. Export/review/validation tools support explicit alternative paths while retaining their baseline defaults.

## Current artifacts and measured structure

- Editable, losslessly compressed source: `Nib_Master.blend` (about 85 MB), SHA-256 `c4fc3bce0413ab65a9a96e1d70451abbc8179c63a79b2a859c2ab1e11c1185eb`.
- Promoted runtime source: `Nib_Runtime_Optimized_v4b.blend`, SHA-256 `6a8a65e66a4f37f799ec97cb0ecb2259073be6391fdded340667892dcb147f1f`.
- Shared outputs: `../../shared/characters/nib/manifest.json`, identical current `asset_manifest.json`, `facial-rig.json`, three FBXs, seven per-clip FBXs and 72 PBR PNG maps.
- Every variant: one consolidated skinned mesh, 75 bones, 25 nonzero morph targets, 18 material slots, maximum four normalized bone influences per vertex.
- Promoted runtime counts: Natural 538,642 triangles / 304,261 vertices; Grip replacement 532,244 / 301,078; Leg replacement 533,534 / 301,669. Dense v4b had 1,158,384 / 1,103,608 / 1,147,908 triangles respectively. Actual engine costs still need measurement.
- Height is about 1.394 m to ear/fur tip. Bind ankle height is 0.10 m; source sole minimum is approximately 0.0005 m.
- Batched runtime fur: all 10,784 original strands retained, now 112,536 triangles per variant instead of 258,816. Additional fine edge, eyebrow and chin tubes are included in the complete character counts. Representation is skinned opaque geometry, without simulation or a cutout-material dependency. Engine frame-time/VRAM measurement is still required before further tuning.

The source is original procedural construction from concept sheets 02 and 05. No outside anatomical library has been incorporated into v4b. The isolated failed native v5/v5b studies use the official Blender Studio CC0 animation-head topology; v5b also uses the explicitly CC0 coherent hand topology. They have not been promoted; the corrective v5c pass remains ungenerated.

## Pretriangulated engine handoff

Root verified the 85-file receipt and promoted the triangle-only runtime FBXs. `v5-study/runtime-triangulated-candidate-v4b.contract.json` records the exact handoff; adjacent raw payload, preservation and fresh Blender roundtrip reports provide the checks. All Basis coordinates and 25 sparse morph payloads are byte-identical to the previous validated derivative. Vertex/material/UV corner sets are unchanged, and mapped normal difference is exactly zero. The serializer preserves the existing point-normal layer with Blender's own FBX parser/writer and verifies every other serialized property. This avoids Unreal's high-memory FBX SDK triangulation step; actual Unreal import still needs verification.

All three assembled variants and seven single-take clips pass fresh roundtrip with 75 bones, 25 morphs, normalized weights and zero bind-matrix difference. Blender removes one duplicate triangle from each imported variant (Natural indices 6192, 9363, 24611); raw FBX triangle counts above remain exact. This cleanup is recorded, not silently counted as identical topology. Guard peaks were 2,246 MB export, 381 MB payload preservation, 301 MB raw comparison and 768 MB roundtrip.

## Verification evidence

`v5-study/runtime-export-validation-v4b.json` records the promoted derivative's fresh-process FBX roundtrip of all three variants and all seven standalone clips. It passed with one mesh per variant, all required bones/morphs, no invalid skin weights, and exactly zero bind-matrix difference between every standalone clip and the assembled Natural skeleton. Each standalone clip contains one take and actual varying FaceRoot controls. `export-validation.json` remains the earlier dense-source result.

`v5-study/runtime-posed-validation-v4b.json` compares all 64 changed components at 23 actual authored poses, using up to 4,000 rest-surface correspondences each. Maximum sampled difference was 2.287 mm on head strands. The shared barycentric helper uses float64 intermediates because float32 arithmetic falsely failed very thin triangles. This is a source/derivative comparison, not artistic acceptance.

`animation-targets.json` records 112 hand/foot targets, with maximum solved bone-position error about 1.84e-7 m, and zero full-aim barrel-direction error. These are skeletal checks, not proof of good animation, sole contact on terrain, or lack of sliding in an engine. `facial-performance.json` records authored per-frame facial controls in every clip.

Guarded v4 generation peaked at 2,080 MB private memory; export peaked at 2,604 MB. All generation, review, patch, export and validation jobs exited 0 under the serialized heavy-task guard. No AAA, engine-performance or investor acceptance is inferred from these checks.

The successful derivative stages peaked at 1,287 MB (reduction), 2,597 MB (five renders), 669 MB (all-component pose check), 1,507 MB (export) and 770 MB (roundtrip). Rejected reduction trials are preserved only in the ignored local version archive. The undershirt and both trousers retain source density after their surface-error checks failed; tolerances were not relaxed.

## Visual review progression

| Pass | Evidence | Result |
| --- | --- | --- |
| v1 | `versions/v1-renders/`; old exports in `versions/pre-v4-shared/` | Failed: baby/teddy head, bulging eyes, tubular brows, flat leaf ears, rigid hair, disconnected arm joints and primitive clothing. |
| v2 | `versions/v2-source/`, `versions/v2-renders/` | Failed: long thin muzzle, floating eyes/brows, rigid scarf, sparse hair, marbled cloth, skyward Shoot pose. |
| v3 | `versions/v3-source/`, `versions/v3-renders/` | Failed: connected facial surface introduced, but cavity/teeth protruded at neutral; eyes, shoulders, scarf and hair remained wrong. Shoot now aimed forward. |
| v4 before patch | `versions/v4-prepatch/` | Neutral mouth sealed and torso/arms united; dark polygon lid margins looked jagged and the lowered scarf intersected the chest. |
| v4b current | `renders/Nib_FaceReview.png`, `renders/Nib_ReviewFront.png` and adjacent source-hash JSON | Major lid-material/scarf penetration corrected. **Still fails likeness:** face reads flat, orange iris pieces protrude from dark eye slits, nose/nostril/cheek/muzzle/lip construction lacks the reference continuity; head/ear groom is sparse; scarf reads as a broad sheet instead of compressed fabric loops; bib and hands remain insufficiently shaped. |
| native v5 failed | `v5-study/native-renders/` plus source-hash JSON | Continuous cheeks/lips improve construction, but source-eye parent transforms are wrong, the bust/neck base protrudes, nose mask is jagged, and groom/ears/cloth still fail. Source retained for review. |
| native v5b failed | `v5-study/native-v5b-renders/` Face/Front plus source-hash JSON | Evaluated eye source transforms are now correct, but the opaque source corneal shell hides the irises. Teeth/gums protrude beneath the closed mouth after an erroneous second head drop. Ear/goggle guide fields use stale heights; groom remains stiff and crosses lenses; scarf wraps have gaps, nose identity is lost. Hands and trousers improve, but the character still fails likeness and quality. No further dependent pose or export jobs were run. |
| optimized v4b | `v5-study/runtime-renders/` Front/Face/Shoot/Run/Blink and source-hash JSON | Reduction preserves the baseline appearance. Blink explicitly fails eye occlusion; the same face/groom/cloth weaknesses remain. This is the current technical engine baseline, not a visual approval. |

Current Shoot/Tongue images outside the version archive were captured before the v4b material/scarf patch; their JSON identifies that older source hash. Front/Face are the current v4b captures. No pass has received artistic approval.

The failed v5b source is `Nib_Master_v5b_WIP.blend`, SHA-256 `fbe314c1506157ee27e1fdd90f2db92ea0d62156da11d7970724caa58e9e43bf`. Its generation and first Face/Front review exited 0 with peaks of 672 MB and 2,643 MB; these successes concern process completion only. Source eye centers were independently checked against the CC0 library at approximately ±0.0358764, −0.1153812, 0.3100375 m before fitting. The existing mouth parts and facial pivots already included −0.032 m head lowering; v5b incorrectly repeated that offset. `source-face-fit-coordinate-audit.json` is a lightweight control-cage diagnostic, not evaluated saved-mesh evidence. A guarded saved-source coordinate/neutral-occlusion audit is prepared but pending.

Ungenerated v5c work corrects those inherited spaces, projects the source iris onto the anterior opaque globe before the common creature fit, adds evaluated mouth/bone/pose measurements before rendering, and measures actual lens bounds for grooming clearance. Main hair radii are proposed at 35–80 μm with curved paths and root-to-tip color variation. These are pending geometry/render checks, not an improvement claim. The shared v4b baseline also has 128 exact zero-area triangles in actual FBX Nib_Leather/Nib_Workwear material slots (64 each) and 1,876 collapsed UV triangles, reported by the independent Unreal raw audit; cleanup/localization is pending on isolated future exports, with shared inputs pinned.

Direct reinspection of the original sheet and actual failed v5b Face capture also identified a color-region mismatch: the concept has dusty pink inner ear skin, a tawny outer/rim coat and paler head/inner wisps; v5b has a dark brown membrane and nearly uniform ivory strands. `nib_groom_materials.py` prepares separate opaque UV-based regions, restrained clump/root-tip variation and a short outer-ear nap. Its numeric sRGB palettes are proposals requiring the next native render, not sampled/approved albedo values. The generator will report strand and triangle counts per group and embed hashes plus copies of the active authoring scripts in the new source. None of these new materials has been baked or imported into either engine. The guarded coordinate audit precedes generation; visible eye/lip/interior failures still stop dependent pose/export work.

The first actual Unity captures are `../../local/evidence/unity-verify/20261006-010937/Nib_Natural.png` and `Nib_Natural-face.png`. Their geometry generally reproduces this source's silhouette and visible defects. Skin renders incorrectly red in that initial engine pass; root is investigating the HDRP material/profile setup. Do not recolor source art to match that fault or count these images as visual acceptance. The portrait also exposes the sparse rectangular chin tuft and a light mouth-interior strip during idle; the next continuous-lip/groom pass must check animated poses as well as neutral.

## Animation, face and weapon contract

Source coordinates are meters, Z up, facing -Y. FBX forward is -Z, up Y. Shared limb names are paired `UpperArm`, `LowerArm`, `Hand`, `Thigh`, `Shin`, `Foot`, `Toe`, and `Ear` with `_L`/`_R` suffixes. All finger controls and non-weighted facial/socket bones export.

Clips are `Idle`, `Walk`, `Run`, `Melee`, `Shoot`, `Hit`, `FacePerformance`, authored at 30 fps. Each body clip includes appropriate facial acting. The independent FacePerformance combines cautious glances/flinching with a playful tongue gesture; it is not a random runtime emote. Nibs remain playful, technically capable adults who are physically weak and a little cowardly.

Walk uses frames 1–25, 0.8 s, 0.9 m/s, stance fraction 0.62. Run uses frames 1–19, 0.6 s, 2.7 m/s, stance fraction 0.32. Left contact phase is 0 and right is 0.5. These are animation tuning values, not lore.

`FaceRoot` is a separate subtree under `Head`. Jaw/eyes deform skeletally; other facial controls and body joint deltas drive named morphs through `manifest.deformation`, with per-variant nonzero-target overrides. Runtime channels measure local transform delta from bind in meters or degrees; they do not assume imported Euler axes or rely on Blender drivers surviving FBX. The dark-blue tongue is canonical. Interior teeth/gums, mouth proportions and expression design remain provisional for review.

`WeaponMuzzle` is the actual barrel endpoint. `WeaponAim` sits four centimeters farther along the barrel, providing an axis-independent forward vector. `manifest.weapon.fireTimesNormalized` is `[0.46]`, matching an explicit recoil/trigger key. A tiny Root-skinned bind-carrier triangle is included in each standalone animation FBX to preserve Skin/BindPose data; animation import ignores its geometry.

## Variants and materials

- `Nib_Natural`: organic arms and legs.
- `Nib_GripReplacement`: a lightweight left forearm/hand replacement restoring ordinary function.
- `Nib_LegReplacement`: a lightweight right lower leg/foot replacement restoring ordinary function.

These variants grant no crusher claw, enlarged limb, heavy upgrade or stat advantage. Clothing, tools and fixed proportions follow the same candidate design.

Maps are explicit BaseColor, OpenGL normal, roughness and metallic PNGs, shared by all variants. Most are 1024²; skin is 2048² and the generated workwear albedo is 1254². The canvas source/prompt are retained in `Nib_Workwear_BaseColor_v1.png` and `canvas-texture-prompt.txt`; its darker material tint is baked into the shared albedo. It is not a scanned PBR set or a verified seamless texture.

Confirmed fur coverage follows the concept: visible mottled skin with fine facial/body fuzz, fuller head and ear fur, and visible inner ear skin. A cinematic master has **not yet been generated**. Do not run the old generator's `--cinematic` path against the pinned assets: it also rewrites shared maps and evidence. The isolated v5 study now has a separate cinematic output path with an identical deterministic guide field; it remains unexecuted and unreviewed.

## Pipeline and remaining work

Run one Blender task at a time through `benchmark/tools/Run-HeavyTask.ps1`. Generation, review, export and roundtrip validation use separate processes, four CPU threads and an eight-GiB private-memory cap. The original combined process exhausted memory; its history is preserved locally. Do not bypass the guard or reintroduce unbounded parallel rendering.

Current outputs remain pinned for engine integration. Next art priorities are coherent orbital/eye/lid/lip topology, shaped hands, fuller concept-consistent head/ear tufts, compressed scarf loops and more convincing clothing construction. Native engine appearance, simultaneous per-unit actions, terrain contacts and performance need actual verification. A denser cinematic master and expression review are still outstanding. This is not a complete modular wardrobe, manufacturing-ready sculpt or approved merchandising master.
