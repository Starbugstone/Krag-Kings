# Decision register, verification and release acceptance

5 October 2026 · [Realization plan](15-poc-realisation-plan.md) · [Persistent context](../PROJECT_CONTEXT.md)

“Confirmed” records user direction. “Proposed” identifies a production recommendation. “Pending” is an unanswered choice. A future gate is not permission to invent an answer or a claim the work passed.

## 1. Confirmed user decisions

| ID | Decision |
| --- | --- |
| D01 | Narrated material illustrates world/lore; it is not the final scenario or scripted campaign. |
| D02 | Downloadable Windows build with visual quality prioritized. |
| D03 | Polished tactical mission, squad customization and compact persistent injury/bionic recovery loop. |
| D04 | Compare Unreal and Unity before selecting the engine. |
| D05 | Playable objective: depot engine release, loading and extraction, with boarding opportunities. |
| D06 | Authored clothing/armor/tattoos, color and tattoo placement controls, fixed body proportions. |
| D07 | Include partial replacements, eyes/jaw and complete arm/leg replacements, subject to species compatibility. |
| D08 | Krags prefer armor and bionics over clothing; minimal clothing does not imply minimal armor. Nibs have more desert clothing/equipment variety and fewer bionic options. |
| D09 | Match the concept art in detailed 3D, with special attention to squad models and merchandise consistency. |
| D10 | Merchandise masters support collectible figures and printed/illustrated products. |
| D11 | Produce campaign, base-building and world-map concept art in the same style; desert scrapyard travel and fort progression are approved exploration subjects. Names, geography and story remain provisional. |
| D12 | Tin Cans are tall round scrap barrels/tin cans refitted into extensively customizable machines, piloted only by Nibs. Concept art and integration plan only for this POC; not playable. |
| D13 | Audio includes music, effects and AI-generated English character speech/quips. Krags are deep and gruff; Nibs higher-pitched and faster-speaking. Keep recordings replaceable with actors if finances allow. |
| D14 | No budget/deadline set; prioritize quality and report real production dependencies. |
| D15 | Use the user's ASUS ROG Strix G17 as the medium-range performance reference; its exact configuration is locally verified below. |
| D16 | Campaign presentation must be a UX/UI concept showing management and travel decisions. The first cinematic campaign sheet does not satisfy this requirement. |
| D17 | World map must show a much larger, sparser region, taking strategic viewing scale and spacing from Total War as a reference while retaining the original Krag Kings style. Geography remains provisional. |
| D18 | Modular Tin Can sheet 14 is approved as the visual direction. Production turnarounds, clearances and module mechanics still need review. Base-building and revised campaign/map concepts remain awaiting user review. |
| D19 | Implement matched Windows Unity and Unreal character/dune demos with selection, terrain-following run movement, melee/shoot/hit demonstration keys and multiple bionic variants, including the Krag crusher claw. Nib implants restore function without upgrades. This is the engine comparison, not an expansion of the depot mission. |
| D20 | Limited battlefield character counts and turn-based combat support prioritizing detailed hero models. Continue natural-character likeness and animation passes against the selected concepts, then give bionic add-ons the same quality review. No specific simultaneous unit count has been set. |
| D21 | Implement very expressive facial animation for actions, close-ups and future cutscenes, supported by credible facial skeletons and muscle-aware body deformation. Validate facial and body deformation in both engines; a basic body skeleton or static facial likeness is insufficient. |
| D22 | Develop provisional concept-consistent mouth interiors and expression sheets for user review while continuing the rigs. This authorizes exploration, not final approval of unseen anatomy. |
| D23 | Krag walking must convey weight and ground impact; Nib movement is light-footed, stealthy and nimble. |
| D24 | Nib tongues are dark blue. |
| D25 | Nibs are playful engineers, physically weak and a little cowardly; playful tongue-out acting is appropriate. Krags are serious brute force who love big guns and smashing skulls, are fearless and feel little pain; they do not clown around like Nibs. Apply this to personality/animation/audio, without silently introducing panic or forced-retreat rules. |

## 2. Resolved follow-up questions

