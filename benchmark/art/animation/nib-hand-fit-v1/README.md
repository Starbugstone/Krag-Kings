# Nib anatomical hand fit v1 — actual source and poses

Rebuilt the natural left hand from the licensed CC0 Blender Studio hand cage, using topology-connected digit domains before warping. This avoids blending a finger with adjacent fingers across empty space. The existing 79-bone bind, canonical actions and component name are preserved. The previous mesh is archived inside the editable source.

The saved hand has 13,194 vertices and 13,192 faces. Its skinning uses at most four influences. The original cage coordinates are retained as a mesh attribute. See `hand-fit.json` for exact input/output hashes, source provenance and fit measurements.

Eighteen actual palm/back/edge poses are in `hand-review/`. Inspected Idle and Run views show rounder fingers and less web distortion. The old glove rivets and wrist box still float or fit poorly; the subsequent glove study replaces those details. Forearm wraps remain separate tubes, and right-hand/weapon contact remains unfinished.

This is a left-hand source improvement, not final character acceptance or an engine import. Frozen recipes and original guarded execution evidence are retained.
