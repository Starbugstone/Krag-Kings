# Combat, vehicles and boarding

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Status:** Turn-based combat and visible vehicle damage are established. The combined vehicle/crew/infantry design is the accepted direction. The exact activation, action, momentum and damage rules below are draft proposals.

## 1. One battlefield, persistent entities

Vehicles, characters, detached components, cargo and wrecks exist on the same battlefield. A character keeps their identity, equipment, wounds and remaining actions when entering a station, dismounting or boarding an enemy.

A vehicle has a chassis, movement characteristics, components, crew stations, boarding positions, attachments and transport limits. It is not a single character with a vehicle skin. Losing its gunner affects the gun; losing its driver affects control; losing its engine does not automatically kill its passengers.

## 2. Turn structure and action ownership

### Proposed alternating activation

At the beginning of a round, identify each side's available activation groups. Sides alternate selecting a ready group until all have acted. Which side starts, and whether a side with fewer groups gets limited passes, remain open tuning questions.

| Situation | Activation group |
| --- | --- |
| Friendly vehicle with its own crew and passengers | Vehicle group, containing its friendly occupants |
| On-foot character | Individual character |
| Friendly character already aboard an enemy vehicle at round start | Independent boarder |
| Undriven moving vehicle | Passive vehicle slot, with no new crew actions |

The default prototype budget is **2 actions per character per round**. This is a test rule, not a final commitment. A vehicle group coordinates its occupants; it does not create a separate pool of free character actions. Driving spends the driver's actions, shooting a crewed mount spends the gunner's actions, and repair spends the mechanic's actions.

Routine movement, a basic attack, station transfer or short interaction initially costs one action. Sprinting, a complex hijack or heavier maintenance may cost the full budget. Tune costs through play rather than assuming two actions balance every ability.

### No extra turns from changing location

Action budget and activation-used state belong to the character for the whole round.

- Starting a group activation marks its eligible occupants as taking their activation.
- A boarder or dismounting passenger can immediately use their remaining actions as part of that activation's continuation.
- They cannot receive another independent activation in the same round.
- Their new independent group appears next round if they remain on foot or aboard an enemy rig.
- Someone who already acted and then joins another group gains no new actions.
- Unused actions expire when the activation ends unless explicitly reserved for a reaction.

For example, Brok starts with two actions aboard Scrapjaw. Jumping to Red Fang spends one. He may use the second to brace or attack a reachable occupant. He cannot then appear as a fresh two-action unit later in that round.

For the first prototype, a vehicle receives at most one normal movement action per round, regardless of driver swaps. Crew who capture a rig may act with their own remaining budget, but cannot reset the chassis's movement allowance. This prevents hijacking or seat cycling from producing repeated full moves.

### Selection is not commitment

Inspecting any character or vehicle never starts an activation. The first committed command activates its ready group. The UI must distinguish selection, preview and committed activation.

## 3. Movement, speed and momentum

### Speed bands

| Band | Intended behaviour |
| --- | --- |
| Stopped | No forward travel; safe loading and routine entry/exit |
| Slow | Short travel, tighter turns, useful positioning and safer boarding |
| Fast | Strong repositioning, broader turns and greater commitment |
| Flat-out | Long travel, widest turns, poor braking and high impact potential |

Changing speed changes the legal route, braking distance and risks immediately. The initial rule allows one normal band change as part of the movement action. Emergency braking is a separate, costly option with its outcome previewed. Exact acceleration, deceleration and reverse rules remain tuning work.

The player plots a curved route and end orientation inside the chassis's steering and travel limits. The route cannot cut corners through obstacles or teleport the vehicle's rear through terrain. Validate the whole vehicle footprint along it, including a fitted sidecar or protruding attachment.

At higher speed, legal end positions include a minimum forward commitment unless braking or a collision changes the outcome. A rig cannot remain in place while retaining all the benefits of being Flat-out. A stopped chassis may make a small positioning manoeuvre only if its steering model permits it.

### Discrete tactical time

Only the current action and its triggered reactions resolve. Other units do not secretly advance while the player plans. Speed represents the rig's motion state, which informs turning, impact and boarding; it is not a background simulation running between turns.

This is deliberately abstract. A displayed moving truck stays at its current resolved position until its next action. Animations, exhaust and wheel motion must not imply a different target position from the one used by the rules.

### Driver loss and uncontrolled rigs

If the driver is lost during a movement, resolve only the remaining travel of that move according to the visible uncontrolled path and collisions. Do not grant a second movement because the driver died.

