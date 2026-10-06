# Symmetric macroface diagnostic — numerical v6

Actual standalone numerical preflight only; no Blender application, saved native source or render. Input is regional `ed53df07…`, with exact Basis and all 17 saved facial targets. The selected field adds no neutral corner-height asymmetry. Illustrated smile asymmetry remains an expression decision; v5 is rejected as neutral authoring.

All 18 arrays introduce zero degenerate triangles or greater-than-90-degree flips relative to the same original shape. Minimum sampled Jacobian determinant is 0.456307 and minimum singular value 0.323775 across 6,139 samples. Fitted globe/iris transformations match their declared similarities within 2.23e−16 m.

The strict preflight intentionally returns failure because combined Smile/JawOpen differs from the transformed combined pose by 0.493993 mm, over its 0.25 mm gate. This warning is retained for actual posed review; no geometric threshold was relaxed. The explicitly named diagnostic override permits only this warning, never a new fold/Jacobian failure. Nearest opposite eyelid vertex distances are sampling evidence, not zero-gap or collision claims.

The new source, camera-matched/neutral/profile review and Tongue/Blink contact checks remain pending. `projection-check.json` compares the same provisional reference cameras without refitting them to improve the candidate score. Shared assets are unchanged and artistic acceptance is false.
