# Semantic Krag jaw replacement studies

The actual v1 source is `benchmark/art/krag/Krag_IronJaw_Replacement_v1_WIP.blend` (SHA256 `20c48d2e23c112ebca5b855247eca3e3aea630b1c463e8f99d4c4594adb5f031`). `ironjaw-replacement-v1-review.json` records two real failed clearance views. Natural geometry/weights/bind/actions were preserved and replaced mandible/lower oral surfaces genuinely removed. The inherited lip-shaped casing, shield intersection and opening cheek gap still fail.

The following are **prepared, syntax-checked, ungenerated**:

- `refine_replacement_v2.py`: rebuild the rigid lower shell as an authored formed U housing/pan; add `attachment_cuff.py`, whose outer row follows the exact retained skin boundary/morphs/weights and whose inner row belongs to Jaw. Actual fit and continuity remain unverified.
- `review_replacement_v2.py`: ClosedFront and unobscured OpenRight review of that future source.
- `audit_natural_mouth_opening.py`: one read-only decomposition of actual natural frame146 into Basis, bone-only, JawOpen-only and combined motion, with actual evaluated-LBS verification and tooth/gum/tongue supports. It does not reduce the expression range or mutate the source. Its result must guide the normal-mouth repair.

All jobs use the shared heavy-task guard and require root's serialized handoff. No shared runtime export is changed by these isolated source studies.
