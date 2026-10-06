# Krag Kings — engine comparison demo

Work in progress. This directory contains the shared asset pipeline and separate Windows Unity HDRP and Unreal projects. Neither demo is accepted as complete until the actual packaged application and imported character likeness have been checked.

## Shared contract

- Editable Blender sources live in `art/`; reproducible asset scripts in `tools/`.
- Engine-neutral FBX models and PBR textures live in `shared/`.
- Character source units are meters, Z-up, facing -Y. FBX export is -Z forward, Y-up. Engines must verify the imported orientation and scale rather than blindly applying scale fixes.
- Character animation clips: `Idle`, `Walk`, `Run`, `Melee`, `Shoot`, `Hit`, `FacePerformance`; in place with stable root. Facial performance uses a dedicated `FaceRoot` subtree; exported morph targets and portable corrective-driver data supplement the skeleton.
- Krag variants include natural anatomy and an exaggerated crusher claw. Nib variants provide light functional replacements only, with one replacement per demo variant.
- Both demos use the same dune geometry and character exports; engine lighting and materials may be optimized independently and documented.
- These are hero characters for a limited-unit, turn-based game. Preserve silhouette, facial likeness, clothing construction and deformation detail; measure real rendering costs before reducing visible quality. High mesh counts alone do not satisfy the concept likeness requirement.

## Controls

| Input | Action |
| --- | --- |
| Left mouse | Select unit |
| Right mouse | Run selected unit to the terrain position |
| Shift + right mouse | Walk selected unit to the terrain position |
| A / F / H | Melee / shoot / hit animation |
| E / C | Facial performance / selected-character portrait view |
| V | Cycle selected species' bionic variant |
| Tab | Select next unit |
| Arrow keys | Pan camera |
| Middle mouse drag | Orbit camera |
| Mouse wheel | Zoom |
| Home | Reset camera |
| Escape | Quit packaged demo |

Keyboard actions are animation demonstrations, not the final tactical combat rules. An action cancels the prior movement command; a fresh right-click during an action queues its next destination. Unit footprints block overlap, but this open-dune study does not yet provide navigation around obstacles. This benchmark does not implement the depot mission or broader campaign. Quality, performance and behavior must be reported from actual runs, not inferred from settings or concept images.

## Environment

Terrain uses the same analytic dune surface in both engines. Blender-space horizontal coordinates are `(x,y)` in meters, over `[-40,40]`:

```text
z = 0.8 + 1.1*sin(0.105*x + 0.035*y)
        + 0.65*sin(0.055*x - 0.145*y)
        + 0.30*cos(0.22*x + 0.13*y)
```

The runtime collision mesh is authoritative for grounding and destination placement. Terrain movement must be checked uphill, downhill and across dune crests, including the run animation's feet.

The generated backdrop extends to 760 meters in each direction, keeping the central comparison surface unchanged. Distant rolling dunes are intended to prevent the terrain edge appearing in the camera; actual engine framing still needs review. Regenerate with `tools/environment/Run-Environment.ps1` through the shared memory guard.

## Runtime verification

Unity's `-benchmarkVerify` exercises selection, variants, seven required clips, facial/body corrective activation, walk/run traversal and foot contacts. Captures remain visual review evidence; a functional pass does not establish concept likeness. `-inputProbe` enables a separate native Windows mouse/keyboard check through `tools/unity/Verify-WindowsInput.ps1`.

Unity's separate `-benchmarkPerformance` mode uses the natural pair and default camera, warms for 15 seconds, then samples 30 seconds of idle animation at native resolution. `-benchmarkPerformanceMoving` (launcher mode `PerformanceMoving`) uses the same timing and camera with a repeating 12-second dune run/melee/shoot/hit sequence. Both disable input-probe writes and take their evidence capture after sampling. All modes accept `-evidencePath <folder>`. The launcher's `-Quality Full|Balanced` option selects a controlled A/B candidate: Balanced uses half-resolution SSGI and disables SSR while retaining native output, character meshes/textures, SSS, SSAO and contact shadows. The [actual same-build comparison](evidence/unity/20261006-lighting-comparison/README.md) measured 40.77 FPS Full moving, 57.95 FPS Balanced moving, and 58.15 FPS Balanced idle at native 1080p. Wide-view lighting differences are subtle, but final close-up/motion quality remains unaccepted. Do not compare timings from functional capture runs as if they were these fixed workloads. These short samples do not establish a sustained or locked 60 FPS result.

