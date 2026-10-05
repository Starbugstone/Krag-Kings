# Krag Kings — Design overview and campaign

Draft 0.5 · 4 October 2026 · Project label: Krag Kings; final public title remains open.

## Reading this pack

**Current production direction — 5 October 2026:** start with [15 — investor POC realization plan](15-poc-realisation-plan.md) and [the persistent project context](../PROJECT_CONTEXT.md). The user now requires a polished downloadable Windows mission, detailed modular squad models, customization/recovery, audio and wider-game concept art. Compare Unreal and Unity before choosing. Files 00–13 remain design sources; their browser-first and placeholder-delivery proposals are superseded where they conflict with the new plan. The narrated stories explain world/lore and are **not the final scenario**.

This pack develops `game-design-notes.md` and the subsequent discussion into a working design. The original notes remain the source for the original decisions. The later discussion adds the vehicle/infantry relationship, transport, battlefield interface, terrain, jetpacks and bionic implants.

For the earlier mechanics foundation, consult [05-poc-scope-and-backlog.md](05-poc-scope-and-backlog.md) and [06-poc-technical-foundation.md](06-poc-technical-foundation.md). Files 01–04 explain the wider design behind that bounded prototype. The art guide includes the ten original reference sheets and future model requirements. File 08 defines the expanded heavy-bionic and outrageous-weapon direction. Files 09–13 add narrated missions, XP and bionic perks, event-driven downtime, stable casualty recovery, rescue, slower foot retreat, advanced Nib weapons and modular Tin Cans. New production planning starts at file 14; additional concept explorations are registered in file 18. This pack does not contain a playable build or finished 3D meshes.

| File | Owns the detail for |
| --- | --- |
| [01-combat-vehicles-and-boarding.md](01-combat-vehicles-and-boarding.md) | Turns, movement, crew stations, bikes, transport, combat damage and boarding |
| [02-characters-jetpacks-and-bionics.md](02-characters-jetpacks-and-bionics.md) | Character roles, equipment, jetpacks, injuries and bionic implants |
| [03-terrain-missions-and-forts.md](03-terrain-missions-and-forts.md) | Terrain, map topology, verticality, objectives and fort battles |
| [04-ux-ui-and-controls.md](04-ux-ui-and-controls.md) | Selection, previews, contextual commands, information and controls |
| [05-poc-scope-and-backlog.md](05-poc-scope-and-backlog.md) | POC encounter, roster, build sequence, starting values and acceptance criteria |
| [06-poc-technical-foundation.md](06-poc-technical-foundation.md) | Proposed stack, modules, state, commands, navigation, AI and persistence |
| [07-art-direction-and-model-briefs.md](07-art-direction-and-model-briefs.md) | Ten concept sheets, scale, pivots, sockets, damage parts and import checks |
| [08-outrageous-machinery-and-weapons.md](08-outrageous-machinery-and-weapons.md) | Crusher claws, metal jaws, wrecking balls, missile racks and future mechanical absurdity |
| [09-rusthook-narrated-playthrough.md](09-rusthook-narrated-playthrough.md) | Design decisions and narrated raid, XP, Brok's injury, replacement downtime and return |
| [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md) | XP awards, perks, structural debuffs, species implant limits, campaign time and recovery |
| [11-campaign-events-rescue-and-retreat.md](11-campaign-events-rescue-and-retreat.md) | Daily events, rare fatalities, downed recovery, capture/rescue, foot salvage and travel |
| [12-tin-cans-and-nib-technology.md](12-tin-cans-and-nib-technology.md) | Nib technology, piloted modular vehicles, no vehicle boarding and follow-on profiles |
| [13-relay-station-narrated-mission.md](13-relay-station-narrated-mission.md) | Second narrated mission: acquire a Tin Can, test Brok's upgrade, extract or recover |
| [14-source-and-art-audit.md](14-source-and-art-audit.md) | Review of every supplied document and original concept; gaps and conflicting assumptions |
| [15-poc-realisation-plan.md](15-poc-realisation-plan.md) | Current Windows investor POC, engine comparison, integration architecture, production gates and handoff |
| [16-character-and-merch-production.md](16-character-and-merch-production.md) | Detailed modular characters, clothing, armor, tattoos, complete limbs, animation and merchandise derivatives |
| [17-decisions-and-acceptance.md](17-decisions-and-acceptance.md) | Confirmed decisions, unresolved questions, test matrix and release quality gates |
| [18-strategic-concept-art.md](18-strategic-concept-art.md) | New campaign/base/world-map and Tin Can explorations, review notes and exact prompts |
| [19-poc-audio-and-voice-plan.md](19-poc-audio-and-voice-plan.md) | Music, sound effects, race/character voices, quips, integration and mix acceptance |

