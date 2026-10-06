# Semantic Krag jaw replacement studies

The actual v1 source is `benchmark/art/krag/Krag_IronJaw_Replacement_v1_WIP.blend` (SHA256 `20c48d2e23c112ebca5b855247eca3e3aea630b1c463e8f99d4c4594adb5f031`). `ironjaw-replacement-v1-review.json` records two real failed clearance views. Natural geometry/weights/bind/actions were preserved and replaced mandible/lower oral surfaces genuinely removed. The inherited lip-shaped casing, shield intersection and opening cheek gap still fail.

The read-only natural-mouth decomposition has now run successfully. `benchmark/art/krag/anatomy-study/natural-mouth-opening-v9o-review.json` preserves both the first JSON-serialization failure and the successful scalar-safe retry. At the unchanged 22.9908-degree jaw pose, skeleton alone opens the central rim by 75.64 mm and skeleton plus JawOpen by 80.63 mm. This is not a duplicated full jaw opening: the corrective instead moves the lower lip backward by 10.94 mm relative to the rigid dental arch. Existing dental crowns are 12.4–17.1 mm tall. Analytical skinning matches actual Blender within 0.364 micrometres.

The following are **prepared, syntax-checked, ungenerated**:

- `refine_replacement_v2.py`: rebuild the rigid lower shell as an authored formed U housing/pan; add `attachment_cuff.py`, whose outer row follows the exact retained skin boundary/morphs/weights and whose inner row belongs to Jaw. Actual fit and continuity remain unverified.
- `review_replacement_v2.py`: ClosedFront and unobscured OpenRight review of that future source.
- `build_normal_mouth_v9p.py`: retain neutral head/dental geometry, jaw hinge, full expression range and every source action; replace the lip-local JawOpen slide, add contained tongue-floor movement and rigidly reorient the existing tusks around their actual gingival roots. `natural_tusk_rotation.py` preserves crown size and root positions. The saved file is reopened to verify coordinates, bindings, curves and shared JawOpen control activation.
- `review_normal_mouth_v9p.py`: actual ClosedFront, OpenFront, OpenRight and ClosedRight views. Closed contact and full-range opening must pass visible inspection before rebasing the mechanical cuff/housing on this natural-mouth source.

All jobs use the shared heavy-task guard and require root's serialized handoff. No shared runtime export is changed by these isolated source studies.
