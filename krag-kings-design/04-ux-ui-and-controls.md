# Tactical UX, UI and controls

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Accepted direction:** one tactical screen, contextual commands, clear previews and minimal interruption. Detailed controls and layouts below are proposals. The POC implements mouse and keyboard first, while keeping actions independent of input device.

## 1. Primary interaction

**Select → choose action → choose target/path → preview → commit.**

Selection never spends actions. Hovering, inspecting or cancelling a preview never changes game state. A committed command is validated again against the current state before it spends resources.

Click a vehicle to focus its group. Click a visible character or station portrait to focus that individual. Click an on-foot character to show foot actions. Click a boarder attached to an enemy rig to show that character's reachable positions and actions.

There are contextual tools such as movement planning or target selection, but no separate battlefield screen for boarding, interiors or jetpack travel.

## 2. Screen layout

| Region | Normal content | On demand |
| --- | --- | --- |
| Top bar | Round, active side, objective summary | Mission details and combat log |
| Readiness strip | Friendly groups ready/used; currently activating group | Known enemy readiness; independent boarders |
| Main view | Battlefield, selected outline and essential markers | Movement route, firing arc, landing area, component nodes |
| Bottom strip | Selected unit, crew/station portraits, remaining actions | Passenger drawer and equipment details |
| Context action bar | Up to about 5–6 relevant commands | Secondary actions in a compact menu |
| Inspect panel | Hidden or concise critical state | Components, wounds, modifiers, cargo and implant details |
| Commit area | Action name, cost, target, risk and Confirm/Cancel | Specific failure outcome or blocked reason |

The alternating-choice activation proposal does **not** have a fixed future initiative queue. Show readiness and the active side rather than inventing an exact enemy order. If a fixed-order system is chosen later, the strip may become a true queue.

## 3. Selection and crew stations

A vehicle's strip identifies driver, gunner, passengers, external riders and cargo. A station shows its occupant, protection state, remaining actions and any urgent impairment.

Selecting the station changes the actions. Examples:

| Focus | Primary commands |
| --- | --- |
| Driver | Plot move, brake, ram, brace, leave station |
| Gunner | Fire, aim, reserve reaction, leave station |
| Passenger | Shoot, board, dismount, brace, change station |
| Mechanic | Repair, sabotage, shoot, board, move |
| Jetpack wearer on foot | Move, jump, shoot, interact, brace |
| Enemy boarder | Move aboard, attack, sabotage, brace, dismount |

For the POC, show only implemented commands. The larger design may include reload, engine boost or throwing opponents, but these should not appear as unexplained dead buttons.

The revised signature loadouts add Crusher strike and Bite for the equipped character, and Swing for a wrecking-ball operator. A later missile operator gets Salvo with remaining ammunition. These actions replace irrelevant buttons in context; they do not all appear on every character's bar.

Large transports use summary groups such as Crew 2/2, Passengers 4/6 and Cargo 3/8. Expanding Passengers reveals individual occupants without permanently filling the screen with portraits. A bike naturally has a compact rider/sidecar layout.

Friendly portraits stay selectable even when attached to hostile vehicles or obscured by geometry. Cycling friendly units includes them. Ownership, seat control and allegiance must use separate markers.

## 4. Vehicle movement planning

Choose the driver's movement command, choose a speed band, then place or drag a destination and heading. The route curves inside the chassis's actual turn constraints. Show the vehicle footprint at the endpoint and at a hovered point along the route.

Display current band and proposed band separately. Show travel commitment, any braking cost and remaining actions. At Fast/Flat-out, a long forward route with a broad turn visually teaches the constraint better than an unexplained handling percentage.

Along the path, mark meaningful events: firing point, barrier impact, boarding window and entry into a known reaction arc. Use short labels such as Heavy impact, Unsafe turn or Exposed crossing, with calculation detail in Inspect.

Changing speed, path, crew action or target recomputes the preview. A stale preview is never accepted after damage changes the selected rig's steering or a wreck obstructs the route.

At resolution, preserve the player's spatial context. If an interruption stops the rig, show what caused it, its real position and remaining resources. Do not leave a ghost route implying the cancelled movement happened.

## 5. Shooting and component targeting

Choose a target silhouette, then optionally a visible component or exposed occupant. Highlight the actual ray/arc, relevant cover and valid range. Show chance to hit and possible damage, with explicit reasons such as Cover, Target speed and Optical implant.

An example preview might say `70% hit · 3 damage · 1 action`, with the modifier breakdown one inspection away. That is presentation guidance, not a balancing value.

Keep concealed information concealed. The preview describes what is currently known and uses language such as Unknown beyond sightline where appropriate. It must not reveal an unseen enemy through an invalid-target message or a perfect damage prediction.

## 6. Mount, dismount and change station

