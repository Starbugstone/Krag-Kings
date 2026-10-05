# Campaign events, casualties, rescue and retreat

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Established:** advancing campaign time can produce random events. Fatal wounds are rare. Downed comrades have no bleed-out countdown and must be recovered to return home; captured survivors can be recovered through a rescue mission. Losing transport does not trap surviving crew: they can retreat on foot carrying portable scrap, with a longer journey.

All percentages, load values and timing examples below are **prototype proposals**. These rules supersede the earlier open casualty/extraction descriptions. [File 10](10-experience-wounds-and-recovery.md) owns XP, wound debuffs, elective bionics and treatment. This file owns the campaign clock, physical recovery and return journey.

## 1. Campaign time and events

Time advances in integer campaign days, through resting or committed travel. Combat rounds, menu use and real-world hours do not advance that clock. Offer Advance one day and Advance until an interruption. A multi-day request processes days individually and stops for a decision; it cannot silently skip three days of events while a limb is fitted.

For each elapsed day, in order:

1. Advance the date once and resolve treatment completions and journey progress.
2. Apply scheduled events, such as an already-known job deadline or a rescue lead. These are not random rolls.
3. If there is no unresolved decision, evaluate one eligible random event: initial chance 35% per day, then select from location/state-appropriate entries.
4. Stop for an event choice, mission arrival, or a crew member becoming ready. The player may then continue advancing.

Use a campaign RNG separate from combat RNG. Persist event IDs, rolled outcomes, consumed options, dates, cooldowns and pending choices. Reloading a day cannot reroll its event or its rewards. A scheduled decision blocks further advancement until resolved; resume the same day's remaining work without processing it twice.

At most one random event occurs per day. Apply a two-day cooldown to a repeated event type initially. Events can be helpful, inconvenient, or offer a trade-off; resting is not automatically punished. Eligibility includes party location, conscious crew, inventory, available missions and completed upgrades. Never offer only unaffordable or impossible choices.

| Initial event | Eligible location | Choice and concrete consequence |
| --- | --- | --- |
| Scavenger rumour | Fort or route | Reveal an authored optional salvage location; accepting the information costs no time or item |
| Passing parts trader | Fort | Trade one scrap bundle for one light implant part when both exist in the fixture, or decline; no full shop required |
| Loose salvage | Route | Take one scrap bundle if carrying space exists, or leave it; update the remaining journey estimate if the party becomes burdened |
| Sandstorm detour | Route | Add one travel day or abandon that journey destination and choose a legal return route; no automatic crew damage |

A route can receive only one sandstorm delay in the first implementation. This prevents a chain of rolls from indefinitely extending the return. Added days still count for recovery and event checks. A travel change is previewed before commitment, and the event that caused it cannot repeatedly extend its own duration.

Later events may offer rival raids, ambushes, bargains, recruits and time-sensitive jobs. Do not create an unimplemented tactical battle from an event button. The initial four events can be text/data outcomes; a rumour points to an existing fixture when one is available. Rescue offers are guaranteed consequences of capture, not a lucky roll among random events.

## 2. Downed is a recoverable state

At zero health, resolve the character's first incapacitation event of the encounter. Initial mortality tuning proposal: **2% fatal, 98% stable downed**, rolled once and saved with that event. This number is a playtest starting point, not final balance or real-world physiology. A test fixture can use fixed seeds to verify either branch.

A fatal result is explicitly shown as Dead. Otherwise the character is Downed: no actions, reactions, operation of a station or independent movement. There is **no bleed-out timer**, periodic mortality roll or death caused simply by waiting for rescue. Repeated hits cannot farm additional mortality rolls; the first POC does not allow execution attacks or repeated damage against a downed body. Active rescuer exposure and loss of access provide the tactical danger.

An existing wound and its penalties persist. Incapacitation does not reset inventory, XP, implants, body size or identity. A driver becoming downed loses control under the ordinary vehicle rules. A downed passenger already secured aboard a successfully extracted vehicle returns with it; do not require unnecessary unloading and reloading.

### Wound generation boundary

For the battle prototype, retain the explicit structural leg-injury fixture. For the first connected campaign test, a nonfatal first downing can assign that leg wound once if it is not already present; a recovered survivor returns for treatment. More varied nonfatal wounds and injuries suffered while still conscious need a later injury table. Do not invent repeated limb losses from every hit. The narrated injury to a conscious Brok remains an illustrative authored case.

No in-battle revive is required initially. A survivor recovered to the fort becomes conscious before later deployment, with active structural wounds intact; the existing preparation health-reset simplification does not bypass a treatment lock. Captives stabilised between encounters can start a later rescue mission conscious but restrained, with low health and their existing impairments.