| ID | User answer | Result |
| --- | --- | --- |
| Q01 — resolved | Concept/integration plan for Tin Cans; keep current playable mission scope | No additional Tin Can gameplay, animation or audio-production dependency |
| Q02 — resolved | English AI voices; deep/gruff Krags, higher-pitched/faster Nibs; possible later actors | Voice auditions follow that direction; provider and specific accent remain production review items |
| Q03 — resolved | User's ASUS ROG Strix G17 as medium-range reference | Local hardware inventory verified; engine trials and performance measurements still pending |

All three scope/direction questions have been answered. The review items below remain proposals to resolve at their production gates.

## 3. Production decisions to resolve at the named gate

These have not been silently approved. They are concrete review items for the plan, with a recommended decision process rather than hidden defaults.

| ID / gate | Decision needed | Proposed next evidence |
| --- | --- | --- |
| P01 / G0 | Final POC cast, identity differences and exact wardrobe/armor/tattoo catalogue | Review proposed finite manifest in file 16 against the four-person squad |
| P02 / G0 | Full-limb item effects, strain and species/side fit | Review one table of legal/illegal complete/partial assemblies and sample loadouts; no automatic relaxation of Nib limits |
| P03 / G0 | Ball diameter/cradle and conflicting truck gun/arm-interface views | Side-by-side blockout alternatives with matching concept crops and route/fit constraints |
| P04 / G0 | POC end state for unrecovered crew when rescue missions are not included | Proposed truthful captured/missing result and bounded demo ending/restart; preserve future continuation data |
| P05 / G0 | Draft rule baseline: AP, activation, damage, casualty and recovery tuning | Review files 05/06/10 as editable test values; narrative events excluded |
| P06 / G1 | Engine/renderer/version and export presets | Common-scene Unreal/Unity report; select after comparison |
| P07 / G2 | Final likeness, neutral anatomy, complete-limb designs and unshown surfaces | Approved turnarounds, sculpt, fit scene and animation evidence |
| P08 / G2 | Tattoo zones/layer limit and material palettes | Interactive appearance prototype and skin deformation tests |
| P09 / audio preproduction | Music/performance direction and exact line inventory | Short theme and voice auditions plus contextual bark test |
| P10 / merchandising | Figure scale/process/pose/articulation and print formats | Vendor requirements, a selected loadout/pose and proof plan; runtime asset is not a manufacturing signoff |
| P11 / source completeness | Location of the cited original `game-design-notes.md`, if it is still relevant | Review it if supplied; this audit covers only the available pack |
| P12 / facial authoring | Mouth interiors, complete teeth and tongue are unseen in the supplied concepts | User authorized provisional designs and expression sheets; review their actual mesh rendering before treating new anatomy as final |

## 4. Traceability from requirement to evidence

| Requirement | Build owner / dependency | Acceptance evidence |
| --- | --- | --- |
| Concept likeness | Art direction + character team / G2 | Approved front/side/back/close-up and turntable comparisons under neutral and game lighting |
| Modular clothing and armor | Character/technical art + equipment rules | Runtime swaps on all supported profiles; armor stats/mesh agree; no exposed gaps in pose matrix |
| Tattoos | Materials + appearance persistence | Same design/placement through deformation, wardrobe changes, partial/full replacement, LOD and reload |
| Complete replacements | Anatomy/rig/gear integration | Correct region exclusion, side, function, fit, strain, animation and treatment path |
| Mixed tactical combat | Gameplay/navigation | Mission completed using both vehicle and infantry contributions; meaningful boarding opportunity |
| Boss/Nib scale | Art + geometry | Actual body/gear clears legal routes and seats; invalid fits explained; no temporary rescaling |
| Persistent consequences | Campaign/persistence | Mission → debrief → treatment → restart application → completion → redeploy with same identity |
| Audio personalities | Audio/voice + dialogue scheduler | Approved auditions, intelligible contextual speech, correct captions and no repeated/stale barks |
| Wider-game vision | Concept art | Campaign UX/UI shows management/travel decisions; the regional map has broad terrain and sparse small locations; fort and map concepts retain original style. All are labelled concepts and reviewed by the user. |
| Windows delivery | Build engineering + QA | Clean-machine startup, offline play, settings, saves, complete run and reliable reset/exit |

