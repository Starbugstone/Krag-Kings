# Actual Unity native strand render: control failed

Unity6000.4.4f1/HDRP17.4 on the RTX2060/D3D12 rendered real native High Quality Lines with the local shader-keyword repair. PID30984 closed with native/guard0. This is a partial result, not a passing matched comparison or character/performance test.

Visual inspection found only two regions in `actual/strands.png`, while `actual/without-strands.png` still shows all three regions. The second filename reflects the intended capture, not its actual content. The hide/settling control failed. The probe incorrectly continued calling `DispatchUpdate` on inactive GameObjects because it checked only `component.enabled`; native renderer settings can re-register the renderer through OnValidate. This code defect is being corrected; the entire visible/control result must be rerun.

The twelve authored strands/108 points retain positions and diameters exactly in the HairAssets. GPU rendering currently uses the official linear taper fit and regional constant colors; authored per-point widths/colors are not framebuffer-verified.

The exact native log also records a render-target cleanup warning and188 persistent allocations on exit. These prevent a clean validation claim despite the zero process code. The first shader-compilation failure is preserved separately.

`files.json` hashes the actual staged source, graphs, frames, job and raw logs/telemetry. No production Unity project or build was changed.
