# POC technical foundation

Draft 0.5 · 4 October 2026 · [POC scope and backlog](05-poc-scope-and-backlog.md)

**Production update — 5 October 2026:** the browser/Babylon stack below is a historical proposal. The user selected a downloadable Windows POC and an Unreal-versus-Unity comparison before engine choice. Use [15 — current integration plan](15-poc-realisation-plan.md) for production. Preserve the useful state/command contracts below; do not run this old scaffold or assume its coordinate/export/browser-storage choices are now approved.

**Status:** proposed implementation contract for the first test build. These choices make development concrete without committing the final game to a platform or engine. Code shapes and commands below are starting specifications, not an implemented or tested repository.

## 1. Recommended starting stack

**Draft recommendation:** browser-first TypeScript with Babylon.js, Vite and a small HTML/CSS HUD. This follows the stated web preference and keeps the POC accessible through a local browser. The original Unity recommendation remains an alternative for production; decide again after the first camera, model-import and movement spike.

Babylon.js provides a JavaScript rendering/game engine with typed npm packages. Vite provides a development server and build workflow with TypeScript templates. Those are current tooling facts; choosing them for this POC is a design recommendation, not a measured conclusion that they outperform Unity. See the official references at the end.

Use a WebGL rendering baseline for the POC. Treat WebGPU as a later rendering option. Use a supported Node version satisfying the chosen Vite release's current requirements, pin resolved package versions in a lockfile and record them in the repository README. Do not assume the user's older Node 20 installation already meets those requirements.

Suggested scaffolding sequence for a new repository:

```bash
npm create vite@latest krag-kings-poc -- --template vanilla-ts
cd krag-kings-poc
npm install
npm install @babylonjs/core @babylonjs/loaders
npm run dev
```

These commands have not been run as part of the document/art deliverable. Check the installed package documentation before writing loader imports. Use local project dependencies and assets rather than depending on an unpinned public script at runtime. No backend, account system, hosted deployment or external AI API is required.

## 2. Architecture and ownership

| Area | Owns | Must not own |
| --- | --- | --- |
| `src/domain/` | Serializable entities, state, identifiers and invariants | Engine mesh references or DOM elements |
| `src/rules/` | Command validation, previews, resolution, costs and seeded outcomes | Camera animation or input events |
| `src/navigation/` | Foot graph, vehicle path geometry, clearance and landing queries | Spending actions or changing allegiance |
| `src/content/` | Chassis, equipment, tuning and encounter definitions | Per-frame mutations |
| `src/ai/` | Candidate generation and utility scoring | Privileged commands or hidden-state access |
| `src/presentation/` | Babylon scene, model binding, animation, camera and effects | Authoritative damage or movement outcomes |
| `src/ui/` | Selection, contextual actions, previews and HUD | A second implementation of legality/cost rules |
| `src/persistence/` | Versioned snapshot validation and local import/export | Recreating state from rendered transforms |

These are suggested module directories, not an existing file tree. Keep a single authoritative `BattleState`. UI and AI submit the same commands. Presentation consumes resolved events and state; it never decides whether a wheel was hit because an animation happened to intersect it.

Use procedural boxes/capsules first. Bind imported meshes to stable entity IDs later. A model swap should not change AP, health, allegiance or cargo capacity.

For special machinery, add data-driven ability profiles with operator requirements, mount/socket, AP/ammo cost, per-round use, legal speed bands, footprint/sweep/blast geometry and exposure rules. The crane and missile rack are alternate hardpoint fittings, not new entity hierarchies. Resolve fitting-dependent capacity from the loadout definition; do not repeatedly subtract it whenever a save is loaded.

## 3. Minimum data model