## 5. Rule and state verification

Retain the useful IDs in the old file 05 instead of replacing their intent. Automate business-critical invariants and state transitions; use the real scene for motion, presentation and usability.

| Group | Required cases |
| --- | --- |
| A — actions | A01–A04: preview/cancel spends nothing, driver swap does not refresh movement, board/dismount preserves AP and used state; rejected and duplicate commands consume nothing |
| G — geometry | G01–G03: full sidecar footprint, rotating high-speed sweep, wheel loss during movement; add boss/large gear, full-limb bounds, stair/recovery pair and wreck blocking |
| J — jetpack | J01–J03: destination and entire arc checked; interrupted jump has one resource spend and valid outcome; no hidden free arrival action |
| W — signature equipment | W01–W04: claw exposure/reach, supported jaw, entire ball sweep/friendly risk, crane consumes cargo capacity; missile W05 only if later scoped |
| K — species/body | K01–K06: pain/fear filters distinct from structural function, natural armor, boss fit, heavy-gun support and persistence |
| C — cargo/control | C01/C02 and M01: real fit and capacity, mixed allegiance, no magical cargo on captured wrecker, carrier loss handled |
| R — aftermath | R01–R08: no duplicate rewards, treatment/availability, linked wound restoration, species/strain, save during recovery, non-kill contribution, elective fit, stable downed |
| E — extraction | E01/E02 in core: cargo exit does not teleport remaining crew; foot retreat/partial result works. Capture classification retained; rescue/event cases require expanded scope |
| S — persistence | S01 plus loadout/appearance, scene/save versions, RNG continuity, atomic backup, invalid references, missing content, interrupted write and stale async completion |

Add high-value property checks: every entity occupies one place; no duplicate station/body region ownership; AP/fuel/charges nonnegative; inventory item consumed once; appearance rebuild does not alter health/traits; expired/ineligible actors cannot emit authoritative commands. Seeded scenario replay must produce the same outcomes in the same build independent of camera movement and display frame rate.

Full-limb checks must cover nested overlap (arm plus forearm), bilateral fitting, disabled implant function, retained tattoo history, garment conflict, strain accounting and a Nib attempting an unsupported heavy part. UI and imported save paths use the same rules.

## 6. Art, animation and audio matrix

Cross body profile with supported anatomy state, clothing/armor layer, weapon/pack and pose. Exhaustively cover interface hazards: shoulder/claw/sleeve, hip/full leg/trousers, mechanical foot/boot, eye/lid, jaw/scarf/tusks, Nib ears/headwear, pack/harness, seat clearance and hand grip. Cover the remaining catalogue with systematic combination sampling and every canonical outfit. Store the matrix and captures with asset versions.

Review face and silhouette at close workshop zoom, normal tactical distance, during motion, in shadow and at LOD transitions. Pair a technical reviewer with an art review; a passing import validator is not sufficient likeness evidence.

Facial reviews cover blinks, gaze, lip closure, speech shapes, jaw/teeth/tongue fit, asymmetry and species personality. Include the Nib's dark blue tongue-out gesture and cautious/flinching responses, versus serious, fearless Krag acting. Validate portable facial/muscle corrective drivers in both engines and body volume during shoulder/elbow/hip/knee extremes. Gait reviews require heavy, planted Krag impacts and light, nimble Nib contacts on actual dune slopes.

Audio checks include cue truthfulness, clean looping, voice priority, cooldown, race/individual distinction, subtitles, mechanical jaw speech, effect synchronization, volume settings and absence of stuck loops after reset/load. Test the loudest supported encounter on headphones and ordinary speakers. See [19](19-poc-audio-and-voice-plan.md).

## 7. Packaged build and performance

Test the packaged Windows executable, not only editor play. Record OS/GPU/CPU/RAM/driver, build/content version, display/internal resolution, graphics preset and upscaling for every result. Use the agreed demonstration machine and minimum supported machine; if these are the same initially, disclose the limited coverage.

