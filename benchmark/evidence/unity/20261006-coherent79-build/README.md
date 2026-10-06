# Unity coherent79 build — actual technical integration

The guarded Unity6000.4.4f1 import and Windows build both exited0 and emitted the required success marker. All115 delivered Nib files match after import, all75 retained `.meta` files were left in place, and the12 obsolete texture/meta pairs are archived. Of those retained files,72 remain byte-identical; Unity updated3 model importer configurations. The earlier receipt check incorrectly expected all metadata bytes to remain unchanged; that failure is preserved. Prior GUIDs were not separately snapshotted, so no independent before/after GUID proof is claimed. The prior d431 executable is preserved intact.

Allthree Nib variants import79 bones,25 morphs and allseven clips. Idle is6seconds, with14 varying torso curves and16 ear curves; Walk/Run each retain15 torso curves and4 ear curves. These counts establish that animation survived import, not natural-looking movement. Unity reports750166 Natural triangles; see each variant in `nib-import.json` for actual imported totals.

Krag remains on the previous shared68-bone source and2-second Idle. The newer Krag whole-body/hand work is not in this build. Runtime visual, input and performance checks of this executable remain pending, and neither character has artistic acceptance.