### Status language

- **Established:** an explicit decision in the original notes or an explicit user requirement in the discussion.
- **Accepted direction:** the broad approach developed in the discussion and accepted as the basis for this draft. This does not approve every example or number.
- **Draft proposal:** a concrete rule suggested here to make the design coherent and testable.
- **Prototype value:** an initial tuning input, not a release specification.
- **Open:** a choice that still needs a decision or evidence from playtesting.

Unless identified otherwise, detailed mechanics in the companion documents are **draft proposals**. Example names, statistics, equipment and mission layouts are illustrative.

## 1. Game identity

**Established.** A 3D, turn-based tactical game about a battered desert gang, improvised vehicles, salvage and lasting consequences. The appeal is the combination of a vehicle brawl and the individual stories of its crew: the mechanic who saved a rig, the boarder who stole a hauler, the driver who came home with a replacement arm.

Combat uses discrete turns. Simultaneous WEGO resolution was considered and rejected. Enemy behaviour uses conventional game AI; no LLM or external AI service is part of gameplay.

Vehicles visibly accumulate damage. Characters retain visible injury histories; active wound debuffs persist until an appropriate treatment or functional replacement resolves them. Between battles, the player develops a 3D base that improves income and other capabilities.

The setting, characters, writing and visual designs have their own identity. The original tabletop and videogame references describe the intended feel, not assets, names or lore to reproduce.

## 2. Design pillars

### Vehicles own distance; infantry owns complexity

**Accepted direction.** Vehicles provide mobility, firepower, protection, carrying capacity and extraction. Characters exploit cover, interiors, height, machinery and boarding opportunities. Mixed spaces are where those strengths interact.

Neither role should be decorative. A driver cannot solve every objective by circling in the largest truck, and a foot gang should find it difficult to recover a heavy haul without transport.

### The crew is the gang

Characters persist across stations, vehicles and battles. A passenger can become a boarder, an on-foot survivor, the driver of a captured truck, or a wounded veteran with a bionic implant. These are changes in the same character's situation, not replacements with anonymous unit tokens.

### Boarding is a central combat activity

**Accepted direction.** Bikes, external rails, vehicle decks, elevated terrain and jetpacks all create ways to reach another rig. Getting aboard begins a contest over positions and systems; it does not automatically transfer ownership.

### Consequences should be visible and understandable

A missing wheel, empty driver's seat or bionic leg should communicate meaningful state. The interface provides precise inspection when needed, and previews known risks before commitment. Spectacle must not obscure why an outcome happened.

### Salvage changes future choices

**Draft proposal carried forward from the notes.** Recovered parts, captured vehicles and injuries shape the next mission. Reaching an extraction point with an engine and three survivors can be a success even if enemies remain alive.

### Outrageous machines with memorable actions

**Established direction from the latest feedback.** The initial art and equipment list were too restrained. Oversized steampunk bionic claws, replacement metal jaws, truck-mounted wrecking balls and improvised missile racks belong in the game's core identity. Keep semi-realistic materials, but exaggerate proportions, motion, noise and crew confidence. Their abilities should create tactical situations, not simply supply small stat bonuses. Regular operation should be readable; optional risky overcharging can create deliberate gambling later.

## 3. Established characters and new equipment requirements