| Record | Essential fields |
| --- | --- |
| Battle | Schema/content version, revision, round, active side/group, phase, RNG state, mission state |
| Character | ID, faction, species, clan role, body-profile ID, trait IDs, stats, natural/worn armour, health/status, location, equipment, injuries, implants, cumulative XP, awarded threshold IDs, perk points/IDs, deployment status, remaining AP, activation-used round, reaction-used round |
| Campaign | ID, integer day/phase, roster, inventory, treatment-place occupancy, processed encounter/time-event IDs, reward ledger, campaign RNG, pending event/choices/cooldowns, rescue leads and journey records |
| Casualty / captive | Character ID, encounter first-downing ID/result, stable/dead/captured/missing state, captor/site, recovery attachment, stash references and release state |
| Journey | Party IDs, route/leg, travel mode, elapsed/remaining work, payload/burden, destination, day-event IDs and detour-applied flag |
| Campaign event | Definition/instance IDs, eligibility, location, rolled choice/reward data, availability/cooldown, resolution state and pending time cursor |
| Injury | Stable event/record ID, anatomy socket, structural cause, modifier definition, active/restored function state, linked replacement and history |
| Treatment | ID, patient, wound/socket, committed part, place, start day, fitting-end day, ready day, phase and completion-applied flag |
| Implant definition/instance | Species and body fit, socket, light/heavy class, strain, restored functions, equipment effects, condition and installation state |
| Progression definition | Cumulative XP thresholds, perk costs/effects and capped contribution categories |
| Body profile | Capsule/target geometry, standing/seated clearance, hand requirements/support capabilities, passenger load and valid equipment/station fits |
| Status definition | Effect values plus cause tags such as pain, fear, structural injury, bleeding, physical stun or displacement |
| Vehicle | ID, owner faction, current controller, pose, speed band, component states, stations, nodes, transport pools, movement-used round |
| Character location | Exactly one of ground surface/pose, vehicle station, vehicle boarding node, recovery attachment, extracted/transit, fort/treatment or captive/missing site; casualty status is a separate field |
| Station | ID, local transform, accepted occupants/fit, protection, occupant ID, connection IDs |
| Boarding node | ID, local transform, capacity, protection, traversable connections and reachable systems |
| Component | ID, type, health, functional state, local hit volume, linked modifiers, visual state |
| Equipment | Definition ID, holder/socket, remaining charges, condition |
| Ability/mount state | Definition ID, operator/station, used-round marker, ammunition, stowed/operating state, permitted working sector |
| Cargo | ID, definition, load, fit/handling requirements, exactly one holder/location |
| Terrain | Collider, sight blocker, surface, traversal links, cover, landing support, destruction/hazard state |
| Mission | Console state, engine state/holder, extraction volume, objective result |

Enforce invariants when loading and after every resolved command: an occupant appears in one location, a station has at most its declared capacity, cargo has one holder, AP/fuel are nonnegative, and a character cannot be both extracted and occupying a seat.

Vehicle faction, driver control and occupant factions are distinct fields. Capture is a state transition, not a recursive faction overwrite.

Likewise, the clan boss is a Krag with a boss body/role template, not a different species or a temporary scale buff. Keep leadership role distinct from driver/gunner station assignment. Initialise the chosen body's stats once, then persist them with current health; loading a save must not repeatedly add boss health, natural armour or size multipliers.

### Example command shape

```ts
type CommandEnvelope = {
  actorId: string;
  expectedRevision: number;
  command:
    | { type: 'moveVehicle'; vehicleId: string; route: Route; speed: SpeedBand }
    | { type: 'moveFoot'; destination: SurfacePoint }
    | { type: 'board'; vehicleId: string; nodeId: string; useJetpack: boolean }
    | { type: 'fire'; targetId: string; componentId?: string }
    | { type: 'interact'; targetId: string; interactionId: string }
    | { type: 'endActivation' };
};
```

`Route`, `SpeedBand` and `SurfacePoint` are domain types to implement; this is an interface sketch. Add mount, transfer, aim, reaction reservation, repair and cargo commands explicitly rather than letting a generic interaction bypass their rules. Add named ability commands for crusher strike, jaw bite, wrecking swing and, at P8, missile salvo. Each carries its ability ID and target/sector; costs and legal geometry come from the rules layer.

## 4. Preview, commitment and resolution

