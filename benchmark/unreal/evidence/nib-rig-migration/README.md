# Expanded Nib rig: import preparation

This is a source compatibility audit and a reversible cache migration recipe, not a new engine import. The current Windows executable and shared assets remain unchanged. The 79-bone Nib study, new whole-body clips and six-second Idle are isolated candidates; anatomy and motion are not artistically accepted.

The Windows read-only plan passed: the existing three Nib variant folders contain 30 `.uasset` packages, accompanied by three validation receipts, totaling 299,751,295 bytes. There are no separate `.uexp` or `.ubulk` files currently. The helper preserves every file in each folder, including those sidecars if present. See [actual inventory](read-only-plan.json) and [preparation checks](preparation-checks.json).

A small independent filesystem fixture actually exercised Archive and Restore in a task-owned temporary tree. All 39 original files, including `.uexp`/`.ubulk` sidecars, matched their hashes after restore. A replacement package was retained separately. Corrupting an archived sidecar then caused Restore to reject the archive before changing the restored files. This fixture used a distinct mutex; it did not touch the actual cache or launch an engine. Production Archive and Restore have not run.

## Compatibility findings

| Concern | Current implementation and required next check |
| --- | --- |
| New hierarchy | The proposed source has `EarTip_L/R` below `Ear_L/R`, `ForearmTwist_L/R` below `LowerArm_L/R`, and `Hand_L/R` reparented below the twist bones. Preserve the entire matching mesh/skeleton/clip set. |
| UE skeleton reuse | Installed UE 5.8 `FbxSkeletalMeshImport.cpp`, lines 2196–2233, loads an existing same-name Skeleton and calls `MergeAllBonesToBoneTree`. Its failure dialog explicitly identifies inserting a bone between existing nodes. Archive the old generated folders before importing this hierarchy; do not rely on unattended regeneration of an old Skeleton. |
| Bone counts | Current authored Nib75 imports as 76 mesh bones in UE because the `Nib_Rig` wrapper remains above Root. Verify all authored bone names and parents separately from that wrapper. If unchanged, the expanded source79 would import80; that has not been measured. Unity renderer-bone counts may exclude unweighted controls, so inspect the full Transform hierarchy there. |
| Animation source | UE imports seven explicit standalone FBXs against each imported Skeleton. Unity's manifest class does not consume the standalone `animations` map; it imports seven embedded takes from each assembled variant. A skeleton-only candidate is insufficient for the Unity demo. |
| Retargeting | Both runtimes use directly imported animation, without a humanoid/avatar retarget stage. Unity uses Legacy and preserves bone/object controls. Neither custom runtime has a fixed 75/79-bone allocation. |
| Bone translation | Installed UE `Skeleton.h` initializes fresh bone translation-retarget modes to `Animation`; this importer does not override them. Blender's observed auto-connected edit bones can suppress translated children during its own roundtrip, but that does not establish suppression in either game engine. Verify actual imported Pelvis and TongueTip motion before acceptance. |
| Ear layering | EarTip bones remain descendants of FaceRoot, so the separate facial layer includes them. New body clips must also carry their own authored ear/facial acting. |
| Arm adaptation | Current custom IK addresses thigh/shin/foot chains only. It does not override forearm twist or reparented hands. Muzzle/aim lookup and corrective drivers resolve named controls dynamically. |
| Cadence | Actual clip duration and manifest cycle duration/speed drive playback in both engines. Six-second Idle has no hard-coded duration cap. Contact phases/stance come from the manifest; matching source metadata still needs promotion and actual engine review. |
| Validation gap | Existing UE import checks required bone names, control variation, morphs and limb/bind scale ratios, but not the complete authored parent map. Before acceptance, compare the actual imported hierarchy and bind transforms with the new candidate's source contract. No expanded-rig import is claimed by these checks. |

## Reversible migration workflow

Use [Migrate-NibRigCache.ps1](../../../tools/unreal/Migrate-NibRigCache.ps1) at a reserved process boundary, after a full matching character candidate passes source/FBX checks and root authorizes promotion. `Plan` is the default and changes nothing.

1. Preserve the current executable/package receipt and record the promoted candidate hashes. Close only task-owned editors for this project. The helper refuses an open matching editor or an occupied shared heavy-task mutex.
2. Run `Archive` with a fresh explicit path under `benchmark/local/unreal-rig-migrations/`. It verifies each current receipt's package hashes, hashes all folder contents, moves the complete folders and receipts, then verifies the archived bytes and writes `migration.json`. Shared FBXs, textures, map/material packages and the Windows build are untouched.
3. Use `Invoke-IsolatedImport.ps1 -Variants Nib_Natural,Nib_GripReplacement,Nib_LegReplacement -SkipAssembly` from PowerShell to create fresh matching packages at the original loadpaths. Each variant still owns a separate guarded editor process. The coordinator now avoids saved-package validation when the generated folder was deliberately archived.
4. Require the new authored hierarchy, bind scales, morph/driver mappings, seven named clips, actual durations, face/ear/twist variation, weapon markers and ground contacts to pass. Then assemble all seven current receipts and inspect an actual engine frame/pose before packaging. Source hashes and generated-package hashes remain authoritative.
5. If restoration is needed, `Restore` requires the completed exact-project archive and verifies every original file. It preserves any replacement folders/receipts separately, copies the old cache back and verifies it. Restoration does **not** revert promoted shared sources or bypass stale-source checks; reverting a candidate source snapshot and rebuilding assembly remain explicit separate decisions. The original package remains runnable throughout.

Example invocation (prepared, not executed against production):

```powershell
.\benchmark\tools\unreal\Migrate-NibRigCache.ps1 -Mode Plan
.\benchmark\tools\unreal\Migrate-NibRigCache.ps1 -Mode Archive -ArchiveDirectory D:\Dev\Krag-Kings\benchmark\local\unreal-rig-migrations\nib79-before-import
# After an independently reviewed candidate and its actual import outcome:
.\benchmark\tools\unreal\Migrate-NibRigCache.ps1 -Mode Restore -ArchiveDirectory D:\Dev\Krag-Kings\benchmark\local\unreal-rig-migrations\nib79-before-import
```

## Independent animation exporter audit

The initial isolated exporter could inherit unkeyed new-bone transforms from another action. Blender's installed all-actions exporter restores its initial pose between takes, so an initial nonzero forearm twist could contaminate older actions even when each named take was selected. The initial validator also lacked exact seven-take coverage, parent-map/full-bind comparison and posed-scale checks.

These concrete findings were sent to the owning animation author. The revised prepared exporter resets pose channels, explicitly selects the action slot and adds neutral tracks only for missing transform components in the disposable export process. The revised validator adds canonical names/coverage, hierarchy, source-to-imported full bind matrices and posed scale. Those are source-reviewed corrections; fresh export/roundtrip execution is tracked by the animation owner. They do not establish engine import, mesh deformation or artistic acceptance.
