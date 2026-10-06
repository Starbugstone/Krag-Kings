# Basic POC: scope, build order and acceptance

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Production update — 5 October 2026:** the current delivery target is [15 — investor POC realization plan](15-poc-realisation-plan.md). This file retains the mechanics sequence and tuning/test references. Placeholder presentation is an internal stage, not investor acceptance. Windows delivery, detailed modular characters, full-limb replacements and audio are now required; wider campaign systems are scoped separately. Narrative examples are not the final scenario.

**Purpose:** give development a bounded playable target. This is a specification, not a claim that a prototype or 3D models have already been implemented. The default rules here are provisional decisions for a test build; change them through measured playtests.

## 1. What the POC must answer

Can vehicle movement, exposed crew, infantry cover, boarding and vertical access work together in a readable turn-based encounter? Can the player understand the risk without managing several unrelated interfaces? Does a giant claw, a metal jaw or a wrecking-ball swing create a memorable choice? Does preserving a crew member or capturing a rig create a better choice than simply shooting everything?

The deliverable is a local, single-player encounter with a restart button, an elementary enemy AI, an objective with success/failure, save/load at stable decision points, and a simple equipment/debrief view, followed by a connected XP, bionic-perk, recovery/event and retreat/rescue slice. It is not the whole campaign.

## 2. Small content roster

| Asset or system | Required POC content |
| --- | --- |
| Friendly rigs | One heavy truck and one bike with passenger sidecar |
| Enemy rigs | One truck using the same base chassis with the wrecking-ball fitting |
| Friendly crew | Gorr: larger Krag clan boss at the truck gun station, with a portable heavy gun and optional claw/jaw fitting; Fiz: Nib driver/mechanic; Brok: ordinary-sized Krag sidecar boarder with crusher claw and iron jaw; Tikk: Nib bike rider with optional jetpack |
| Enemy crew | Driver and crane operator aboard their truck; one foot guard |
| Map | One 120 × 120 m hand-authored depot, plus a tiny development test pad |
| Terrain | Packed ground, rubble, solid cover, one breachable barrier, ruins, one gantry with stairs |
| Weapons | Basic gun, portable heavy gun, mounted gun, basic melee, crusher strike, bite and wrecking-ball swing |
| Equipment | Fiz: repair tool with 3 repair charges; burst jetpack, crusher claw, iron jaw; servo/piston leg, light grip and optical implant comparisons; standard casualty recovery sling |
| Objective props | Engine cradle, console, transportable/dismantlable engine, portable scrap and separate foot/vehicle extraction access |

Four friendly and three enemy characters are enough to expose the important interactions. Additional squads, buggy meshes, dedicated haulers and recovery rigs are later content. A truck variant can demonstrate cargo and capture without requiring three new vehicle models.

The standard friendly truck carries the mission engine. The enemy wrecker has no usable cargo hold; capturing it gives a fighting asset rather than an instant spare hauler. Keep the rocket truck as the P8 follow-on fixture, reusing the same chassis and retaining a carrier where the engine objective is used.

Tikk starts riding the bike. To use the jetpack, they must stop/leave the rider station legally; the player sees what happens to the bike. Fiz's repair and driving tasks compete for the same actions. Gorr can operate the gun or dismount to use his portable heavy weapon. Brok's sidecar approach demonstrates a passenger boarding while the driver keeps control.

The boss body template and Krag traits are part of the first slice. The standard truck's gun station and exits must fit Gorr; the ordinary sidecar is deliberately too small. Keep an infantry route open to the larger boss and show the model beside Brok in loadout or a simple test pad. Four friendly characters remain sufficient.

## 3. Required interaction set

Implement selection and inspection; alternating groups; per-character action budgets; curved vehicle movement; speed bands; foot movement; shooting at exposed crew/components; component disablement; mount/dismount; station changes; sidecar occupancy; ordinary and jet-assisted boarding; local movement aboard a rig; a basic sabotage/hijack; repair; cargo loading; objective progression and extraction.

Implement one planned crew action during a vehicle move and one reserved shot reaction. Both use the same command/resolution rules as ordinary actions. Broader chains and special reactions can wait.

The jetpack needs legal landing geometry, charge use, action cost, exposure and a defined interruption outcome. The implant needs a visible model change, a displayed modifier and persistence. Neither needs a full upgrade tree.