### Verified reference-machine inventory

Read locally on 5 October 2026 through Windows CIM and NVIDIA's GPU query. No serial numbers or unrelated device identifiers were collected.

| Field | Observed value |
| --- | --- |
| Model | ASUS ROG Strix G712LV_G712LV |
| CPU | Intel Core i7-10750H @ 2.60 GHz |
| Dedicated GPU | NVIDIA GeForce RTX 2060 |
| GPU memory | 6144 MiB (6 GiB) |
| System memory | 31.8 GiB reported; approximately 32 GB installed class |
| Active display | 1920 × 1080 |
| NVIDIA driver at inventory | 591.44 |

Run both engine trials at 1080p on this laptop, recording internal resolution/upscaling and quality settings. Ensure the packaged game uses the dedicated NVIDIA GPU, not the integrated Intel adapter. Document AC/battery status, performance mode and sustained thermal behavior for comparable runs. These checks establish test conditions; do not change power settings without a separate need. The proposed 60 fps target remains subject to measurement, and a broader minimum-PC specification is not yet established.

Proposed targets for hardware selection: smooth 60 fps gameplay/camera at the agreed resolution, p95 command-preview latency at or below 100 ms on the full scene, no repeated shader/streaming stalls during the rehearsed presentation, and memory remaining within the hardware's available budget after repeated mission/loadout cycles. These targets are not achieved measurements and are not a guarantee for every Windows PC. Establish p95/p99 frame-time and load-time thresholds with the benchmark report.

Exercise cold launch, graphics changes, windowed/fullscreen, alt-tab, audio settings/device behavior, unsupported/corrupt saves, file-write failure, mission reset, quit/relaunch and missing-dependency behavior. Saves go to an appropriate writable user location, never an installation folder requiring elevated privileges. Keep the last valid checkpoint when a write fails and give a clear message.

Build validation checks all referenced assets, textures, audio/subtitles and content IDs. The build must not require an editor, a developer workstation path or network service for normal play. Save migration/rejection behavior and version compatibility are documented.

## 8. Unassisted playtests and release gate

Run internal scenario tests, then fresh-player sessions. Ask testers to customize a character, identify its equipment, plan a route, board, understand an interrupted move, recover someone and finish extraction without reading design documents. Log failed attempts and comprehension, not only wins. Revisit mission length and controls from observed play.

Proposed minimum release evidence includes complete runs using at least two tactics and each supported win/retreat/loss outcome; stable- and fatal-casualty fixture checks if the mortality rule is retained; treatment/elective replacement/redeployment; cold save/reload; long customization sessions; and repeated mission reset. Choose final run counts after the test matrix is sized; passing a few rehearsals is not statistical proof of no bugs.

| Severity | Examples | Release rule |
| --- | --- | --- |
| Critical | Crash, corrupt/lost save, progression blocker, unfinishable mission, action duplication exploit, missing shipped asset | Zero known open |
| Major | Wrong preview/outcome, persistent anatomy/armor mismatch, visible hero clipping/likeness failure, unusable UI, unintelligible required audio, target-machine performance failure | Zero known open on the supported POC flow |
| Minor | Bounded presentation defect away from key views, nonessential wording or polish issue | Document and explicitly accept; do not hide it under a “bug-free” label |

Every fix of a critical/major defect gets a focused regression check, plus impacted integration cases. Do not rerun unrelated checks indefinitely after they pass. Freeze the release candidate, retain a build hash and known-issue report, and rehearse on a clean Windows machine. Store a working backup build and clearly labelled demo checkpoints.

## 9. Handoff checklist

Deliver the executable/package and checksum, controls/quick-start, graphics/hardware results, complete source and build recipe, approved design/asset manifests, editable character/environment/vehicle masters, texture and animation sources, audio sessions/stems/voices/subtitles, reference comparisons, test report and issue status. Include actual real-time gameplay footage separately from offline renders and strategic concept art.

Investor materials should state what is playable, what is demonstrated visually, what has been validated and what remains on the roadmap. This is the defensible quality commitment; an absolute guarantee of no undiscovered defect is not one.
