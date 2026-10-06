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

The [isolated compatibility run](../../../evidence/unity/native-strands-compatibility-v1/README.md) now passes native/guard0, including the real128-strand/8-point asset build. Fresh-import GUID diagnostics were resolved by Unity's own API Updater before successful compilation. Character deformation remains pending; the first actual GPU results are recorded below.

`prepare_fixture.py` flattens the actual Blender fixture, retaining its curve counts and radii. `NativeCurveProvider.cs` supplies these authored curves to the official builder. `prepare_shader.py` preserves the official `HairVertex` GPU position/width/velocity graph and selects HDRP Physical Hair with strand geometry, native High Quality Lines and an exposed regional color. The stock debug-rainbow connection is removed. Both shader inputs are pinned by recorded SHA-256.

`stage_render.py` copies these prepared files into the separate project. The render jobs invoke `RenderProbe.Run` with actual D3D12 graphics, intending matched strand-visible/hidden1280×720 frames. The prototype has12 strands/108 points, no simulation and no character binding; even a successful fixture does not constitute a full Nib groom or performance result. Its provider currently lives in an editor assembly and must move to a runtime assembly for a player build.

The first graphics attempt [failed before drawing](../../../evidence/unity/native-strands-render-v1-failed/README.md): the HairVertex subgraph and generated shader duplicate the built-in procedural-instancing keyword. `prepare_shader_repair.py` creates a local provider copy treating only that keyword as Predefined, retaining native shader math and the HDRP Physical Hair target. The upstream package/installed engine remain unchanged. Derived shader notices are retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The [actual second attempt](../../../evidence/unity/native-strands-render-v2-control-failed/README.md) renders native strands on the RTX2060/D3D12 and closes native/guard0. Its capture control fails: only two groups appear initially, and all three remain in the intended hidden view. The probe continued dispatching inactive objects, allowing buffers/line-renderer registration to be recreated. Its native log also contains a render-target cleanup warning and188 persistent allocations. These failures remain preserved despite the successful shader compilation/process exit.

The [actual v3 retry](../../../evidence/unity/native-strands-render-v3-missing-region/README.md) corrects inactive dispatch and owned cleanup, records completed camera frames/renderer state, and adds per-region image checks. It passes the empty-background control but fails native/guard1 because CreamHead still has zero visible pixels; the other two regions render. There are183 completed camera callbacks, so merely waiting longer does not solve it. The188 previous allocation reports reduce to two static upstream allocation stacks (LongOperation and CoreUtils.emptyBuffer), retained with full traces. First-renderer shader/compute initialization remains under diagnosis.

Additional source inspection found that the official GPU renderer currently fits a linear root-to-tip taper from curve diameters; its optional per-vertex width/UV rendering feature flags are commented out. Retaining exact per-point widths in the HairAsset therefore does **not** prove exact widths in the framebuffer. The fixture receipt records that approximation. Regional fixture colors also do not yet reproduce the character sidecar's per-point color variation. Actual rendered quality determines the follow-up work.