| Element | Established identity or requirement |
| --- | --- |
| Krags | Large bodies, resistant sandstone skin, small tusks, very little pain, fearless temperament, love of fighting and oversized guns |
| Clan boss | A Krag who is physically larger and broader than ordinary Krags; size must be visible on the model, not only conveyed by equipment |
| Nibs | Smaller bodies, light sandy skin, large fennec-like ears; dodge, mechanics and advanced technology; fragile in hand-to-hand combat |
| Jetpacks | Characters can equip them to improve access to height and vertical routes |
| Bionics | Krags willingly accept heavy replacements; fragile Nib bodies permit only limited lightweight bionics; all implants retain anatomical compatibility |
| Progression and recovery | XP grants learned perks; bionics grant equipment perks, including elective replacements; fitting takes time during which campaign events can occur |
| Casualties and retreat | Fatal wounds rare; no bleed-out timer; recover downed crew or rescue captives; portable scrap can be carried home on foot with longer travel |
| Tin Cans | Nib-piloted external machines with wheel/leg and weapon options; cannot board vehicles |
| Mechanical excess | Large weaponised claw arms, metal jaws, wrecking-ball vehicles and missile launchers are explicitly wanted; detailed models and balance remain proposals |
| Art | Semi-realistic, readable 3D characters and vehicles; the earlier flat cartoon direction was rejected |

Krags suit aggressive gunplay, physical boarding and close combat. They enjoy the noise, recoil and spectacle of big guns, and their larger bodies can support equipment that smaller crew need a mount or brace to use. Nibs suit repair, sabotage, advanced weapon controls and support, including operating enormous mounted weapons or piloting Tin Cans. Those are role advantages, not universal class locks. Detailed modifiers remain proposals.

The new Krag traits are established fiction and design requirements. Their first gameplay translation is natural physical armour, no pain-only action penalties, immunity to fear-driven panic/routing, and useful heavy-weapon handling. Physical damage still causes real wounds and loss of function. A player can order a withdrawal, and a Krag can use cover without being afraid. The clan boss uses a larger body/fit profile and a modest health increase in the prototype, while keeping the same action budget as other crew.

## 4. Tactical scope

**Accepted direction.** The combat design includes vehicles and dismounted characters, dedicated transports, bikes and modular sidecars, crew stations, external riders, cargo, component damage, boarding and hijacking.

A battle should support a coherent chain such as: scout by bike, disable an escort, deliver boarders, capture a functioning hauler, load salvage, and escape with survivors. These events should arise from reusable rules rather than one mission-specific script.

The selected unit determines which controls appear, but the player remains on one battlefield. Movement, combat, vehicle interiors represented by stations, and boarding share the same tactical interface.

## 5. Campaign and world — proposal retained from the notes

The preferred draft is a persistent campaign with meaningful crew loss, a procedural strategic map, several possible starting gangs and a clear ending. Rare fatal outcomes, recoverable downed crew and captive rescue are now established directions; exact fatality tuning and the wider campaign format remain proposals. A roughly 4–6 hour first complete campaign is a scope target from the original proposal, not a promised play length.

The proposed loop is:

1. Inspect the gang, repair rigs and choose equipment at the fort.
2. Choose a destination and commit fuel, crew and transport.
3. Fight for a mission objective, with retreat and partial success supported.
4. Extract the survivors, captured vehicles and cargo actually recovered.
5. Award experience/perks and resolve wounds, treatment, repairs, salvage and rival consequences.
6. Improve the fort, advance campaign time through explicit choices, and prepare an available roster for travel or a defensive raid.

A node or hex map represents travel rather than a continuous free-roaming world. Fuel is the proposed travel resource. Scrap fields, traders, rival forts, mutant camps and a central ancient wreck provide destinations. Rivals expanding, raiding and holding grudges, plus storms changing routes, are later campaign systems rather than prerequisites for the combat prototype.

### Proposed fort facilities

| Facility | Main purpose |
| --- | --- |
| Scrapyard | Income and processing recovered material |
| Garage | Vehicle repair, parts and attachments |
| Sawbones | Treatment place, species-compatible replacement limbs, bionic installation and recovery before redeployment |
| Bunkhouse | Crew capacity |
| Fuel still | Travel fuel |
| Watchtower | Strategic visibility and warning |
| Trophy wall | Recruitment and gang identity |

