# Nib benchmark asset work

**Current handoff: v4b, structurally validated and artistically unaccepted.** `Nib_Master.blend`, the three shared variants, seven standalone clips and current Front/Face captures are pinned for the first Unity/Unreal imports. They do not meet the requested concept likeness or finished hero-quality bar.

`benchmark/tools/nib` is the current v4b pipeline, with no ungenerated v5 art changes. `create_nib.py` incorporates the scarf fitting, neutral-lid cleanup and lossless saves. `patch_nib_v4.py` records the equivalent small changes applied to the saved v4 source. `source-report.json` retains original generation hashes, patch hash and current reproduction-code hashes. New likeness work must use new work-in-progress files until root checkpoints these outputs.

## Current artifacts and measured structure

- Editable, losslessly compressed source: `Nib_Master.blend` (about 85 MB), SHA-256 `c4fc3bce0413ab65a9a96e1d70451abbc8179c63a79b2a859c2ab1e11c1185eb`.
- Shared outputs: `../../shared/characters/nib/manifest.json`, identical current `asset_manifest.json`, `facial-rig.json`, three FBXs, seven per-clip FBXs and 72 PBR PNG maps.
- Every variant: one consolidated skinned mesh, 75 bones, 25 nonzero morph targets, 18 material slots, maximum four normalized bone influences per vertex.
- Natural: 1,158,384 triangles / 614,132 vertices. Grip replacement: 1,103,608 / 586,760. Leg replacement: 1,147,908 / 608,856. These are current review costs, not accepted runtime budgets.
- Height is about 1.394 m to ear/fur tip. Bind ankle height is 0.10 m; source sole minimum is approximately 0.0005 m.
- Batched runtime fur: 10,784 strands / 258,816 triangles per variant. Additional fine edge, eyebrow and chin tubes are included in the complete character triangle counts above. Representation is skinned opaque geometry, without simulation or a cutout-material dependency. Engine frame-time/VRAM measurement is still required before tuning.

The source is original procedural construction from concept sheets 02 and 05. No outside anatomical library has been incorporated into v4b. The official Blender Studio CC0 reference library is being considered for the next topology pass, preserving the creature identity.

## Verification evidence

`export-validation.json` records a fresh-process FBX roundtrip of all three assembled variants and all seven standalone clips. It passed with one mesh per variant, all required bones/morphs, no invalid skin weights, and exactly zero bind-matrix difference between every standalone clip and the assembled Natural skeleton. Each standalone clip contains one take and actual varying FaceRoot controls.

`animation-targets.json` records 112 hand/foot targets, with maximum solved bone-position error about 1.84e-7 m, and zero full-aim barrel-direction error. These are skeletal checks, not proof of good animation, sole contact on terrain, or lack of sliding in an engine. `facial-performance.json` records authored per-frame facial controls in every clip.

Guarded v4 generation peaked at 2,080 MB private memory; export peaked at 2,604 MB. All generation, review, patch, export and validation jobs exited 0 under the serialized heavy-task guard. No AAA, engine-performance or investor acceptance is inferred from these checks.

## Visual review progression

| Pass | Evidence | Result |
| --- | --- | --- |
| v1 | `versions/v1-renders/`; old exports in `versions/pre-v4-shared/` | Failed: baby/teddy head, bulging eyes, tubular brows, flat leaf ears, rigid hair, disconnected arm joints and primitive clothing. |
| v2 | `versions/v2-source/`, `versions/v2-renders/` | Failed: long thin muzzle, floating eyes/brows, rigid scarf, sparse hair, marbled cloth, skyward Shoot pose. |
| v3 | `versions/v3-source/`, `versions/v3-renders/` | Failed: connected facial surface introduced, but cavity/teeth protruded at neutral; eyes, shoulders, scarf and hair remained wrong. Shoot now aimed forward. |
| v4 before patch | `versions/v4-prepatch/` | Neutral mouth sealed and torso/arms united; dark polygon lid margins looked jagged and the lowered scarf intersected the chest. |
| v4b current | `renders/Nib_FaceReview.png`, `renders/Nib_ReviewFront.png` and adjacent source-hash JSON | Major lid-material/scarf penetration corrected. **Still fails likeness:** face reads flat, orange iris pieces protrude from dark eye slits, nose/nostril/cheek/muzzle/lip construction lacks the reference continuity; head/ear groom is sparse; scarf reads as a broad sheet instead of compressed fabric loops; bib and hands remain insufficiently shaped. |

Current Shoot/Tongue images outside the version archive were captured before the v4b material/scarf patch; their JSON identifies that older source hash. Front/Face are the current v4b captures. No pass has received artistic approval.

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

Confirmed fur coverage follows the concept: visible mottled skin with fine facial/body fuzz, fuller head and ear fur, and visible inner ear skin. `--cinematic` is prepared to generate a separate denser `Nib_Cinematic.blend` with the same coverage. That cinematic file has **not yet been generated**.

## Pipeline and remaining work

Run one Blender task at a time through `benchmark/tools/Run-HeavyTask.ps1`. Generation, review, export and roundtrip validation use separate processes, four CPU threads and an eight-GiB private-memory cap. The original combined process exhausted memory; its history is preserved locally. Do not bypass the guard or reintroduce unbounded parallel rendering.

Current outputs remain pinned for engine integration. Next art priorities are coherent orbital/eye/lid/lip topology, shaped hands, fuller concept-consistent head/ear tufts, compressed scarf loops and more convincing clothing construction. Native engine appearance, simultaneous per-unit actions, terrain contacts and performance need actual verification. A denser cinematic master and expression review are still outstanding. This is not a complete modular wardrobe, manufacturing-ready sculpt or approved merchandising master.