The revised first slice also needs a crusher strike against reachable exposed targets, a jaw attack from a supported/hanging node, and one validated wrecking-ball swing. These signature actions demonstrate the requested wacky tone early. They use existing AP, melee/contact, damage and exposure systems. Exact draft rules are owned by [08-outrageous-machinery-and-weapons.md](08-outrageous-machinery-and-weapons.md).

### Intentionally simplified for the POC

- Damage uses component health and intact/damaged/disabled mesh states; full deformation is later.
- Vehicles follow validated kinematic paths; collisions use bounded outcomes rather than a realistic vehicle physics simulator.
- The demolition ball follows a validated attack/recovery animation and swept collider; a simulated chain of rigid bodies is not required. The claw and jaw use simple mesh/pivot animations.
- Infantry uses a small hand-authored walk graph and traversal links; no procedural multi-storey navmesh is required.
- The fort is represented by a loadout/debrief screen, not a construction game.
- Injuries use one structural leg wound and stable downing without bleed-out. One saved first-incapacitation mortality roll demonstrates rare fatal outcomes; the exact 2% tune is provisional. Compatible bionics grant perks and require three campaign days of fitting/recovery, including elective installation.
- Progression uses capped debrief XP, one threshold, three simple perk choices and a duplicate-award guard. One treatment place and event-aware day advancement enforce deployment downtime. Four eligible event entries, portable-scrap foot return and one rescue variant form the connected follow-on. A full item market, real-time waiting and economy remain outside scope.
- Species compatibility uses anatomical sockets plus proposed strain: Krag 8, Nib 2 with lightweight restorations only. Entry servo replacements consume strain; only Krag upgrade versions grant an extra equipment perk. Nib implants restore ordinary function without upgrades. The POC supplies one compatible leg part for the recovery fixture.
- The map and rival are hand-authored. Campaign map generation, raid construction, multiplayer, accounts, monetisation and mobile shipping are outside scope.

## 4. Rusthook depot completion rules

**Primary objective secured:** release the engine, load it into a compatible stopped carrier, then extract that carrier with the engine aboard. This does not end tactical play while friendly crew remain on-map.

**Final extraction:** account for every friendly/cargo holder through actual exit or explicit abandonment. Show captured/missing crew, fatalities and abandoned assets before committing the debrief.

**Partial recovery:** leave with surviving crew but without the intact engine. Portable scrap can leave with foot carriers; dismantling the engine produces four scrap bundles while losing the primary objective. A foot return takes longer and uses the daily campaign event clock.

**Battle loss:** all controllable friendly characters are incapacitated, or the player withdraws without the objective. Living abandoned downed crew in enemy territory become captives and create a rescue lead. An unusable carrier makes the intact-engine goal fail but still permits foot recovery and retreat. Terminal campaign defeat is separate: no available crew and no remaining authored rescue route. File 11 defines the first emergency-rescue fallback. A fresh-run restart remains available.

Do not require exterminating the enemy. A captured hostile truck is a valid carrier only if controlled, functional, compatible, has enough free cargo load and is actually extracted. The default POC enemy wrecker has no cargo capacity, so it does not meet that test. Control of a driver seat alone does not remove enemies elsewhere aboard it.

No turn limit is needed in the first tuning build. Add pressure only after the objective and movement are fun; a timer must not conceal an excessively long infantry approach.

## 5. Build sequence