If the vehicle remains undriven afterward, it gets one passive coast/brake resolution at its vehicle slot in later rounds. If its normal movement already resolved this round, no additional passive move occurs this round. Taking over the driver's station cancels the future passive behaviour only when the character can legally reach and operate it.

A derelict vehicle stays on the battlefield. A stopped, intact bike can be remounted; a destroyed bike cannot.

### Ending an activation without driving

A moving, driven rig cannot preserve its speed indefinitely by skipping movement. If its movement allowance is unused when its group ends, resolve one previewed passive straight coast/brake using the existing band minimum and then drop one speed band; Slow drops to Stopped without forward travel. Mark movement used even though this passive resolution grants no crew action. A rig already moved this round gets no second coast. Collisions and interruptions use the ordinary rules. Show this consequence before confirming End activation.

## 4. Shooting and reactions during movement

A vehicle route can carry action markers, such as firing a turret or attempting a board at a particular point. Each marker belongs to a named character and reserves that character's actions. A driver's movement does not grant free gunfire from every passenger.

The prototype should first support one move with one embedded crew action. Expand the planning sequence only after that interaction is readable.

At each relevant route point, evaluate actual position, weapon arc, line of sight, target state and exposure. Resolve a triggered reaction before the planned action at that point, then revalidate the remaining plan. If a wheel is destroyed or the path becomes blocked, stop or redirect according to the movement rules; never continue an invalid preview through scenery.

Costs already executed remain spent. A cancelled, unexecuted shot does not consume its action. Return to planning with the real position and remaining resources where the rules permit continuation.

Overwatch and other reactions require an explicitly reserved action or ability resource. The same gunner cannot spend their entire turn shooting and also obtain an unlimited free reaction pool. Known arcs appear in previews; undetected enemies remain unknown. Reaction depth and per-round limits need a clear cap, initially one reaction per reserving character.

## 5. Vehicle construction and roles

The earlier roster mixed physical size and battlefield role. Keep these separate so a light vehicle can be a transport and a heavy vehicle can be a recovery rig.

| Physical class | Typical examples | Main trade-off |
| --- | --- | --- |
| Bike | Solo bike, bike with sidecar | Speed and access versus exposure and stability |
| Light | Buggy, scout | Agility versus armour and payload |
| Medium | Pickup, technical | Flexible general-purpose platform |
| Heavy | War truck, armoured carrier | Protection and impact versus turning space and cost |
| Oversized | Late-game monster rig | Mobile strongpoint with severe access and support demands |

Roles include scout, gun platform, rammer, transport, hauler and recovery/support. These describe fitting and use rather than a second incompatible movement system. Oversized rigs are future scope.

Components may include frame, engine, steering, individual wheels, armour panels, weapon mounts, ram, fuel system and transport attachments. Mount compatibility and chassis limits constrain combinations. Salvaged parts should change a visible capability or weakness, not only add percentage bonuses.

### Stations and access

Each station defines an occupant limit, fit, protection, allowed actions and connections to neighbouring positions. Useful station types are driver, gunner, protected passenger, open passenger, external rail and specialist working position.

Boss fit is a real station/access constraint. The POC truck has a boss-compatible gun station; the ordinary bike sidecar does not. Using a heavy gun also checks body or mount support. A Nib operating a mounted gun uses that gun normally because the mount carries its weight and recoil.

Connections form a small navigation graph over the actual vehicle. An external rail might lead to the roof and cargo bed; a locked cab may require access from a door. Characters cannot freely teleport from the rear bumper into the driver's seat.

Switching stations costs an action when there is a legal route. Occupied or obstructed stations remain blocked. The prototype need not model a fully walkable interior: named, visible positions can represent it.

## 6. Bikes, sidecars and external transport

A bike exposes its rider directly. Targeting distinguishes **rider**, **bike** and any sidecar occupant or mounted weapon. Killing the rider risks an uncontrolled crash; disabling the bike can leave a surviving rider. The exact crash outcome depends on speed, terrain and protection, not an unconditional kill rule.

Bikes suit scouting, flanking, pursuit, exposed-crew attacks, boarding delivery and small-objective recovery. Their narrow footprint gives route advantages, but a sidecar widens the footprint and changes handling.

Proposed sidecar fittings include a passenger seat, gunner and mount, cargo pod, extra fuel or repair equipment. A repair sidecar can enable an adjacent repair interaction; initially require a stopped/slow legal working window. Repairs alongside fast-moving rigs are a later advanced manoeuvre, not a free passive aura.