Selecting an adjacent friendly vehicle offers an entry action. If only one legal station makes sense, preselect it and show it before confirmation. If several matter, show a small list with occupant, fit and protection.

Dismount shows valid landing locations near the selected exit. High-speed choices include injury/fall risk. A blocked door, occupied landing spot or incompatible pack must have a specific reason, not just Action unavailable.

Changing station previews the route on the vehicle's node graph and its cost. For the POC, explicit commands are preferable to dragging portraits in combat. Dragging may later be useful during loadout planning.

## 7. Boarding and hijack flow

Choosing Board highlights reachable nodes on nearby enemy vehicles. Hovering a node shows the jump or climb path, action cost, calculated chance if a roll applies, and possible failure result. The inspection breakdown can include distance, relative motion, height, grip implant and target manoeuvring.

After arrival, animate the character's portrait moving to its new host vehicle. Keep its allegiance, remaining actions and activation-used state visible. The UI must not suggest that it gained a fresh turn.

While aboard, show only connected positions and interactions available from the current node. Cab access, occupied stations and engine access points should be understandable from the model and markers.

Hijack appears when its prerequisites are meaningful to inspect. Explain the missing step when blocked: Driver still defending, Cab inaccessible, Engine disabled or Vehicle already moved this round. A mixed-crew vehicle displays contested state rather than switching every portrait to the new owner's colour.

## 8. Jetpack flow

Show fuel charges beside the character, with a separate back-slot icon. Selecting Jump reveals legal landing surfaces and a height/range envelope. The player chooses a destination, then sees the swept trajectory, arrival footprint, landing protection and known reaction exposure.

Use distinct shapes for Safe landing, Risky landing and Blocked. A blocked marker explains whether the cause is range, headroom, fuel, occupied space or a collision along the route. Red/green alone is insufficient.

Jumping to a vehicle uses its boarding node selection. The confirm panel states that fuel and an action are spent and that subsequent attacks or movement use the remaining budget.

If an interruption forces a landing or fall, show the event at the point it happened and the resource outcome. Keep the camera usable throughout.

## 9. Damage, wounds and bionics

Normal vehicle display emphasises critical components: frame, engine, steering, wheels and main weapon. The model does most of the work: missing wheel, smoke, bent ram, empty turret.

Inspect exposes exact component health, disabled effects and repair eligibility. A damaged component should not rely solely on a percentage; Steering damaged must explain the reduced turning capability.

Character portraits show urgent wounds and relevant equipment states. Detailed anatomy and implant slots belong in inspection or loadout. Show the injury, its lasting record and what the replacement restores; avoid presenting a bionic arm as both fully restored and still carrying the same lost-arm penalty.

Inspection exposes Tough hide, Low pain, Fearless and Heavy-weapon support as separate Krag traits. The damage preview distinguishes natural skin armour from equipment armour. If a tagged pain/fear effect is rejected, give a brief trait explanation; do not display a panic meter that Krags never use. A broken-arm penalty still names its physical cause.

The boss has a clear rank label, but his body also appears larger in the world. Seat/door/landing previews explain size and load restrictions. Portable heavy-gun previews show whether body, mount or bracing provides support, as well as the weapon's actual accuracy and damage. Bigger visuals must not conceal different rules.

A permanent wound is logged without opening a large campaign screen mid-action. Debrief separates its active debuffs, permanent history and treatment options. Show the leg example as Move 10 m → 6 m, Sprint unavailable and Risky boarding -15 points; do not present a structural effect as pain that a Krag should ignore.

The debrief lists Participation +1, Primary objective +2 and Contribution +1 XP where earned, followed by cumulative XP, next threshold and available perk points. Choosing a perk shows its exact modifier and does not clear wounds. A recovering character can choose a perk while the roster still says Unavailable — recovery until day 4.

Treatment preview names the part, socket, species fit, strain before/after, functions restored, required treatment place and three-day duration before committing the item. Show Fitting, Recovering and Ready with text/icons, not colour alone. Advance day previews the date and patients becoming ready; longer advancement stops on a campaign event, arrival or completion. Show remaining travel days and choices before applying an event. Menus and reloads advance nothing. Rejected treatment consumes nothing.

Display total implant strain and anatomical fit separately: Brok 7/8; a Nib with two light implants 2/2. Heavy Krag-only part and Implant allowance exceeded are different rejection reasons. Entry servo parts explicitly show their proposed Strain 1 and restored functions. Krag upgrade versions additionally show their named equipment perk; Nib restorations show no extra implant perk. Elective Krag fitting previews the same perk and downtime on healthy anatomy; label XP-learned and implant-granted perks separately. Deployment filtering must also be enforced by game rules, not just a disabled UI button. See [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md).

