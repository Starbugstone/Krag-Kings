# Coherent79 Nib — actual Unreal import

All three new Nib variants, the seven-variant scene assembly and five-material Profile preparation completed with native and guard exit 0 on 6 October 2026. Each stage produced its fresh semantic completion marker. The updated content has **not yet been packaged or rendered** in this evidence set; artistic acceptance remains false.

The source is the technically promoted `e1cdbd03…` fitted-neck candidate and its exact `fee71393…` PBR derivative. The old generated Nib mesh, skeleton, animation packages and receipts were archived before import. Their previous 75-bone contract was not reused for the new hierarchy. All four unchanged Krag variants reused hash-verified packages.

Each Nib import retains the 79 authored bones plus Unreal's `Nib_Rig` wrapper, 25 morphs, 27 material slots and all seven clips. Idle is 6 seconds, Walk 0.8 seconds and Run 0.6 seconds. EarTip/ForearmTwist bones, ear animation and portable contact/speed metadata survive. The wrapper's local scale is 100; imported limb scales and local translation lengths remain consistent with their bind values. These structural checks do not establish the appearance of the resulting motion.

The Profile mapping now includes the actual facial atlas and `Nib_v5_DustyPinkEar`, alongside the retained Krag/Nib skin materials. Masked groom materials retain their separate alpha contracts. No source texture was tinted and no shared payload changed during import.

| Stage | PID | Peak private MB | Minimum system available MB | Result |
| --- | ---: | ---: | ---: | --- |
| Natural | 30264 | 8404 | 3399 | Passed |
| Grip replacement | 28316 | 8043 | 3866 | Passed |
| Leg replacement | 31792 | 8145 | 3815 | Passed |
| Scene assembly | 27960 | 3648 | 8174 | Passed |
| Profile preparation | 4000 | 3803 | 8216 | Passed |

The existing limits were unchanged. The logs retain unused physics-root warnings and zero-length tangent-normal messages; independent source payload checks preserve the authored split normals exactly. These warnings still need actual rendered inspection. This is not a performance measurement or a clean-machine test.

`result.json` records the outcome and limitations. The exact executed recipes, source snapshot, per-variant dependency receipts, migration inventory, editor logs and memory samples are preserved here. The previous `fe65cc4a…` Windows executable remains unchanged; its prior native-input pass does not validate this new content.
