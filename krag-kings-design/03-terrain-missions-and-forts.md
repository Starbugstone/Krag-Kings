# Terrain, missions and fort battles

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Accepted direction:** design open vehicle space, dense infantry space and mixed transition areas together. Terrain must support both vehicle and on-foot play. Dimensions, routes and surface effects below are draft proposals or prototype values.

## 1. The three battlefield spaces

| Space | Typical terrain | Tactical purpose |
| --- | --- | --- |
| Vehicle | Wide roads, desert flats, dry riverbeds, large yards | Speed, overtaking, ranged support and ramming |
| Infantry | Ruins, interiors, trenches, narrow passages, gantries | Cover, short routes, sabotage and local control |
| Mixed | Loading yards, road edges, broken settlements, depot approaches | Boarding, dismounts, objectives and combined support |

Do not try to make every location equally good for every unit. Also avoid separating the infantry and vehicle areas so completely that their fights never interact. A roof overlooking a vehicle yard, a covered approach to a loading dock and a lane beside a boarding gantry create useful overlap.

A Nib-sized service passage may be a useful occasional shortcut. It should not become a universal hidden path network or make a Nib mandatory for every objective.

## 2. Routes before raw size

Give each map a readable main route, an alternative vehicle route, covered infantry connections and at least one contested meeting space. A bike/light route or hazardous shortcut can add variety if its physical dimensions justify access.

Assess routes by actual vehicle footprint, turning radius, sidecar width, headroom and slope. Avoid invisible class barriers such as an apparently wide road that refuses a heavy rig solely because it is tagged Light Only.

Do the same for the clan boss's larger body. Clearance, cover and landing tests use his real capsule, not the normal Krag's. A low wall may leave more of him exposed, and a small doorway may require an alternate route. The depot must still provide a useful ground route and objective access for him; do not turn being the boss into permanent exclusion from the infantry game. Fearlessness changes his response to threats, not the physical width of a passage.

Keep room to turn, disengage and overtake. A main road that fits a truck's width but cannot accommodate its corners is not a usable vehicle route. Test spawn and exit geometry with the largest POC vehicle in both directions.

### Initial scale targets

The earlier discussion suggested maps around 120 × 120 m to 160 × 120 m. Use the smaller end for the first integrated encounter, with a compact 40 × 40 m test pad during initial implementation.

| Unit | Starting travel target per activation |
| --- | --- |
| Foot character | Ordinary move about 8–12 m; sprint about 15–18 m |
| Bike | About 25–45 m, depending on speed |
| Buggy | About 20–40 m |
| Heavy truck | About 15–30 m |

These broad ranges are design hypotheses, not exact movement formulas. The POC document chooses a small explicit tuning table for implementation. Infantry should cross a local position in a turn; vehicles should cross a sector. Objective approaches must be measured in turns for both.

## 3. Surface and obstacle definitions

Separate what a surface does to traction from whether an object blocks movement or sight.

| Surface proposal | Primary vehicle consequence | Design use |
| --- | --- | --- |
| Packed ground/road | Predictable steering and braking | Baseline routes |
| Loose sand | Reduced acceleration; mass matters | Build and route trade-offs |
| Glass flat | Easy travel but poor braking | Commitment and overshoot risk |
| Rubble | Slower travel; exposed running gear may be threatened | Dangerous shortcuts and cover edges |
| Mud | Reduced handling and possible bogging | Later variation requiring clear recovery options |
| Rock faces | Physical obstruction except usable passages | Route boundaries and height |

Only packed ground and rubble are required for the first POC. Broader surfaces should be data variations once baseline movement works.

Each terrain object separately declares movement collision, line-of-sight occlusion, cover geometry, traversable top, destruction state and any hazard. These properties must agree with its visible silhouette.

## 4. Cover and destruction

**Infantry cover** protects a character at their current position and stance. **Vehicle-scale cover** is large enough to interrupt substantial weapon lines or block a rig's route. These are readable scales, not a substitute for testing the actual attack ray and collider.