`preview(state, command)` is a pure query. It returns legal/blocked status, reason codes, costs, path/target geometry, known reaction crossings, chances, possible results and the state's revision. It does not spend resources or advance the RNG.

On commit, reject stale revisions and revalidate the command. If legal, apply costs exactly once and resolve an ordered event sequence. Increment the revision for authoritative changes. The UI updates from events such as MovementAdvanced, ShotResolved, ComponentDisabled, CharacterTransferred, FuelSpent and ObjectiveChanged.

A moving action resolves in deterministic segments/event points. At each reaction or collision, update actual state and revalidate the remainder. The complete animation need not finish before the logical outcome is computed, but no other player command is accepted until the presentation reaches a stable decision point.

Use one seeded pseudorandom generator for authoritative outcomes and store its current state/counter. Resolve candidates in stable ID order when ties matter. Cosmetic particles use a separate generator. Hovering, camera motion and frame rate cannot consume combat randomness.

Initial tactical flow: Loadout → Round start → Choose group → Plan → Resolve → Plan or End group → Other side → Round end → next round. Objective secured is a flag, not immediate debrief. Final extraction/explicit abandonment diverts a stable point to Debrief → Return journey → Fort. Daily events may interrupt travel/rest. Entering Resolve disables duplicate commits.

## 5. Round and group implementation

At round start, refresh each living eligible character's two AP and reaction allowance, clear current-round activation state, and rebuild groups from actual locations. Start with player-first alternating choice and no passes. If a side has no ready groups, the other completes its remaining groups.

Starting a vehicle group marks its eligible occupants activated. Subsequent transfers preserve that marker and AP. Let departing characters finish their remaining actions in the same activation continuation, then expire unused AP. Do not add them to the ready list until the next round.

Vehicle movement-used state is independent of occupant state. Driver takeover can enable an unmoved captured rig, but never refresh an already-used move. An undriven rig has one passive slot; a driver lost after moving does not create a second slot that round.

For the POC, an undriven rig coasts straight by the minimum travel of its current band at its next slot, then drops one band. Collision truncates that movement. A Slow rig has a zero minimum and drops to Stopped. Remaining travel after driver loss during an active move is resolved first and counts as that round's movement. This is deliberately simple kinematic behaviour. The same previewed passive coast/brake occurs when a driven moving rig ends its group without using movement. It consumes the shared movement allowance, grants no new AP and cannot run after a completed move. End-group previews must show this consequence.

## 6. Spatial contract and navigation

Use metres. Define a project scene convention of Y-up, +Z forward/north and +X right/east; convert imported art once at its root. Heading, node transforms and collider poses all use the same convention. Export/import software settings must be verified with a visible axis/test asset rather than assumed.

### Foot movement

Use a hand-authored walk graph or small layered navigation grid. Nodes carry surface IDs and height, so ground under a gantry is distinct from its deck. Stairs, ladders and vehicle connections are explicit links with cost and clearance. Dynamic vehicles/wrecks invalidate intersecting foot links. Recheck path occupancy at commitment.

### Vehicle movement

Start with an analytical forward arc followed by an optional straight segment. The player drags reachable endpoints/curvature; an unreachable cursor position remains visibly outside the envelope. General obstacle-avoiding vehicle path search is not necessary for P1.

| Minimum turn radius | Slow | Fast | Flat-out |
| --- | ---: | ---: | ---: |
| Truck | 5 m | 10 m | 18 m |
| Bike with sidecar | 3 m | 6 m | 11 m |

Use the travel table in the POC scope file. One band change accompanies a normal move. Emergency brake costs the driver's second action, permits up to two downward band changes and must still validate a stopping path; it is not instant braking through a wall. For the first build, a stopped vehicle may reverse up to 3 m as its one movement action, with no pivot on the spot.

Represent the chassis and attachments with a few oriented boxes. Validate the swept volume along the route, including rotational sweep. Sample the visual route at no more than about 0.25 m/2 degrees between poses, then use conservative swept collision checks between poses; endpoint checks alone can miss thin barriers.