The fort grows from tents and wreckage into a fortified scrapyard. Crew members visibly inhabit it with their scars and implants. Using the built fort as a raid battlefield, with persistent damage, remains a substantial campaign proposal. Its route constraints are described in the terrain document.

### Crew progression and time

XP/perks, wound debuffs, replacement downtime and species-specific bionic limits are now established requirements. The current tune gives Brok three in-game days of fitting/recovery; he cannot deploy during that period, though earned XP and perks remain. Krags are comfortable with heavy replacements, while Nibs use lightweight restorations and a small total implant allowance. Exact strain, XP and timing values remain proposals in [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md). The POC proves a small debrief/perk/recovery loop without requiring the full campaign economy or 3D fort.

### Connected campaign consequences

Passing campaign days can produce eligible random events and guaranteed consequences such as rescue leads. A downed character remains stable without a bleed-out timer; actual recovery or a later rescue is required. Fatal outcomes should be rare. Abandoning the last working vehicle can turn a raid into a slower foot return with limited portable salvage, rather than trapping the gang. Bionic installations provide useful equipment perks and can replace healthy anatomy by choice. Exact draft contracts are in files 10 and 11.

Tin Cans are external Nib-piloted vehicles, with no outgoing boarding ability. Their original rules and advanced Nib weapon profiles are follow-on content in file 12, illustrated by file 13. The ten original sheets are preserved; the new tall barrel-shaped Tin Can exploration and strategic concepts are registered in file 18. Final production designs and advanced-weapon concepts still need review/development.

## 6. Setting and tone — still provisional

The existing setting proposal is **the Scour**, a desert world of glass flats, canyons and scrap fields. **The Big Iron** is a half-buried ancient machine large enough to contain a city. The **Rebuilders** want to restore it; the **Strippers** want to dismantle it. A possible campaign twist is that salvaging it slowly wakes it.

These names and that conflict have not been locked. Krag Kings is the current project label; the earlier name shortlist was not a final naming decision.

The intended tone mixes dangerous scrap-built machinery with dry humour and overconfident crews. Krags could use radio handles and trucker slang; Nibs could use impatient, mangled engineering jargon. Humour should come from character and consequences as much as dialogue.

Krags actively relish a good fight. Their dialogue, confident hit reactions and delight in oversized guns should communicate that appetite, without involuntary attacks overriding the player's commands. The boss's bulk and appetite for the biggest gun should announce leadership before a nameplate does. Whether bosses grow through age, dominance or another biological process remains open; their larger physical size is established.

The earlier idea of mistreated Nibs retaliating through sabotage is also unconfirmed. If explored, it needs a visible relationship system and player agency; unexplained friendly sabotage would conflict with tactical readability.

## 7. Presentation and production boundaries

Use chunky, readable silhouettes, textured materials, cracked skin, rust and grime. Vehicle damage, external riders, landing areas and exposed components must remain legible from the tactical camera. Jetpacks and implants should look like parts of this setting, with clear mounting points and species-appropriate scale.

The proposed damage approach uses component states, detached/swapped parts and bounded cosmetic deformation rather than a full soft-body simulation. Modular body parts and scars support persistent injuries. Exact technology depends on the eventual engine and asset tests.

**Open for production:** Unity versus a web engine. The original notes preferred Unity for tooling and identified a preference for web delivery. The technical document proposes a reversible Babylon.js/TypeScript starting point for the POC; it does not settle the production engine. Engine licensing, browser support and production-tool capabilities require a fresh assessment at that production decision.

## 8. First playable aim

Prove one small battle where both vehicles and foot characters matter, a boarding manoeuvre changes the situation, a jetpack provides useful vertical access, and an oversized claw or metal jaw creates a memorable action. Include a hostile wrecking-ball rig so the first playable demonstrates the wild tone. A missile-rack fixture follows once the basic encounter works. The prototype needs a coherent interface and rules before it needs a large roster, procedural campaign or complete fort economy.

The staged scope and unresolved decisions are in [05-poc-scope-and-backlog.md](05-poc-scope-and-backlog.md).