| Obstacle category | Examples | Initial rule |
| --- | --- | --- |
| Soft | Fences, light scrap screens, stalls | Blocks a character/shot where geometry applies; a capable ram may destroy it |
| Hard | Large wrecks, concrete barriers, industrial columns | Stops normal rigs; only designated destruction rules can change it |
| Permanent | Main cliffs and structural map boundaries | Stable route boundary for the encounter |

A soft screen can offer real infantry protection and still fail under a heavy ram. The ram preview must show the breach and expected consequence. A wooden fence should not look equivalent to a concrete support.

The POC needs one breachable barrier with intact and destroyed states. Entire collapsing buildings, deformable ground and structural simulation are unnecessary.

The wrecking-ball rig makes the barrier a useful test of a large melee sweep. Give the rig enough space to turn and operate without making the whole yard its attack zone. Stairs, dense cover and approach angles let characters outplay the mount. The later missile fixture needs physical blast blockers and separated cover positions, so a single salvo does not erase every infantry option. Use the actual damage/exposure rules from [08-outrageous-machinery-and-weapons.md](08-outrageous-machinery-and-weapons.md), including friendlies and mission cargo.

## 5. Wrecks reshape the map

Disabled vehicles remain physical objects. They can provide cover, obstruct a lane, carry usable equipment or become burning hazards. Their visual and collision state must update together.

At least one alternative route or recovery option should keep a destroyed truck from permanently trapping the player in the demonstration mission. If a critical path becomes blocked, the mission logic must recognise recoverable, failed and optional goals rather than remaining unwinnable without feedback.

Future systems such as pushing, towing and clearing wrecks can expand this. Until implemented, validate that the POC layout remains completable after expected wreck placements.

## 6. Verticality and jetpack access

Use a restrained number of meaningful height levels: ground, a useful raised level, and occasional higher landmarks. Roofs, loading ramps, gantries and bridge edges should provide sightlines, refuge from ramming and boarding approaches.

Every intended landing surface needs enough area for the character's collision footprint, headroom, a stable support and a defined exit route. Pipes, sloped scrap heaps and decorative tank caps are not automatically legal landing pads.

Jetpacks create approach choices, not automatic objective ownership. Limit flight by fuel and clearance, expose the trajectory to reactions, and put useful ground routes beside the airborne alternative. A roof can be reached quickly by a jump or slowly by a covered stair approach, with different exposure.

Do not cover every attractive roof with anti-jetpack hazards merely to undo the feature. Instead vary open, covered and enclosed destinations. A roof should be useful enough to justify fuel but not allow an untouchable shooter to solve the entire battle.

Bridge-to-truck and jetpack-to-truck boarding both use the existing vehicle nodes. The truck does not need a separate aerial boarding system.

## 7. Infantry and vehicle counterplay

Infantry threaten rigs through exposed crew, boarding, reachable components, sabotage, mines, grenades and emplaced weapons. Only boarding, a basic component attack and a repair/sabotage interaction are needed in the POC; the rest form later options.

Avoid balancing by making every rifle penetrate every armoured plate. Nearby dense terrain should create approach and angle advantages. Open ground should remain dangerous, with readable evasion space and cover.

Vehicles answer infantry with repositioning, suppressive or direct fire, ramming where space permits, dismounting their own crew and clearing soft cover. No single upgrade should remove all these positional concerns.

## 8. Missions that make both scales matter

| Mission family | Vehicle task | Character task | Extraction concern |
| --- | --- | --- | --- |
| Salvage recovery | Carry the heavy prize and protect approach | Secure, release or load the item | Leave with cargo and a working carrier |
| Fuel depot | Contest the yard and protect withdrawal | Operate the control room or pumps | Avoid being trapped after loading |
| Capture a rig | Intercept or disable the target | Board, clear and operate it | Find a driver or recovery solution |
| Convoy raid | Catch, block and escort | Raid cargo or reach controls | Retain enough transport to escape |
| Fort assault | Approach, breach and support | Clear structures and operate local objectives | Recover survivors and optional loot |

Not every mission needs every mechanic. The campaign should vary emphasis while preserving useful participation from both unit scales. Winning is based on the stated objective; it is not automatically tied to killing all enemies.