Packed ground is baseline. Rubble halves allowed local travel speed/distance progress and caps the band at Slow in the POC; integrate the path through that region rather than charging the whole route the same cost. Steering damage increases minimum radius by 50%; one disabled wheel reduces maximum travel by 40%; two disabled wheels prevent powered movement. All are provisional data modifiers.

### Jetpack

Construct a ballistic-looking arc between launch and destination; it is a designed trajectory, not a full thrust simulation. Check the swept character capsule, clearance and supported landing footprint. Retain validated fallback positions along the approach for interruptions. Validate vehicle-node endpoints in world space using the target's current resolved pose.

## 7. Minimal combat calculations

Use each weapon's base hit chance: initially 75% for the basic rifle/mounted gun and 60% for the portable heavy gun. Subtract 20 percentage points for applicable cover, 10 for a Fast target or 15 for Flat-out; add 15 for an Aim token. An equipped optical implant adds 10 only to an aimed shot. Clamp legal shots to 5–95%. Blocked line of sight or out-of-range targets are invalid, not 5% miracle shots.

A hit against an exposed character then checks graze: initially 10% for a Krag and 25% for a Nib. A graze halves damage, rounded up. Do not graze component hits. Keep the damage, probabilities and modifiers in content data.

Aim tokens expire on the next shot, on a position/station change, or at activation end. The optical implant stacks with the Aim bonus before the final cap. Basic melee starts at 75% hit, with +10 points for a Krag or -10 for a Nib, capped at 5–95%; it requires an adjacent ground position or a connected occupied vehicle node. Connected nodes permit attacking across their boundary, not sharing the same occupied station. The Nib ranged-graze rule does not also apply to melee.

Use simple armour subtraction: truck frame armour 3; exposed wheel/engine/mount armour 0. Krags, including the boss, have natural armour 1 against direct ballistic/melee hits, physical blast damage and wrecking/ram/crash contact; Nibs have natural armour 0. Worn character armour defaults to 0 and is tracked separately. Natural skin protection does not reduce fall damage or a future fire/toxin hazard unless that damage definition explicitly grants it. The POC has no ongoing bleeding-damage or bleed-out status.

For damage that can graze, first halve raw damage on a graze and round up. Then calculate eligible natural plus worn armour, subtract the attack's armour penetration with a minimum of zero, and subtract that effective armour from damage, again with a minimum of zero. Area blast, falling and component hits do not use the character ranged-graze check. Thus an ordinary un-grazed 3-damage physical bullet deals 2 to a Krag with no worn armour. Pain tolerance changes effect eligibility, not this health subtraction. A basic rifle still threatens exposed systems and crew much more than the truck's main frame.

Ordinary rifles/mounted guns use abstract ammunition initially; no magazine/reload rule is implied. Explicit charge weapons keep their own costs. A failed ordinary hit roll causes no secondary damage. Reject direct fire at friendlies and rays physically blocked by a friendly body; area/sweep attacks retain their explicit friendly-fire rules. Shot animations cannot create extra contacts. The advanced energy profile in file 12 explicitly uses armour/penetration and charge rules rather than a hidden exception.

### Krag traits, gun support and boss geometry

The Krag trait filter rejects pain-only aim/AP/movement penalties and fear/terror-induced panic, routing or action loss. It does not reject structural impairment, blood loss, unconsciousness, physical stun or displacement. Where an attack proposes several effects, validate each cause separately; never discard its entire damage event because one pain/fear effect was rejected.

The portable heavy-gun profile has 4 damage, 25 m range and a 1 AP firing cost. Validate support before accepting fire: an eligible Krag body in a secure position, a proper mount, or a currently valid Brace effect can supply it. Brace costs 1 AP and ends on movement/station transfer; required hands, station clearance and weapon compatibility are still checked. Do not grant a hidden accuracy bonus for loving big guns: the meaningful advantage is support/handling, with visible weapon trade-offs.