| Milestone | Deliverable | Done when |
| --- | --- | --- |
| P0: project and state | Local scene, camera, units, state model, seeded rules, reset | A developer can launch it, select entities and restart the same fixture |
| P1: movement and turns | Foot and curved vehicle movement, speed bands, actions | Preview/commit agree; side changes correctly; blocked routes cannot be committed |
| P2: crew and transport | Stations, mount/dismount, sidecar, load validation | Location changes preserve identity/actions and obey fit/capacity |
| P3: contact and consequences | Shooting, component damage, basic ram, one reaction, wrecking-ball sweep | Damage changes legal actions; full sweep and first contact are resolved; wrecks remain truthful |
| P4: signature interaction | Board, move aboard, sabotage, driver takeover | Brok can reach an enemy node, spend remaining actions, and act normally next round without a reset exploit |
| P5: height and equipment | Jetpack, crusher strike, iron-jaw bite, comparison implants, wound state | Landing is validated; special attacks spend AP; fuel, equipment and wounds persist |
| P5 trait/size checks | Krag natural armour, pain/fear filters, heavy-gun support and larger boss body | Traits change the relevant rule; structural wounds remain effective; fit/cover uses actual body size |
| P6: complete encounter | Utility AI, console, engine loading, extraction, debrief, save/load | A full mission can be won, lost or abandoned through the UI |
| P6a: crew aftermath | Debrief XP, learned/equipment perks, elective fitting, strain, treatment and day advancement | Brok keeps learned perks, gains Power Step after recovery, and cannot deploy early; a healthy recipient uses the same process |
| P6b: connected consequences | Day-by-day events, stable casualty recovery, final extraction, foot salvage/journey and rescue variant | Events interrupt time correctly; abandoned living crew can be rescued; a lost truck does not strand surviving crew |
| P7: presentation pass | Readable final placeholders or selected model imports, sound/effects, usability | First-time testers can complete the essential interactions and explain outcomes |
| P8: follow-on missile fixture | Four-missile rack, two-projectile salvo, scatter, blast and ammunition | Full possible blast area is previewed; friendlies/cover/colliders resolve correctly; a carrier remains available for any engine mission |
| P9: Nib machinery fixture | One wheeled Tin Can, heavy-gun module, Needlebeam carbine and acquisition mission | Pilot/vehicle identity and AP remain distinct; no outgoing vehicle boarding; damaged locomotion permits pilot escape |

Build in three testable slices. **Battle proof:** P0–P6 plus the P7 readability pass; include stable casualties, their basic recovery and explicit final extraction. **Connected gang proof:** P6a/P6b add event-driven time, equipment progression and rescue/foot-return consequences. **Machinery follow-ons:** P8 and P9 are separate optional fixtures after those foundations. Walking Tin Cans, free-form assembly, a large perk tree and procedural campaign remain later work. The newly specified campaign rules do not block initial movement playtests.

Prioritise a playable greybox throughout. Concept art guides later models but does not block P0–P6. Replace one placeholder at a time, checking scale, collision and attachments after each import.

## 6. Starting tuning set

These values make an initial implementation possible. Keep them in editable content data rather than scattering constants through the UI or AI.

| Rule | First value |
| --- | --- |
| Actions | 2 per character per round |
| Vehicle movement | At most 1 normal move per chassis per round |
| Foot move / sprint | 10 m for 1 action / 17 m for 2 actions |
| Regular Krag / clan boss / Nib health | 10 / 14 / 7 |
| Krag natural armour | 1 against eligible physical hits; both regular and boss; worn armour handled separately |
| Mission XP / first perk | Participation 1 + primary success 2 + capped contribution 1; first perk at cumulative 4 XP |
| Structural leg wound | Move ×0.6, Sprint disabled, risky boarding -15 points; persists until restored |
| Replacement downtime | 3 campaign days: fitting 1 + recovery 2; patient excluded from deployment |
| Equipment perks | Servo leg +1 m Move; piston leg +2 m Move/+3 m Sprint; strongest leg bonus only, then learned bonuses |
| Casualty | First downing only: 2% fatal / otherwise stable; no bleed-out or repeat mortality rolls |
| Daily random event | Initial 35% chance, eligible table, max 1/day, 2-day type cooldown; seeded/persisted |
| Foot scrap load | Nib 1 / Krag 2 / boss 3; burdened Move ×0.75, no Sprint/jetpack |
| Return duration | Motorised B; foot 3B; burdened/casualty foot 3B+1; events each day |
| Total implant strain | Krag/boss 8; Nib 2, lightweight strain-1 parts only, including basic restorations; species/socket checks also required |
| Krag pain/fear response | Ignore pain-only penalties and fear-driven panic/routing; keep structural injury and physical displacement |
| Rifle | 3 damage, 25 m range, 1 action to fire |
| Portable heavy gun | 4 damage, 25 m range, 60% base hit chance, 1 AP; valid body/mount/brace support and hand fit required |
| Mounted gun | 4 damage, 40 m range, 1 action to fire |
| Melee | 3 damage, connected adjacent position, 1 action |
| Crusher claw | 5 damage, ignores 1 armour, 1 AP, up to 1.8 m physical reach and valid adjacency |
| Iron jaw | Basic melee profile for a supported/hanging attacker even with occupied hands; 1 AP |
| Wrecking ball | 8 nominal damage, 1 operator AP, once per round, Stopped/Slow; full draft sweep rules in file 08 |
| Aim | 1 action; +15 percentage points to the next eligible shot this activation |
| Truck frame / engine / wheel / mount | 24 / 8 / 4 per wheel / 6 health |
| Bike frame / engine / wheel | 10 / 4 / 3 per wheel |
| Cargo | Truck transport pool 8; passenger sidecar pool 2; engine uses 4 |
| Passenger load | Nib 1; regular Krag 2; clan boss 3, with fit checked separately |
| Special fitting capacity | Wrecking rig: 0 cargo/passenger load; missile rig: 2 transport load; both cap speed at Fast |
| Field repair | 1 action and 1 carried repair charge; restores 3 engine/mount health, once per component per round; cannot restore a destroyed frame or missing wheel |
| Jetpack | 2 charges, 10 m horizontal reach, 5 m rise/descent, 1 jump per activation |