## 9. POC map: Rusthook depot

Use a hand-authored 120 × 120 m encounter. A wide vehicle loop connects the friendly approach in the southwest, the loading yard in the centre/east and an extraction road in the southeast. A secondary lane bypasses the main yard. Dense ruins along the north edge connect the approach to the depot controls.

Place a roughly 4 m-high gantry beside the main lane, with stairs on the infantry side and a clear jetpack landing area. It overlooks a boarding opportunity but not every objective and spawn. Include a low covered alternative for characters without a pack.

The primary mission is to release and recover an engine from the depot. A character must reach the control point and spend an action to release its loading cradle. An adjacent character then secures/loads it into a stopped compatible truck, consuming its declared cargo space. Extract that truck with the engine to secure the primary objective, then account for remaining crew before final extraction. Capturing the enemy vehicle is an optional opportunity.

Use explicit setup rules: no immediate spawn-line shot, no unavoidable opening ram, and enough time for a mixed approach before the enemy can reach the friendly spawn. Exact placement belongs in a scene asset; broad directions here are layout guidance, not pixel-perfect coordinates.

The demonstration should produce several choices: stay mounted for protection, dismount through ruins, jump to the gantry, disable an enemy wheel, or deliver a boarder by sidecar. It should also allow retreat with surviving crew even if the engine is lost.

For the revised first encounter, the enemy truck is the wrecking-ball variant. Its whole bed is dedicated to the crane, so capturing it does not solve engine extraction. The friendly standard truck remains the required carrier unless a separately authored variant adds another compatible vehicle. The missile setup is a follow-on fixture; always retain at least one usable cargo-capable truck when that fixture uses the engine objective.

### Recovery and fallback routes

Each fixture needs a foot exit and a body-width recovery path suitable for a rescuer and trailing casualty. A lost carrier changes cargo/reward possibilities, not whether mobile survivors can leave. Provide accessible loose scrap and the engine-dismantling interaction for a partial-salvage result. A rescue variant can reuse this terrain with holding points, released captives and a foot extraction route. Tin Can acquisition needs a real vehicle exit; the machine cannot use boarding to bypass a blocked lane. Campaign-day event and journey rules live in file 11.

## 10. Fort layout and raids — later scope

The proposed fort becomes its own battle map during a raid. Construction therefore needs path validation for entry, internal vehicle travel and loading/escape space. A gate may close, but it needs a defined breach interaction; ordinary building placement cannot create an impossible, indestructible maze.

Check minimum width, corners, headroom and reachable yards using actual permitted vehicle footprints. A built fort must preserve a valid route or explicitly authored breach route for the encounter types it can receive. Players can influence firing lanes, cover and chokepoints without exploiting broken AI pathfinding.

Damaged structures and wrecks persist until repaired or cleared in the campaign proposal. Raids, a construction editor and procedural fort validation are outside the basic POC.

### Fort recovery and roster availability

The compact POC fort screen now needs a Sawbones treatment place and an explicit campaign-day control. In the full 3D fort, the same state can show Brok recovering and testing his replacement leg. Treatment blocks expedition deployment; room placement or moving a portrait cannot waive it. Waiting and travel advance the same day-by-day event clock, with interruptions for choices, arrivals and treatment completion. Walking home with salvage takes longer and exposes the journey to more eligible daily events. Patients do not appear in a battle when recovery completes elsewhere. Rules for attacks on the fort during treatment remain later work; the POC does not invent hospital casualties or compulsory defence. See [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md).

## 11. Map review criteria

Before adding art, drive every route with the truck, bike and fitted sidecar. Walk the infantry routes, occupy the roof, test the landing footprint and drop a wreck in the busiest lane. Confirm that the objective remains readable and the scenario resolves correctly when a carrier is disabled.

Look for a roof that dominates every lane, compulsory open-ground infantry travel, narrow corners the player cannot predict, objective interactions vehicles can trivially bypass, and jetpack routes that bypass the complete mission. Fix layout problems before tuning damage numbers around them.