The first boss body target is 2.75 m standing height versus 2.2 m for a regular Krag. Author colliders, seated headroom, attack target points and footprint from the approved greybox, then use the same profile for path clearance, cover and landing validation. Passenger load is 3 versus 2; a standard capacity-2 sidecar rejects the boss. A dedicated boss-compatible operating station uses its declared baseline crew accounting. Health is 14 versus 10 and AP remains 2.

Fear/pain fixture checks can inject tagged effects into the pure resolver. No full morale system or new enemy terror power is required to validate these traits in the first build.

Risky boarding starts at 70%; same-band, aligned movement adds 10 points; a one-band mismatch subtracts 15; a two-or-more-band mismatch subtracts 30. A gap beyond 2 m subtracts 10, a height difference beyond 1 m subtracts 10, and a grip implant adds 10. Apply declared geometry limits before a roll and cap risky checks at 5–95%. Ordinary unopposed climbs onto stopped accessible nodes are automatic. Jet-assisted approaches use their flight envelope, then the applicable boarding check.

For ordinary vehicle-to-vehicle boarding, start with a 3 m maximum gap and a 1.5 m maximum positive height difference. Hazardous failure drops the character at the last reachable ledge/ground below the failed endpoint, with fall/collision damage; it must not place them inside a collider. The preview shows that consequence. Ground evasion starts at 60% for a Krag and 75% for a Nib when aware and a legal escape point exists, using the character's one reaction allowance.

Basic rams stop both involved POC rigs at resolved contact. Use 3/6/10 nominal damage at Slow/Fast/Flat-out, multiplied by a simple mass ratio clamped to 0.5–2; attacker suffers half nominal damage before armour. Limit this to chassis contact and the designated breachable barrier. Add angular scaling, side impacts and secondary occupant checks only after the interaction is readable.

Fall damage initially equals 2 per whole metre beyond a safe 1 m drop; zero or negative values mean no damage. Ordinary jetpack-assisted arrival avoids fall damage when completed successfully. These formulas are a coherent first test tune, not realistic physics or final balance.

Reserve overwatch by spending one AP during activation. It lasts until the round ends or it fires, consumes the character's shared reaction allowance, and uses the normal shot resolver. Unused reservations expire without refund. A character who already evaded cannot also take that reserved shot this round.

For the remaining POC interactions, mount/dismount, one station/node transfer, console use, load/unload and simple sabotage each cost 1 AP. Sabotage requires an exposed reachable engine or mount access node and a repair tool; it deals 3 component damage automatically. Hijack costs 1 AP after reaching an uncontested empty driver station and gives control if controls function. It does not repair the engine or override the chassis movement-used flag. Loading requires the released engine, stopped carrier, adjacent character, sufficient capacity and the loading-cradle access point. These deliberately small rules can be expanded after the full loop works.

## 8. Special equipment and enemy AI

### Special machinery resolution

Use the equipment-specific rules in [08-outrageous-machinery-and-weapons.md](08-outrageous-machinery-and-weapons.md) as overrides to basic melee/gun profiles. A claw uses melee hit resolution but its own damage, reach and armour effect. A jaw checks supported position and occupied hands without granting free attacks. Save jaw sockets and per-ability use alongside other equipment.

For the wrecking ball, compute an authored pivot/ball trajectory and swept sphere contacts in stable time order. Validate deployment and recovery clearances before spending AP. Resolve the first contact once, including a possible character evasion; an evade ends that simple POC swing without retargeting it into another victim. Record the mount's used-round state. Animate the visible boom, chain and chassis from these events; animation overlap cannot cause repeated damage.

For the later missile salvo, sample each endpoint from a uniform-area scatter disk using the seeded RNG only on commit, then find actual projectile collision and blast exposure. Query target IDs, not just render mesh intersections. Apply the declared per-missile component/occupant limits and cover blocking in stable projectile order, spending the two-round ammunition cost once. Persist ammunition, fitting and used-round state through a save/reload. Preview queries use an uncertainty envelope and never consume or reveal those sampled endpoints.

