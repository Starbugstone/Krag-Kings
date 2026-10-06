# Actual Unity full native-strand character render

Unity 6000.4.4f1 / HDRP 17.4 / RTX 2060 / D3D12 closes native/guard 0 (PID 33832). All five native High Quality Lines renderers are valid. Actual front, side and groom-hidden images render at 1400×1100. The visible/hidden front comparison differs at 126,804 pixels after 231 completed camera callbacks at the comparison boundary. All 26,000 curves / 234,000 points are supplied; no fur simulation runs.

The graph reads authored linear RGB and per-point diameter from float textures indexed by strand and longitudinal point, retaining native GPU vertex/tangent generation. This proves working GPU execution and visible contribution; no framebuffer metrology of individual subpixel diameters is claimed. Direct authored width has no automatic LOD compensation in this diagnostic. The captured character is in imported rest pose and still uses the frozen original native groom, not the newer Blender v2c study.

All three images were inspected. **Art remains rejected:** combed head veil, straight pale ear strands, retained basal bars, glossy/blotchy skin, weak facial anatomy and rigid jagged scarf. No antialiasing or native fur shadows is enabled here. Source-root animation, standalone frame time, final lighting and concept likeness remain unverified. Recorded GPU memory is system-wide editor telemetry, not an isolated runtime fur budget. The log retains one upstream CoreUtils.emptyBuffer shutdown-allocation report.

The prior [shader/light failure](../native-character-render-v1-shader-failed/README.md) is preserved. Only the reserved variable name, second-light shadows and diagnostic output paths changed for this bounded repair. Neither production Windows project/build is changed by this pilot.
