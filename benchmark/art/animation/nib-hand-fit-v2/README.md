# Nib hand proportions v2 — explicit bind migration

The old left-digit chains incorrectly made the index and little fingertips extend 8 mm beyond middle/ring. This actual source fits the CC0 anatomical hand uniformly and replaces the fourteen left-digit rest bones with corresponding reference joints. All other 65 bind matrices remain exactly unchanged. The hierarchy still contains 79 bones.

This is an intermediate source: its inherited left-digit action rotations are stale after the rest-frame change. Use the subsequent `nib-action-hands-v2` source for posed review, where all seven canonical takes have regenerated digit tracks. Do not merge these clips onto the old bind.

`hand-fit.json` preserves exact old/new source hashes, changed joints and reference provenance. Frozen executed recipes and process records are retained. No engine export or art acceptance.
