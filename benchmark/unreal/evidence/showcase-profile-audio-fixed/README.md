The actual Windows Unreal package recorded this [74.833-second video](unreal-showcase.mp4) at 1920×1080/30fps using the Balanced renderer and opt-in Profile skin candidate. This is recorded output, not a game-frame-rate measurement. The package, game, guard and capture coordinator exited successfully.

The engine-only WAV now contains the full **72.000 seconds**, without padding or time stretching. Black-frame, frozen-frame, motion and audio-signal checks pass. The video contains 2,245 frames and one repeated compositor frame. Fine audiovisual synchronization and listening review remain pending.

All 17 decoded review images were inspected. The [wider Krag shooting view](frames/action-47.4-krag-shoot.png) and [melee view](frames/action-46.0-krag-melee.png) now retain the active arm and weapon. The [wide pair](frames/frame-03.png) and movement samples retain feet; the [Nib expression](frames/expression-31.4-nib-playful.png) retains ears and shows its dark blue tongue. This sampled review is not an all-frame framing proof.

**Character art remains rejected.** Krag anatomy, armpit deformation and grip; Nib eyes, sparse fur and clothing; and hard shaded-face contrast need further work. The explicit Nib HUD text now correctly says “Restores ordinary function. No upgrades.” The Profile shader is a measured-review candidate, not final skin approval.

Startup diagnostics confirm an effective realtime Skylight and enabled Lumen. The single 1.52km terrain mesh has one Lumen card and a valid 18×18×18 distance-field indirection grid. That coarse representation is a diagnostic finding, not an established cause of the dark facial shadows. Lighting and shared textures were unchanged.

[Review and hashes](review.json), [package receipt](package-result.json), [capture report](unreal-showcase-capture.json), [runtime log](runtime.log). The initial coordinator failure and bounded retry are preserved: an empty startup log caused a null-regex exception before recording; explicit empty-log handling and owned-process fallback cleanup fixed it. The old Generic package and rejected short-audio recording remain archived.