A passenger jumping from a sidecar leaves the rider in control. A solo rider jumping away leaves an undriven bike and invokes the uncontrolled-vehicle rule. Show the expected bike outcome before confirming.

External rails and open beds offer quick deployment and boarding access at the cost of exposure, passenger displacement and falling risk. Protected transports offer survival and enclosed seating, with access through designated exits. Capacity alone should not erase those tactical differences.

## 7. Transport, load and extraction

Use both **physical fit** and **load capacity**. A free passenger position does not imply that a bike or engine fits through its door. A large cargo hold is not automatically an unlimited protected passenger compartment.

Each chassis declares its crew stations, passenger/cargo transport pools and which positions share a pool. Dedicated operating crew are accounted for in the chassis baseline. Every additional passenger or cargo object counts once against its declared pool; placing it in a station must not charge it twice or make it free.

Prototype examples for a shared transport pool:

| Object | Example load |
| --- | ---: |
| Nib passenger | 1 |
| Krag passenger | 2 |
| Krag clan boss passenger | 3 |
| Stowed bike | 2 |
| Salvaged engine | 4 |
| Standard scrap bundle | 1 |

A capacity-8 hold could therefore carry four Krags, two Krags and two bikes, or an engine and four scrap bundles, **if** it also has the required physical positions and restraints. These numbers are placeholders. Cargo quality, weapon strength and combat value are not derived from load units.

Secure/load/unload requires an adjacent character, a valid access point and a stopped vehicle in the initial rules. Some heavy objects require lifting equipment or multiple characters. Normal loading never exceeds capacity; optional emergency overloading is an open later rule with handling consequences.

Extraction counts what crosses the exit with a legal carrier, or what is explicitly recovered under that mission's rules. Capturing a hauler does not automatically recover it if nobody can drive or tow it out. Recovery rigs and tow attachments can support this later; do not simulate a full tow-chain system in the first slice.

### Foot salvage and casualty recovery

Extracted cargo and crew are registered separately from final encounter completion. The engine leaving secures the objective but does not recover people elsewhere. A destroyed carrier leaves a legal foot-retreat option: Nibs carry 1 portable scrap load, regular Krags 2 and the boss 3, with movement penalties and longer campaign travel. Downed crew need a recovery sling or compatible transport; unrecovered living captives create rescue opportunities. Full costs, fit and travel rules are in [11-campaign-events-rescue-and-retreat.md](11-campaign-events-rescue-and-retreat.md).

## 8. Boarding, dismounting and hijacking

### Enter or leave a friendly vehicle

At stopped/slow speed, a character uses a reachable station or exit. At fast speed, jumping or grabbing an external rail may require a Reflex/control check; Flat-out attempts are substantially riskier. Valid destination space is always required.

A successful **Grab on** reaches an external hanging position. Climbing into a protected station is a further action. The passing vehicle must actually have a usable handhold and a route event close enough to the character. Reserve the grabbing action in advance; it is not an unbounded free reaction.

Dismount previews landing position, exposure, speed-related injury risk and the cost. No safe space means no ordinary dismount there. An explicitly dangerous bail-out may be offered with its consequences visible.

An adjacent actor may Clear incapacitated occupant for 1 AP when the station is reachable and there is a valid supported destination for the body. This clears a downed/dead defender without requiring an execution; it does not teleport them through a closed cab or grant control. The first prototype requires a stopped host for this relocation.

A Tin Can vehicle cannot board any vehicle. Its dismounted pilot can use ordinary character boarding. A proposed single hatch-rail node permits incoming attacks on Tin Cans under the access rules in file 12; this does not create outgoing boarding for the machine.

### Reach an enemy rig

Boarding can begin from an adjacent vehicle, bike, the ground, a raised structure or a jetpack flight. Valid target nodes include cab rail, roof, rear ladder and cargo bed.

Evaluate distance, height, relative motion represented by the speed bands, available handholds, target manoeuvring, character ability, gear and carried load. Display the actual calculated chance and failure consequences. Any percentages used in mockups are illustrative, not design constants.

An ordinary clear climb onto a stopped, accessible vehicle should not require a theatrical random failure roll. Risk checks belong to genuinely hazardous transitions.

### Fight aboard

After arrival, the character occupies a real node on the enemy vehicle. Connections determine where they can move and what they can reach. Examples include attacking an exposed gunner, sabotaging an engine access point, damaging a mount, opening a cab, bracing or throwing an opponent from a reachable edge.