## 3. Recovering a teammate on the battlefield

Recovery is an explicit action and location state, not an automatic reward at mission end.

| Interaction | Initial rule |
| --- | --- |
| Attach recovery sling / pick up | 1 AP, adjacent accessible downed ally, free gripping hand, valid support/path; one casualty per rescuer |
| Move with casualty | Ordinary foot Move becomes ×0.5 after other movement modifiers; no Sprint, jetpack use, boarding jump, attack or vehicle operation while attached |
| Put down / hand over to vehicle | 1 AP at valid supported ground or a stopped vehicle's reachable access; validate actual capacity and fit |
| Transfer to another rescuer | Put down then attach using ordinary actions; no teleporting a casualty between distant actors |

The standard expedition kit includes a simple recovery sling. It can drag even a larger casualty, allowing a surviving Nib to recover a Krag when terrain permits. It is a rules abstraction with a trailing body footprint: validate the whole path and any stair/door link for both bodies. A crane or physics rope simulation is unnecessary. A crusher claw supplies a gripping hand for this purpose, but not precision controls.

While attached, a rescuer cannot carry portable scrap. The casualty keeps their equipped items with them; they do not become free shared cargo for extra salvage. On loading into a vehicle, use the casualty's passenger load: Nib 1, Krag 2, boss 3, and a compatible position. Releasing the casualty at extraction is part of registering the attached pair, not a requirement to leave them behind outside the zone.

This supports one survivor bringing one comrade out. Recovering several downed people may require several trips, other surviving crew, or an accessible vehicle. A mission with unrecoverable geometry must disclose that condition; authored POC maps need at least one valid ground recovery route.

## 4. Extraction does not end when the first truck leaves

Crossing an exit registers the actual characters, vehicle and cargo crossing it and removes them from tactical play. A carried casualty crosses with their rescuer. The gang cannot fire from off-map or return extracted units during this encounter.

For Rusthook, extracting the intact engine in a valid carrier sets **Primary objective secured**. Continue tactical play for crew still on the map. End the encounter when all friendly entities are accounted for or the player chooses Finish extraction / Abandon remaining assets. Before abandonment, list the people, vehicles and items that will be left, and the resulting capture/loss states.

Debrief distinguishes objective success, recovered survivors, captured survivors, rare fatalities, extracted cargo, and abandoned equipment. Securing the engine does not teleport Tikk or an injured Brok home. Abandoning the engine can be a partial recovery while still saving the gang.

### Vehicle failure and escape

Disabled wheels or an engine do not stop occupants from using accessible exits. Frame destruction leaves a physical wreck. As a small prototype rule, a transition to destroyed frame applies one 3-damage physical crash hit to each occupant, after applicable armour; it does not repeat on later turns. Resolve any resulting first downing once. Exposed falling occupants use fall damage instead of adding both results. This is an authored damage rule, not an explosion simulation.

Open exits remain usable at 1 AP. An adjacent ally can spend 1 AP with a repair tool to open a damaged hatch, followed by the ordinary casualty recovery action if needed. Validate a real clear exit/landing; do not eject bodies through solid walls. The initial map must avoid unavoidable wreck placements that seal every exit, and a blocked recovery path must be shown rather than silently killing the occupants.

## 5. Foot retreat and carrying scrap

Every demonstration encounter has a reachable foot extraction boundary. Destroying the last carrier can make the primary cargo objective impossible, but cannot silently disable retreat for otherwise mobile survivors.

| Conscious character | Portable-scrap capacity |
| --- | ---: |
| Nib | 1 load |
| Regular Krag | 2 load |
| Clan boss | 3 load |

These loads describe expedition salvage carried with the standard harness. Equipped personal weapons/tools are already accounted for in the body profile and cannot be converted into extra salvage capacity. Loading/dropping one accessible scrap bundle costs 1 AP; each bundle uses 1 load. No overload is allowed in the first rules. While carrying scrap, ordinary foot Move is ×0.75 and Sprint/jetpack use are unavailable. Recovery-sling users instead use the casualty rule and have no scrap allowance.

Only **portable** items qualify. The four-load Rusthook engine remains a lifting-equipment/vehicle objective and cannot be made portable simply by adding several characters' capacity numbers. At its reachable access, Dismantle for scrap costs 2 AP and a repair tool, irreversibly replacing the engine with four one-load bundles. This loses the intact-engine objective and enables partial salvage. Show the change before confirmation. Cooperative hauling of intact engines is later scope.

