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

Keyboard actions are animation demonstrations, not the final tactical combat rules. This benchmark does not implement the depot mission or broader campaign. Quality, performance and behavior must be reported from actual runs, not inferred from settings or concept images.

## Environment

Terrain uses the same analytic dune surface in both engines. Blender-space horizontal coordinates are `(x,y)` in meters, over `[-40,40]`:

```text
z = 0.8 + 1.1*sin(0.105*x + 0.035*y)
        + 0.65*sin(0.055*x - 0.145*y)
        + 0.30*cos(0.22*x + 0.13*y)
```

The runtime collision mesh is authoritative for grounding and destination placement. Terrain movement must be checked uphill, downhill and across dune crests, including the run animation's feet.

The source generator extends the backdrop to 760 meters in each direction, keeping the central comparison surface unchanged. Distant rolling dunes prevent the terrain edge appearing in the camera. Regenerate with `tools/environment/Run-Environment.ps1` through the shared memory guard.

## Runtime verification

Unity's `-benchmarkVerify` exercises selection, variants, seven required clips, facial/body corrective activation, walk/run traversal and foot contacts. Captures remain visual review evidence; a functional pass does not establish concept likeness. `-inputProbe` enables a separate native Windows mouse/keyboard check through `tools/unity/Verify-WindowsInput.ps1`.

Unity's separate `-benchmarkPerformance` mode uses the natural pair and default camera, warms for 15 seconds, then samples 30 seconds of idle animation at native resolution. It disables input-probe writes and takes its evidence capture after sampling. Both modes accept `-evidencePath <folder>`. Do not compare timings from functional capture runs as if they were this fixed workload.

`tools/unity/Run-Demo.ps1 -Mode Showcase` prepares a 72-second recording sequence using the same playable actors, assets and real-time clock. It waits for the capture tool to create `showcase-start.flag` in its evidence folder. The sequence covers dune movement, overlapping actions, bionic variants, natural-face portraits and camera movement. Game-only audio is recorded separately for muxing; desktop/microphone sound is not requested. Screenshots and an MP4 from each actual engine are required final deliverables and are not yet produced.

The user prioritizes concept fidelity and smooth framerate together. Tune each engine from measurements on the reference PC, document rendering/resolution tradeoffs, and preserve the agreed proportions, faces, materials, bionics, fur coverage and personalities. Maximum settings alone do not establish the best result.

## Status

Unity 6000.4.4f1, Blender 5.2 and Unreal 5.8.3 are installed. The initial Unity script/HDRP import and Unreal native editor-module compilation have passed. Subsequent source changes, character imports, runtime rendering and packaged demos still need validation. The current character renders remain unaccepted review candidates, with documented likeness/deformation defects; this is not a finished investor demonstration.

The host rebooted during initial work. See [the crash investigation](CRASH-INVESTIGATION.md) for observed Windows stop-code and Blender memory-error evidence. Heavy generation/import/build/render steps now run serially through `tools/Run-HeavyTask.ps1`, with memory telemetry in ignored local files.

## Reproducible assets

Large Blender/FBX/texture assets use Git LFS. After cloning, install Git LFS and run `git lfs pull` before rebuilding assets or opening the projects. Engine caches, installers, build outputs and local diagnostics are excluded from version control.

Sand contact candidates derive from Fantozzi's CC0 recordings, with preserved originals, checksums and processing recipes under `art/audio/` and `shared/audio/manifest.json`. `tools/environment/build_contacts.py` also creates the shared analytic dust mask. Sound balance and visual contact effects require an actual engine review. These are not voice recordings or an approved final mix.

The Unity lit soft-particle shader comes from its pinned HDRP package and stays inside the Unity project, with its source/license record beside it. It is not a shared Unreal asset.