Krag hit reactions should suggest serious irritation, braced determination or renewed combat focus rather than fear, prolonged pain or clowning. They may deliver a dry response or show contained appreciation for a large gun. Nibs may use playful, cheeky expressions, including showing a dark blue tongue in an appropriate personality beat; keep urgent injury and combat states readable. Keep knockdown and incapacitation unmistakable when they occur; personality animation never delays the turn or changes the result.

## 10. Cargo, objectives and extraction

Cargo view shows used/free load and the items consuming it. Hovering an objective item shows its required load and valid carriers. A loaded engine should also appear as a simple physical object in the truck bed.

For Rusthook depot, use a small checklist: Release engine → Load engine → Extract carrier. Completing one step must not silently skip the others. Carrier extraction secures the objective; continue for remaining crew, then offer Finish extraction with an exact abandoned/captured/lost-assets list. Highlight the control console, loading access point and extraction boundary on request.

If the last viable carrier is lost, report that the intact-engine objective is no longer reachable, then show foot retreat, portable-scrap capacity and the longer return. Offer Dismantle engine for scrap with its irreversible primary-objective consequence. Do not pretend that an absent towing feature can resolve the carrier.

Downed portraits say Stable — recovery required, with no bleed-out counter. Show sling attachment, movement/hand restrictions and vehicle loading capacity. A fatal result has a distinct Dead state. Captured crew remain in the roster with a rescue link; released captives do not get a surprise activation. Patients and parties travelling home are unavailable for fort actions.

Tin Can context shows pilot, locomotion and arm modules, but no Board command for the machine. Its dismounted pilot gets the ordinary character actions. The acquisition objective tracks activation, pilot entry and actual machine extraction. Advanced weapons show charge cost and proficiency-gated modes.

## 11. Input and accessibility

| Intent | POC mouse/keyboard | Future controller equivalent |
| --- | --- | --- |
| Select | Left click | Focus cursor/confirm |
| Camera pan | WASD or middle-drag | Left stick while in camera mode |
| Camera rotate | Q/E or right-drag | Shoulder/trigger plus stick |
| Zoom | Wheel | Triggers |
| Cycle friendly | Tab / Shift+Tab | Bumpers |
| Inspect | Hold Alt; toggle option in settings | Hold inspect |
| Cancel preview | Esc | Back |
| Commit | Visible button or Enter | Confirm |
| End activation | Visible button; optional remappable shortcut | Explicit end command |

Right-drag rotates the camera, so it cannot also drag a movement path. Path placement uses left-drag only while the movement tool is active. Disable conflicting camera controls only for the duration of that interaction and provide Esc to return.

Use light text on dark neutral panels, cyan/blue for friendly selection and amber/violet plus distinct shapes for warnings/enemies. Do not rely on red against black or on colour alone. Status icons also have text, and important hover information is available by selection/keyboard.

Provide scalable UI text, reduced motion, camera recentering and a way to dismiss/collapse large panels. Preserve battlefield visibility at an ordinary laptop resolution. Controller and touch shipping support remain later work; the POC does not need a mobile layout.

## 12. Camera and feedback

Default to a controllable elevated tactical view with pan, rotation and zoom. Offer a quick return to the active character. Fade or cut away obstructing roofs while keeping their collision and height readable.

Short optional focus shots may emphasise a ram or jump. Ordinary shooting should not repeatedly seize the camera. Every cinematic should be skippable and return to the player's previous framing. For the POC, use simple animations and brief effects before building a cinematic camera system.

The combat log records actor, action, target, important modifiers and outcome. A debug view may add rolls, node IDs and collision checks, but implementation data belongs outside the normal player interface.

## 13. UX acceptance

### Oversized weapon previews

A claw shows reachable target geometry and whether a component is exposed. A jaw shows a valid adjacent occupant even when the user's hands are busy holding a rail. Both display their AP cost.

A wrecking ball displays the entire swept volume, first expected obstruction, friendly exposure and validated return to its cradle. Show the rig's stowed/operating state and unavailable rail positions. The player should understand why an apparently empty endpoint can still have a dangerous swing path.

A missile salvo shows aim centre, scatter disk, blast envelope, range and the 2-missile ammunition cost. Friendly portraits and objective cargo inside the possible blast area receive a clear warning. Known blast blockers are visible in inspection. Any precise impact marker in a mockup is illustrative: the real preview must not secretly reveal the future RNG result.

After resolution, short chassis recoil, gauge movement, a jaw clack, claw impact or wobbling projectile can convey the comedy without repeatedly taking over the camera. Readable risk and strong feedback matter more than a long cinematic.

### General checks

Without developer explanation, a tester should be able to select a passenger, preview a dismount, cancel it, perform a legal board and understand why the boarder has only one action left. They should also distinguish a valid roof jump from a blocked landing, see which carrier fits the engine, and recognise which damage stopped a vehicle.

If those tasks require reading this design document, the interface needs another pass.