The four original crew could carry seven scrap load if all are conscious and none is recovering a casualty. That is a ceiling, not a guarantee that all items fit or can be reached. Leave the excess behind. A working bike or Tin Can protects/transports its own occupants but does not automatically transport the remaining foot party.

### Return journey

Separate tactical extraction from the journey home. Use an authored route's normal motorised duration B, initially one day for the sample return route:

| Party's return mode | Duration |
| --- | --- |
| Everyone legally transported in functional vehicles | B |
| Party walking without salvage/casualties | 3 × B |
| Walking with any carried scrap or recovered casualty | 3 × B + 1 day |

A mixed party moves at its slowest member's mode in this initial design; splitting into independently simulated convoys is deferred. Apply the burden surcharge once per journey, not once per person or scrap bundle. Wounds still affect tactical movement; further strategic wound multipliers are deferred.

Process these days through the same campaign clock and event system. Display arrival estimates before departure and after an accepted detour or load change. Parties in transit cannot start fort surgery or deposit carried scrap into fort inventory. Treatment of patients already at the fort continues. XP from the resolved encounter can be recorded once at debrief; access to returned crew and cargo requires arrival.

Journey records track elapsed days and remaining base work. When mode/load changes at an event waypoint, recalculate only the remaining work; never restart the whole trip or repay completed days. The prototype may lock transport mode for each committed route leg to keep that calculation small.

## 6. Capture and rescue missions

When an enemy holds the encounter area after the gang leaves, unrecovered living downed crew become **Captured**, not automatically dead. Retain identity, XP/perks, wounds and installed implants. Loose carried loot and removable equipment may be stored in an authored enemy stash; identify exactly what is recoverable rather than deleting random gear. Implants are not stripped as a routine capture consequence.

Create a rescue lead for those captives when the battle result is committed. It is guaranteed and visible even if the random event roll fails. The first rescue opportunity has no execution countdown or expiry. Future relocation events can change the route or difficulty with clear notice, but cannot smuggle a bleed-out timer back into the system.

Rescue fixture: reach the holding point, spend 1 AP to release each reachable restrained ally, then extract those people. Captives are not recovered merely because the gate is opened. A conscious released ally becomes player-controlled with no new AP during the current round and can act normally next round; a still-downed ally needs the sling. Equipment retrieval is a separate optional interaction, subject to carrying limits.

The rescue party's participating returnees earn that mission's normal XP. Captives keep prior earned progression; release alone grants no free XP or retroactive duplicate rewards from the failed encounter. A captive who becomes active and contributes can qualify for the current rescue encounter normally.

If the gang withdraws but no enemy remains to capture the abandoned casualty, retain a known **Missing at site** recovery objective instead. Neither state resolves through passive death. Recoverable wrecks can similarly create salvage-return markers; a marker is not a promise of an implemented towing system.

### Avoiding a roster dead end

If all deployed crew are incapacitated, resolve the battle loss and capture/recovery states explicitly. Use deployable fort reserves for the rescue. The connected POC can provide one clearly labelled, predefined two-person emergency rescue detachment when no playable crew remains; it uses existing Krag/Nib models and the same rules. This is a proposed test fallback, not a free recurring recruitment economy. If that last recovery route also fails and no controllable crew remains, show campaign defeat and offer restart.

Do not generate an unusable rescue button that requires the very captives it is meant to recover. The fixture ensures released conscious captives have viable foot exits; it does not require the emergency pair to drag an entire four-person crew at once.

## 7. Small connected POC and verification

Keep the first combat fixture playable independently. Add these consequences as a connected follow-on: stable downed recovery, explicit final extraction, foot salvage/return, four campaign event entries and a rescue layout using existing terrain/actors. No procedural world or full recruitment economy is needed.

| Case | Required result |
| --- | --- |
| Wait ten rounds beside a downed ally | No bleed-out, repeated mortality or hidden HP decay |
| Reload the first downing or debrief | Same saved casualty result; no repeated injury/XP roll |
| Extract engine while Tikk remains on-map | Objective secured, encounter still active |
| Lose truck and leave on foot with two bundles | Legal retreat, partial objective result and longer return through daily events |
| Recover downed boss with a Nib and sling | Valid where both bodies fit; movement penalty and action restrictions apply |
| Abandon Brok in enemy-held depot | Captured record and usable rescue opportunity, preserving prior progression |
| Release captive and select them immediately | No fresh AP until the next round |
| Advance three treatment days with an intervening event | Clock stops for the choice, then resumes without skipping or duplicating the day |
| Return from four-day burdened walk | Each day counted once; fort patients progress; travelling crew were unavailable at the fort |
| No remaining deployable main crew | Explicit emergency rescue fixture or explicit terminal defeat; no stranded campaign screen |
