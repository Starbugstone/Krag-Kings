# Semantic Krag jaw replacement studies

The actual v1 source is `benchmark/art/krag/Krag_IronJaw_Replacement_v1_WIP.blend` (SHA256 `20c48d2e23c112ebca5b855247eca3e3aea630b1c463e8f99d4c4594adb5f031`). `ironjaw-replacement-v1-review.json` records two real failed clearance views. Natural geometry/weights/bind/actions were preserved and replaced mandible/lower oral surfaces genuinely removed. The inherited lip-shaped casing, shield intersection and opening cheek gap still fail.

The read-only natural-mouth decomposition has now run successfully. `benchmark/art/krag/anatomy-study/natural-mouth-opening-v9o-review.json` preserves both the first JSON-serialization failure and the successful scalar-safe retry. At the unchanged 22.9908-degree jaw pose, skeleton alone opens the central rim by 75.64 mm and skeleton plus JawOpen by 80.63 mm. This is not a duplicated full jaw opening: the corrective instead moves the lower lip backward by 10.94 mm relative to the rigid dental arch. Existing dental crowns are 12.4–17.1 mm tall. Analytical skinning matches actual Blender within 0.364 micrometres.

The following are **prepared, syntax-checked, ungenerated**:

- `refine_replacement_v2.py`: rebuild the rigid lower shell as an authored formed U housing/pan; add `attachment_cuff.py`, whose outer row follows the exact retained skin boundary/morphs/weights and whose inner row belongs to Jaw. Actual fit and continuity remain unverified.
- `review_replacement_v2.py`: ClosedFront and unobscured OpenRight review of that future source.

`build_normal_mouth_v9p.py` has now generated and reopened the actual source successfully, and `review_normal_mouth_v9p.py` has produced all four views. Source SHA256 is `5be64281307b0d35541fb393311c63fcb95b4f7fdd38c2233249fb6a51d51d72`; `normal-mouth-v9p-review.json` records five successful native/guard exits and the **failed visual correction**. Closed lips remain intact, but tusks are hooked external spikes and the open view still hides them, with poor dental/tongue depth and lip/chin overhang. The full range, neutral Head/dental geometry, body bind and all action curves remain intact. Do not treat numerical tusk clearance as anatomical acceptance or rebase the mechanism on an allegedly accepted Natural bite.

All jobs use the shared heavy-task guard and require root's serialized handoff. No shared runtime export is changed by these isolated source studies.