Defenders can contest positions, attack or push boarders. A driver may make a costly shake-off manoeuvre if the route permits it. The preview must also show risk to the driver's own external riders; it cannot selectively ignore friendly passengers.

**Hijacking requires control, not merely contact.** The driver station must be reachable and usable, hostile occupants must be dealt with as required, and the controls and engine must still work. Mixed occupancy remains possible. Controlling the cab does not erase a hostile gunner or instantly make the whole vehicle safe.

Jetpack boarding uses these same positions and control rules; flight only changes the approach. See [02-characters-jetpacks-and-bionics.md](02-characters-jetpacks-and-bionics.md).

## 9. Damage, ramming and survival

Krag physiology applies to the character rather than the vehicle: resistant skin supplies the natural armour in the character rules, low pain prevents pain-only penalties, and fearlessness blocks fear-driven panic/routing. Injured limbs, blood loss, loss of grip and physical knockback still resolve normally. A fearless driver can keep control through a painful hit, but cannot operate destroyed steering or an unusable hand by ignoring it. See [02-characters-jetpacks-and-bionics.md](02-characters-jetpacks-and-bionics.md) for trait and boss rules.

Learned perks and active structural wound debuffs feed the same action previews and resolution rules. A damaged leg can reduce movement and boarding even for a fearless Krag; earned Sure Grip does not erase that wound. Only a completed, functional replacement restores its linked functions. A crew member still fitting/recovering at the fort cannot enter the deployed roster. The exact modifier order and example values are in [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md).

Resolve damage against visible components and occupants with protection, angle and exposure considered. Broad attacks may hit several systems; aimed component or crew attacks trade accuracy, time or ammunition for a more useful result.

| Result | Tactical meaning |
| --- | --- |
| Engine disabled | No powered movement; rig may still coast, fire and be repaired |
| Steering damaged | Reduced legal turning, not arbitrary teleporting |
| Wheel destroyed | Handling/speed loss, possible instability and a changed silhouette |
| Gun mount broken | That weapon cannot operate normally |
| Driver incapacitated | Control lost until someone legally takes over |
| Frame destroyed | Vehicle cannot be restored by a quick combat repair; wreck remains |
| Fuel fire | Visible hazard affecting exposed occupants and nearby space |

Not every disabled vehicle explodes. Frame destruction and occupant escape use the explicit one-time crash/casualty rules in file 11. This is essential for capture, survival and salvage. Permanent visual damage can be richer than the underlying collision model, but collision must stay truthful at tactically important scales.

Ramming uses contact geometry, speed, mass, angle and fitted equipment. Both vehicles can suffer consequences. The preview shows contact point, expected severity and uncertainty rather than a guaranteed damage number for an unresolved roll.

An aware infantry target can evade a vehicle impact when there is reachable space. Use Reflex, awareness and available escape locations. Possible outcomes are escape, clip/knockdown or full impact. A character pinned against a wall has fewer options. Resolve this separately from the proposed ranged dodge-to-graze rule.

An evasion costs that character's limited reaction allowance and cannot repeatedly make them invulnerable to a convoy. Details need tuning; ordinary infantry should neither be guaranteed roadkill nor effortlessly immune.

## 10. Oversized weapons and demolition attachments

Crusher claw arms and metal jaws add character actions, while wrecking balls and missile racks occupy vehicle hardpoints and use their operator's existing AP. They do not create separate activation groups or bypass crew-transfer rules.

The wrecking rig replaces its gun and transport hold with a crane, ball and travel cradle. It threatens a visible swept area from a stopped/slow position. The missile rig replaces the gun with limited-ammunition area attacks, with scatter and blast exposure shown before commitment. Standard, demolition and missile trucks reuse the chassis while retaining distinct station and load definitions.

The initial special-weapon rules, damage, limits and development stages are centralised in [08-outrageous-machinery-and-weapons.md](08-outrageous-machinery-and-weapons.md). In particular, a sweep must test the whole path, and an area attack must not multiply damage across all component colliders on one rig. These interactions extend the damage and reaction system rather than creating a separate physics game.

## 11. Combat acceptance criteria

The rules should produce useful choices between slowing for a board, keeping speed, firing, bracing and exposing a passenger. Passenger count must carry tactical power and campaign cost without overwhelming turn length. A disabled rig should create a new problem or opportunity, not simply vanish.

The prototype must specifically catch action resets from transfer/hijack, free multi-gunner reactions, sidecars fitting through impossible gaps, and repeated movement from driver swaps. See the scenario list in [05-poc-scope-and-backlog.md](05-poc-scope-and-backlog.md).
