# Unity native strand pilot

This is an isolated compatibility and rendering investigation requested after the visibly rectangular Nib fur review. It does not alter `benchmark/unity`, its package manifest, or current Windows build.

The installed HDRP17.4 documentation and runtime include `HighQualityLineRenderingVolumeComponent` and `HDAdditionalMeshRendererSettings`: a compute line rasterizer with analytic coverage and transparency sorting. The stock Hair material documentation also describes cards; selecting a Hair shader alone is not a native groom implementation.

The official [Demo Team Hair package](https://github.com/Unity-Technologies/com.unity.demoteam.hair) supplies strand assets, custom curve providers, GPU simulation, LOD and the HDRP line-renderer integration. [Digital Human](https://github.com/Unity-Technologies/com.unity.demoteam.digital-human) supplies skinned root attachment. Both packages use the Unity Companion License and their implementation stays within Unity. Blender-authored source curves are independent shared character data.

Pinned clean sources:

- Hair `75a7f446209896bc1bce0da2682cfdbdf30ce447` (`0.19.0-preview.1`).
- Digital Human `8d61864050277f2c4574df7b31beb70093a8c263` (`0.2.1-preview`).
- Unity6000.4.4f1 / HDRP17.4.0. The installed Collections package is6.4.0; package compatibility must be tested, not inferred from the older README minimum version.

`prepare.py` checks both upstream source pins and clean working trees, copies only the current project's small settings directories, and creates a separate local project under `benchmark/local/unity-strand-hair-pilot/project`. It refuses to overwrite an existing pilot. Native package paths reference the pinned local clones. `compatibility.job.json` runs the existing heavy-job guard and invokes the authored `CompatibilityProbe.Run` method, which builds an actual128-strand/8-point asset. Success establishes compilation and asset construction only, not GPU rendering, deforming attachment, appearance or speed.

Next evidence: ingest actual native Blender curves; render them with HDRP High Quality Lines; compare root motion against the Nib skin/ears; measure close and tactical views with simulation constrained or disabled where valid. Preserve visible mottled skin and the approved regional coverage. No chosen renderer, performance advantage or artistic acceptance is implied by this preparation.

## Actual first result

The [isolated compatibility run](../../../evidence/unity/native-strands-compatibility-v1/README.md) now passes native/guard0, including the real128-strand/8-point asset build. Fresh-import GUID diagnostics were resolved by Unity's own API Updater before successful compilation. GPU rendering and character deformation remain pending.

`prepare_fixture.py` flattens the actual Blender fixture, retaining its curve counts and radii. `NativeCurveProvider.cs` supplies these authored curves to the official builder. `prepare_shader.py` preserves the official `HairVertex` GPU position/width/velocity graph and selects HDRP Physical Hair with strand geometry, native High Quality Lines and an exposed regional color. The stock debug-rainbow connection is removed. Both shader inputs are pinned by recorded SHA-256.

`stage_render.py` copies these prepared files into the separate project. `render.job.json` invokes `RenderProbe.Run` with actual D3D12 graphics, producing matched strand-visible/hidden1280×720 frames. The prototype has12 strands/108 points, no simulation and no character binding; even a successful fixture does not constitute a full Nib groom or performance result. Its provider currently lives in an editor assembly and must move to a runtime assembly for a player build. These follow-up files compile in a lightweight check against the exact first probe references; actual graphics execution remains pending.