Runtime launchers save machine, driver, AC/battery and active Windows power-scheme conditions through `tools/Write-RunConditions.ps1`; the ASUS vendor performance mode remains unqueried. The shared memory guard can also track descendant processes for compiler/cooker wrapper jobs. Direct game runs use their own process, avoiding process-tree enumeration during timing.

`tools/unity/Run-Demo.ps1 -Mode Showcase` prepares a 72-second recording sequence using the same playable actors, assets and real-time clock. It waits for the capture tool to create `showcase-start.flag` in its evidence folder. The sequence covers dune movement, overlapping actions, bionic variants, natural-face portraits and camera movement. Game-only audio is recorded separately for muxing; desktop/microphone sound is not requested. The first valid [actual Unity recording and review frames](evidence/unity/20261006-wgc-review/README.md) now exist. Capture integrity passes; visual review fails due to current character defects and framing. It is not the final investor video. Unreal recording and the final accepted evidence for both engines remain pending.

The user prioritizes concept fidelity and smooth framerate together. Tune each engine from measurements on the reference PC, document rendering/resolution tradeoffs, and preserve the agreed proportions, faces, materials, bionics, fur coverage and personalities. Maximum settings alone do not establish the best result.

## Status

Unity 6000.4.4f1, Blender 5.2 and Unreal 5.8.3 are installed. Unity's first Windows build succeeded, and its actual 1920 × 1080 Direct3D 12 runtime passed automated checks across seven variants: independent overlapping actions, ray selection, animation/facial/body corrective activation and dune traversal. [First-run evidence](evidence/unity/20261006-first-runtime/result.json) records the build identity, import counts, guard telemetry and failed visual checks. This is functional integration evidence, not visual acceptance or a framerate benchmark.

The first Unity captures showed incorrectly red skin because generated diffusion profiles had zero shader hashes. A corrected build now renders the authored tan skin in [actual review captures](evidence/unity/20261006-material-fix-baseline/Unity-Natural-Pair.png). Its dense natural-pair idle baseline at native 1080p averaged 23.84 ms (about 41.94 FPS), p95 27.13 ms and p99 29.32 ms over 30 seconds after 15 seconds of warmup on the RTX 2060. [The recorded workload and settings](evidence/unity/20261006-material-fix-baseline/result.json) matter: this used the unoptimized characters, full-resolution SSGI/SSR and a warm sun, and does not establish final movement performance or an engine ranking. The newer [controlled lighting comparison](evidence/unity/20261006-lighting-comparison/README.md) uses neutral lighting and the reduced pretriangulated derivatives; it is a different workload/build from that initial dense baseline. Krag face/hand/scarf/armor construction and Nib face/clothing/groom likeness also remain visibly below the concepts. The current character renders remain unaccepted review candidates; this is not a finished investor demonstration.