### Basic enemy policy

Use a small utility scorer over legal candidate actions: protect the engine/console, fire at an exposed threat, reposition into useful range, contest a boarder, repair an essential component, or retreat from a doomed position. Do not build a general planner for the first encounter.

For enemy Krags, bias otherwise comparable choices towards productive attacks, boarding and heavy-weapon opportunities. Health loss does not trigger a fear/rout state. Withdrawal remains an objective-driven choice, such as preserving a captured prize or reaching a better firing position. Do not make fighting enthusiasm force player units to act or make enemies charge into known impossible geometry. The clan boss's death does not automatically panic other fearless Krags.

AI navigation considers its actual chassis footprint. It uses the same action budgets and validation as the player. It may inspect only its observation state, not player-hidden positions or unobserved implants.

The enemy wrecker values a useful working angle and clear swing/recovery path, and penalises hitting its own crew. If no swing is useful it can reposition, defend against a boarder or wait; it must not spin endlessly trying to attack through its own cab. The missile fixture later scores blast benefit against scarce ammunition and friendly exposure.

For P0–P3, keep all encounter units visible to reduce debugging variables. Add line-of-sight observation when reactions and the integrated mission are stable. The preview/AI APIs should still accept an observation view from the start so hidden-state support does not require rewriting all callers.

## 9. Persistence and debugging

Save a versioned JSON snapshot at stable planning/debrief points, including current group, AP, reactions, movement-used flags, occupants, cargo, wounds, implants, fuel, objective state and RNG. Saving mid-animation is unnecessary; offer it after resolution completes.

Keep an automatic local checkpoint plus explicit export/import. Validate imported versions, bounded numeric fields, known content IDs and all entity references. Reject an unsupported/corrupt save with a useful message rather than silently losing a crew member. No remote sync is needed.

The debug overlay should toggle colliders, node connections, navigation links, legal landing footprints, reaction arcs and seed/state revision. This separates visual faults from rule faults during development.

### Crew progression and recovery state

Implement the compact post-mission rules in [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md) inside the same pure domain layer. Add explicit ResolveDebrief, ChoosePerk, StartTreatment, AdvanceCampaignTime and ValidateDeployment commands. Battle AP/round progression and campaign-day progression are separate clocks.

ResolveDebrief consumes an encounter result and contribution flags once, awarding eligible survivors 1 participation + 2 primary-success + up to 1 contribution XP. Store the encounter ID with the applied result. Cross cumulative thresholds once and store awarded threshold IDs; ChoosePerk spends a point once and rejects duplicate ownership. Repeated commands, reloads and animations cannot mint XP or perk points.

StartTreatment validates the character is at the fort, socket/wound, species/body fit, resulting strain, item and free treatment place. Commit the item and reserve the place atomically, mark the patient unavailable, and set fittingEndDay = day + 1 and readyDay = day + 3. All installed/committed implants, including strain-1 servo parts, count towards the strain budget even while recovering or disabled. An elective treatment has an optional injury link, requires no existing wound and creates a modification-history entry rather than a fabricated injury. For a same-socket replacement, the validated final fit replaces the old item rather than counting two parts in one socket; removing other implants requires its own explicit treatment plan. AdvanceCampaignTime(deltaDays, eventId) accepts a positive integer request but processes one day at a time through the saved phase cursor: treatment/journey updates, scheduled events, eligible random event, interruption. Retain unprocessed requested days and stop on decisions/arrival/readiness. Complete restoration, enable the implant perk and release the treatment place once. Imported saves must retain these IDs and reject duplicate occupancy, over-budget fits and patients in deployed rosters.

Use one shared evaluator for UI and rules: identify restored functions and functional implant perks; combine learned and compatible equipment flat bonuses; apply unresolved structural multipliers; enforce restrictions/caps. Use the strongest leg-implant movement bonus, then learned Long Stride, before injury multipliers. Sure Grip changes risky checks only; Measured Shot requires Aim. Perk-granting servo/piston definitions are in file 10, and disabling the implant removes its equipment perk without deleting learned perks. Functional replacement completion removes only its linked impairment. If the implant later becomes disabled, re-evaluate that function without deleting wound history or refunding strain.