| Chassis | Stopped travel | Slow travel | Fast travel | Flat-out travel |
| --- | --- | --- | --- | --- |
| Truck | 0 m | 0–10 m | 8–20 m | 18–30 m |
| Bike with sidecar | 0 m | 0–14 m | 12–30 m | 25–42 m |

Band changes, turning radii, hit checks and interruption details are defined in [06-poc-technical-foundation.md](06-poc-technical-foundation.md). The broad ranges in the terrain document describe intended scale; this table is the executable starting tune when values differ.

## 7. Critical verification scenarios

| ID | Scenario | Required result |
| --- | --- | --- |
| A01 | Inspect, preview and cancel repeatedly | No action, fuel, turn or RNG changes |
| A02 | Move driver, then swap into a second driver | Chassis cannot move twice that round |
| A03 | Passenger boards after spending an action | Remaining budget carries over; no new activation this round |
| A04 | Character dismounts and remounts another rig | No reset of budget, reaction allowance or activation-used state |
| G01 | Sidecar goes through a solo-bike-width gap | Invalid path based on full assembled footprint |
| G02 | High-speed path clips a corner | Rejected or a specifically planned collision; no tunnelling |
| G03 | Reaction destroys a wheel mid-route | Remainder is revalidated and cannot use obsolete handling |
| J01 | Jetpack destination is clear but trajectory hits a roof | Jump rejected before spending resources |
| J02 | Jetpack is interrupted above ground | One fuel/action spend; valid forced landing or defined fall |
| J03 | Equipped implant improves risky boarding | Modifier shown; no benefit beyond cap or extra action |
| W01 | Crusher strike after a boarding jump | Only remaining AP can be spent; no strike through closed armour or inaccessible node |
| W02 | Iron-jaw user attacks while gripping a rail | Legal supported position and adjacent exposed target required; 1 AP consumed |
| W03 | Ball endpoint clear, friendly Nib inside the sweep | Preview warns about the Nib; whole-path contact resolves, not only the endpoint |
| W04 | Wrecker is captured and offered the engine | Loading rejected because its crane occupies the cargo pool |
| W05 | Later salvo overlaps several colliders on one truck | Per-missile component-hit limit prevents multiplying damage; ammunition spent once |
| K01 | Apply a pain-only debuff and a broken-arm effect to a Krag | Pain penalty rejected; actual loss of grip/arm function remains |
| K02 | Apply fear/terror then issue a voluntary retreat | Forced panic/rout rejected; player's legal retreat still works |
| K03 | Ordinary 3-damage physical hit on unarmoured Krag, no graze | Natural armour reduces damage to 2; low pain does not refund health |
| K04 | Boss uses a narrow doorway, low cover or standard sidecar | Actual larger geometry/load is used; valid alternative route remains |
| K05 | Krag and Nib try the portable heavy gun | Krag body support or a proper mount/Brace supplies support; required hands and fit still checked |
| K06 | Save/reload the clan boss after damage | Species, boss body, traits, armour, health, equipment and unchanged action budget persist |
| R01 | Complete Rusthook, reopen and reload debrief | Eligible Brok earns exactly 4 XP once; one first-threshold perk point |
| R02 | Start leg treatment, advance 1 then 2 days | Blocked from deployment after day 1; ready after day 3; actual campaign dates preserved |
| R03 | Apply leg wound and select Sure Grip | Perk does not remove wound; previews include both; completed replacement clears only linked debuffs |
| R04 | Try heavy claw or a third lightweight implant, even restorative, on Nib | Species/strain validation rejects without consuming resources |
| R05 | Save/reload during recovery | Same treatment end day, availability, committed item, strain, XP/perks and wound history |
| R06 | Reward mechanic, injured survivor and absent crew | Useful non-kill contribution counts; recovered wounded participant qualifies; benched crew gets no mission XP |
| R07 | Elective piston leg fitted to healthy Krag | Part/strain/time consumed once; Power Step after completion; no fake wound or XP |
| R08 | Stable downed ally waits ten combat rounds | No bleed-out or repeated fatal roll; still requires physical recovery |
| E01 | Carrier extracts before an on-foot friendly | Objective secured; battle continues until that friendly exits or is explicitly left |
| E02 | Carrier destroyed; survivors collect portable scrap | Valid foot exit and longer travel; no automatic intact-engine recovery |
| E03 | Leave living Brok in enemy-held territory | Captured state and usable rescue opportunity; identity/perks/implants persist |
| E04 | Daily event occurs during a three-day advance | Clock stops for choice and resumes at the correct phase without duplicate rewards |
| E05 | Rescue when main deployed crew are all captured | Fort reserves or the authored emergency detachment can start it |
| T01 | Tin Can attempts boarding, then pilot dismounts | Machine command rejected; pilot may perform legal character boarding with remaining AP |
| T02 | Reload after focused carbine pulse | Same charge count and AP; no free recharge |
| C01 | Engine loaded into a half-full hold | Capacity and fit checked, cargo counted once |
| C02 | Controlled enemy truck still has a hostile occupant | Contested state remains; hostile crew are not converted |
| M01 | Friendly carrier destroyed | Mission offers legal alternatives or reports failed primary goal |
| S01 | Save/reload after equipment, wound and cargo change | Identical state, actions, resources and next seeded outcome |
| U01 | Use UI without distinguishing red from green | Selection, risk, allegiance and blocked actions remain readable |

