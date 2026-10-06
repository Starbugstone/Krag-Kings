# Coherent Nib motion source v1 — failed saved-action retention

The in-memory integration checked all seven canonical v7 motion takes, but the reopened saved source does **not** retain the six inactive takes. Appended actions lacked fake users. The following hand/action step stopped on missing Shoot before export. This source is invalid for playback/export; see the subsequent v2 fix with explicit saved-file readback. The 79-bone bind/hierarchy is exactly unchanged; 402 mesh components retain their geometry, morphs, UVs, skin weights and authored attachments. All seven action curve hashes match, and 17 evaluated bone-matrix samples per clip have zero difference from the motion study.

The source contains captured whole-body Walk/Run, a six-second breathing/weight-shift Idle, and ear motion. This merge does not include the separate corrected anatomical hand yet. Apply that fourteen-bone migration once after this old-bind merge, then regenerate all left-digit clips and refit glove details.

The source retains the recorded shoulder/axilla skinning fault, unaccepted face and groom, thin clothing edges and old restorative upper-body variant. No full combined render, export, native engine import or artistic acceptance is claimed. This is a technical integration checkpoint.