The leg-injury fixture emits one idempotent structural event. Normal zero-health handling uses one saved first-incapacitation outcome per encounter, with the rare fatal/stable-downing tune in file 11; repeated damage cannot reroll it. The connected starter can assign the one leg wound on a nonfatal downing. A broad hit-location/injury catalogue remains deferred. Initial scenario equipment is valid pre-authored state, not the campaign treatment bypass. Campaign snapshots retain inventory, treatment dates, availability, XP/perks, reward/time ledgers and wound-to-implant links. Mid-recovery reload is a required round-trip check.

The first fixture returns from a fresh campaign's initial mission at day 1, then can fit Brok until day 4. Explicit rest advances days immediately; no operating-system clock or background timer is used. Motorised and foot returns now supply authored journey work to the same daily event loop, without counting the same route leg at both departure and return. Larger world-map generation and raids remain deferred.

### Recovery, retreat, events and rescue

Use file 11 as the command contract. Add AttachRecoverySling, ReleaseCasualty, LoadCasualty, ClearIncapacitatedOccupant, CollectScrap, DropScrap, DismantleEngine, ExtractEntity, FinaliseExtraction and ReleaseCaptive. Recovery attachments preserve exactly one body location and validate both bodies' swept footprint. Downed/dead are different statuses; there is no bleed-out ticking system. FrameDestroyed emits its occupant crash/fall outcome once.

ExtractEntity transfers the actual vehicle/occupants/cargo or attached foot pair to extracted state. Primary objective success may be set, but FinaliseExtraction must still classify every remaining friendly. Leaving a living casualty in enemy control creates one captured record and guaranteed rescue lead; otherwise create a missing-site objective. Rescuing the same character transfers their persistent entity, never a fresh clone. Released captives receive no new AP in that round. Check reserve/emergency roster viability before offering the rescue fixture.

A destroyed carrier does not disable foot extraction. Validate per-character portable load and whole-object fit; dismantling the engine atomically replaces it with four bundles and fails the intact-engine objective. Route mode determines return work, with burden applied once. Persist journey party/payload and unavailable-in-transit states. Future vehicle salvage markers do not invoke unimplemented towing.

Campaign event draws use a separate seeded stream. Save eligibility inputs, selected definition, choices, date, cooldowns, result IDs and the day-phase cursor. Previewing/rest cancellation consumes no roll. All daily effects and rewards are idempotent. The initial four events use authored data and no external service. Pending choices and recovery completions stop auto-advance.

Tin Cans are vehicle definitions with a pilot-fit rule and canBoardVehicles=false enforced in domain validation, not only the HUD. Their pilot remains a character with ordinary AP, wounds and implant strain. The wheeled fixture reuses navigation/stations/modules; the walking fitting stays unimplemented until its separate geometry/motion contract exists. File 12 supplies the advanced weapon proficiency, charge and attack profiles. Use the same save schema and deterministic resolution as other weapons.

## 10. First repository handoff

The first development change should contain the pinned project scaffold, README launch/build instructions, one encounter definition, pure domain types, seeded RNG, a camera/selection scene and the tiny test pad. The next change proves preview/commit plus movement before adding combat art.

Use focused automated checks for budget conservation, duplicate occupancy, stale-command rejection, preview not consuming RNG and save round-trip. Use actual scene playtests for camera clarity, movement envelopes, readable art and whether the depot fight is enjoyable.

## Official tooling references

Checked 4 October 2026. These support tooling facts only; the game architecture, balance and scope above are our design proposals.

- [Babylon.js official repository and installation guidance](https://github.com/BabylonJS/Babylon.js)
- [Babylon.js ES module package guidance](https://github.com/BabylonJS/Babylon.js/blob/master/readme-es6.md)
- [Vite getting started, templates and current runtime requirements](https://vite.dev/guide/)