Unity's [actual native input verification](evidence/unity/20261006-native-input/result.json) passes on the host's French keyboard layout: left-click selection, right-click run, Shift + right-click walk, printed action letters, independent overlapping actions, and pan/orbit/zoom while an action plays. The valid video review subsequently caught a Nib forehead deformation defect despite the earlier numerical morph-activation pass. The [shared Nib repair](evidence/shared/20261006-nib-morph-repair-promotion.json) now passes raw-FBX deformation bounds, roundtrip checks and an actual imported Shoot-pose render: body correctives cause zero movement in the head. It preserves geometry, UV/material corners, normals and intended facial targets within the recorded tolerance. The [new actual Unity review](evidence/unity/20261006-morph-aim-review/README.md), build `bb1e2e674721495c87f0bc68dcc8d92d`, renders the repaired assets: the sampled Nib Shoot portrait has no tall forehead spikes, both ears fit the widened view, and the facial-performance HUD reports EXPRESSION. The previous Krag Shoot arm aimed about 53 degrees away from forward at the first discharge. A [validated curve-only correction](evidence/shared/20261006-krag-aim-repair-promotion.json) now preserves all geometry, facial targets and other takes while correcting that direction. The [actual seven-variant regression](evidence/unity/20261006-morph-aim-verification/README.md) now passes in the new executable: eight Krag discharge samples stay within 3.96 degrees of unit forward, with no reported runtime failures. Open fingers around the weapon and severe raised-arm axillary stretching still fail pose review. The new showcase framing also awaits its complete recorded run. Earlier timing/video results belong to the previous build and are not new-build measurements. The initial-state probe also shows Unity grounds on `h(-x,-z)` while the common scene requires `h(x,z)`. The [corrected current executable](evidence/unity/20261006-terrain-coordinate-correction/README.md), build `b5fa6342a69f462d8e2f6510ee0056e6`, now uses a terrain-only 180-degree rotation and passes all four imported height/normal checks plus 17 functional checks across seven variants. The first X-only attempt was rejected by its strict normal check. This build also renders the reviewed sand-v2 maps with finer grain and quieter ridges. Shared geometry and character transforms remain unchanged; no new performance result is claimed.

Unreal's native editor-module compilation and all seven isolated character imports have passed mesh, morph, skeleton and seven-clip semantic checks. The Nib imports include the corrected shared body morphs. Fresh processes kept each import within the unchanged memory cap after the original combined import exceeded it. The first actual editor-game renders caught defects that import checks could not establish: ground queries were not ready on the initial tick, a Python rotation constructor assigned the intended mesh yaw to pitch, and materials lacked morph-target usage. The latest actual frame shows upright, grounded actors with the repaired materials. The excessive orange cast and compounded sun rotation are now repaired in an actual editor-game frame. Skin brightness and matching terrain/camera orientation still require comparison. The first Windows Development package passes build, cook, stage/archive and artifact checks; its entry executable is `builds/unreal/Windows/KragKingsBenchmark.exe`. This does not establish standalone input correctness, visual acceptance or performance. The standalone renders successfully. Its first OS click test was intercepted by a separate Windows system window, so no gameplay selection handler ran; owned-window input delivery is being corrected before judging that control. Actual native input/action checks, controlled timings and final screenshots/video remain unfinished.

The first full Unity character import on 6 October imported Nib Natural, then the task guard stopped Krag Piston at 9,595 MiB editor private memory, with 2,978 MiB system memory available and 77% commit. The first Unreal import with the renderer active also reached its private-memory cap while importing Krag Natural. These are importer costs, not game framerate or runtime VRAM measurements. Follow-up work applies import settings before the first load, processes models separately, and prepares lower-cost runtime derivatives while preserving the detailed masters. Unity's immediate import candidate keeps every position morph but omits per-shape normal/tangent buffers; facial lighting must be reviewed before retaining that tradeoff.

The host rebooted during initial work. See [the crash investigation](CRASH-INVESTIGATION.md) for observed Windows stop-code and Blender memory-error evidence. Heavy generation/import/build/render steps now run serially through `tools/Run-HeavyTask.ps1`, with memory telemetry in ignored local files.

## Reproducible assets

Large Blender/FBX/texture assets use Git LFS. After cloning, install Git LFS and run `git lfs pull` before rebuilding assets or opening the projects. Engine caches, installers, build outputs and local diagnostics are excluded from version control.

Sand contact candidates derive from Fantozzi's CC0 recordings, with preserved originals, checksums and processing recipes under `art/audio/` and `shared/audio/manifest.json`. `tools/environment/build_contacts.py` also creates the shared analytic dust mask. Sound balance and visual contact effects require an actual engine review. These are not voice recordings or an approved final mix.

Candidate shot and hit sounds use the CC0 Free Firearm Sound Library and Kenney Impact Sounds. The four selected originals and provenance are preserved under `art/audio/combat/`; `tools/environment/build_action_audio.py` records cropping, pitch/filtering and non-clipping output checks in `shared/audio/action-audio.json`. Actual synchronization and game mix remain review items.

The Unity lit soft-particle shader comes from its pinned HDRP package and stays inside the Unity project, with its source/license record beside it. It is not a shared Unreal asset.