These are design acceptance scenarios, not a requirement to build a large test framework before the first interaction. Automate the action/resource invariants and state round-trip; playtest route readability and player comprehension in the actual scene.

Pain/fear cases can use a small debug status fixture. They do not require adding a full morale system, terror enemy or extra combat encounter to the POC.

The authored wound fixture and P6a recovery flow are specified in [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md), with a worked narrative in [09-rusthook-narrated-playthrough.md](09-rusthook-narrated-playthrough.md). The story is not an instruction to force Brok's injury on every mission.

## 8. Performance and playtest observations

Record the actual browser, hardware, viewport, scene count and build for every performance result. Initial desktop target: smooth 60 fps camera motion at 1080p with this tiny roster, and local preview updates usually within 100 ms. These are targets, not measured achievements or guarantees for all devices.

Measure preview time, frame time during damage and boarding, time per activation, invalid-command attempts, unused infantry turns, and how often players use each route. Compare the encounter with and without jetpacks and with different starting crew placements.

Do not collect network telemetry for the POC. A local debug log or exported playtest record is enough.

## 9. Open decisions and provisional answers

| Topic | POC default | Revisit when |
| --- | --- | --- |
| Technology | Browser-first TypeScript/Babylon.js proposal | First asset and input/performance spike |
| Initiative | Alternate ready groups; player starts; no passes | Unequal group counts cause clear initiative abuse |
| Actions | 2 per character; 1 chassis move | Crew size or action chains dominate turn length |
| Jetpacks | Short burst with limited charges | Terrain tests show excessive or negligible value |
| Bionics | Crusher strike and jaw bite plus bounded optional passives | Signature actions are mandatory picks or erase species differences |
| Wacky vehicle weapons | Wrecking-ball opponent in first playable; missile fixture next | Extra machinery obscures the core decisions or dominates every route |
| Damage | Component states and mesh swaps | Core combat is stable enough to justify deformation |
| Fatality / rescue | Rare saved fatal result; stable downed recovery; rescue lead on capture | Mortality and rescue cadence can be measured across connected missions |
| Controller/mobile | Action architecture prepared; desktop UI only | Desktop encounter proves worth expanding |

The production engine, full campaign structure, title/lore approval, character slot catalogue, economy, exact roster and fort rules remain open. A POC should provide evidence for them, not silently settle all of them.
