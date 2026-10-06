# Verified whole-body motion on current Krag art

Prepared only: no merged source or review exists yet.

`merge_v4.py` pins the actual root-owned v4 study and either the next saved oral candidate or the preserved v9p source. It requires an exact match of all 68 rest bones, parents and rotation modes before loading only the seven canonical actions. Those complete takes retain the v4 facial timing, normal-speed blinks and six-second Idle. The matching locomotion metadata travels with them.

Every current mesh, shape key, UV, weight and corrective-driver contract must remain unchanged. The merged file is saved compressed, reopened, and compared against the donor's exact take hashes and five actual full-skeleton samples per take. The separate 72-bone reconstructed hand is deliberately rejected by this recipe; it requires root's explicit later migration.

`v9p-fallback-merge.job.json` makes movement integration independent of the next oral-fitting experiment. `v9r-merge.job.json` instead consumes the actual v9r receipt once it exists. Their review jobs render four phases from Walk, Run and Idle in front and side views. Workbench shadows are disabled because the prior matched diagnostic proved its floor strips were rendering artifacts.

Neither source is an art acceptance or shared/export promotion. Mouth, facial likeness, hand shape, cloth and armor defects remain explicit until actual corrected views and engine validation exist.
