# Characters, jetpacks and bionic implants

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Established:** Krags and Nibs have distinct physical identities and strengths; character wounds are visible and permanent; characters can equip jetpacks and have bionic implants. Krags feel very little pain, have resistant skin, love fighting, are fearless, prefer bigger guns, and their clan boss is physically bigger than ordinary Krags. Experience unlocks perks, wounds impose debuffs, and replacing a limb requires downtime. Krags readily accept heavy machinery in place of body parts; Nib bodies support only limited lightweight bionics. Krag bionic upgrades may also grant equipment perks and replace healthy anatomy electively; Nib implants restore ordinary function without upgrades, as clarified below. Downed crew have no bleed-out countdown; rare fatality, recovery and captive rescue rules are in file 11. Specific numerical modifiers and implementations below remain prototype proposals.

## 1. Character identity and roles

Characters remain individual gang members wherever they are: driving, riding, hanging externally, fighting aboard an enemy or moving on foot. Equipment, injuries and action budgets belong to the character, not the current vehicle.

| Species | Physical identity | Starting strengths | Starting limitations |
| --- | --- | --- | --- |
| Krag | Large body, resistant sandstone skin, heavy brow, small lower tusks | Physical toughness, little pain, fearlessness, boarding, close combat and oversized guns | Larger transport footprint and less access to small gaps |
| Krag clan boss | Same species with a significantly taller, wider, heavier body | Krag traits plus greater physical presence and prototype health | Larger fitting/collision profile and greater passenger load; ordinary action budget |
| Nib | Small sandy body, large fennec-like ears, wiry limbs | Dodge, mechanics, sabotage and advanced weapon controls; Tin Can piloting | Lower hand-to-hand strength and limited lightweight bionics |

The species distinctions and new Krag temperament/body requirements above are established. Exact modifiers and further role advantages are provisional. Avoid hard class locks for basic driving, shooting, mounting and objective interactions. A Nib can drive a fitted truck; a Krag can learn repairs, though they may begin less capable.

For the POC, use a small attribute set: toughness, shooting, melee, Reflex and mechanics. Movement range, carry limits, health and armour are explicit derived values. Add a new stat only when it creates a distinct decision the existing ones cannot express.

The proposed ranged dodge rule converts some successful hits to grazes. Reflex checks for a vehicle jump, impact evasion or precarious landing are separate checks with separate outcomes. Do not silently reuse ranged dodge as immunity to every hazard.

### Krag physiology and temperament

**Confirmed performance update — 5 October 2026:** Krags are serious brute force who love big guns and smashing skulls, are fearless and feel little pain. They are grounded and expressive without clowning. Show weight and ground impact in their walking, supported by planted feet, believable weight transfer and muscle/joint deformation. Their enjoyment of combat can read as a determined scowl, controlled grin or contained satisfaction; playful tongue-out gestures belong to Nibs. These performance cues do not create automatic combat actions or new numerical bonuses.

| Established trait | Proposed gameplay expression | What continues to matter |
| --- | --- | --- |
| Very little pain | No action, aim or movement penalty caused solely by pain; minor hits receive a short confident reaction | Broken limbs, incapacitation and damaged implants still have their physical effects |
| Resistant skin | Natural armour 1 against ordinary direct physical hits in the first tune, added to applicable worn armour | Armour penetration, powerful impacts and exposed wounds remain meaningful |
| Fearless | Fear/terror cannot force panic, routing or fear-based action loss | Player-ordered withdrawal, cover, bracing and physical displacement remain available |
| Loves fighting | Eager dialogue and animation; enemy AI favours useful attack/boarding opportunities when choices are otherwise comparable | Mission priorities and player control remain intact; no compulsory charge or attack |
| Loves big guns | Oversized weapon choices, strong recoil handling and obvious enthusiasm | Ammunition, arcs, fit, required hands and AP still constrain use |

The no-pain-penalty rule is a POC abstraction for feeling very little pain, not a claim that Krags have no sensation. Separate a wounded arm's mechanical impairment from a pain debuff: ignoring the latter does not make a broken hand grip a gun. Likewise, a blast can physically knock a fearless Krag down even though it cannot frighten them into fleeing.

Use explicit cause tags for effects. Pain and fear are filtered by these traits; structural injury, bleeding, unconsciousness, physical stun and knockback use their own rules. Do not label all disabling effects as pain or fear to simplify the implementation.

The first POC does not need a morale minigame. Trait data, status validation and a small debug fixture can prove these interactions while the normal encounter demonstrates Krags fighting confidently through ordinary hits.

### Nib personality and performance

Nibs are playful adult engineers who are physically weak and a little cowardly, while remaining light-footed, stealthy and nimble. Their practical technical competence coexists with caution around danger, cheeky expressions and a tongue-out gesture. **Their tongues are dark blue.** Show alert glances, flinching or a cautious posture when appropriate; technical confidence does not make them fearless fighters. Do not translate playfulness into a childish mascot face, constant slapstick or perpetual hostility toward allies. Automatic panic, routing, action loss or forced retreat is not established by this personality direction.

Use responsive eye/brow/ear acting, expressive lips and a controllable tongue for close-ups and future cutscenes. Author light contacts and agile balance changes in walk/run cycles. Facial and body deformation must preserve the selected concept likeness in motion. Mouth interiors and expression sheets may be developed provisionally for user review; only the explicitly specified tongue color and personality direction are settled by this update. See [16](16-character-and-merch-production.md) for rig requirements and [19](19-poc-audio-and-voice-plan.md) for voice direction.

### Big guns as a playable preference

Add a portable heavy-gun profile rather than only scaling up a rifle mesh. The starting proposal is 4 damage, 25 m range, 60% base hit chance and 1 AP to fire. The lower base precision, larger hit and imposing feedback make it a choice beside the ordinary 3-damage, 75%-base gun. Normal cover, target-speed, aim and implant modifiers still apply.

A Krag's strength supplies the required heavy-weapon support when standing securely or in a compatible station. A smaller character needs a proper mount or a Brace action before using a compatible portable heavy gun; bracing lasts until movement or a station change. This checks physical support and fit, not a blanket species ban. Mounted weapons supply their own support and retain their weapon profile.

Weapon hand requirements remain explicit. A one-handed boss gun needs an integrated harness/brace; an item defined as two-handed cannot be fired with one working hand merely because its owner is a boss. Oversized one-handed guns are welcome when designed for that role. Holding a rail occupies the required hand, so the iron jaw retains a useful niche.

### The clan boss

The boss is visibly bigger in body, not merely wearing a taller hat. Initial modelling targets are roughly 2.75 m tall compared with 2.2 m for an ordinary Krag, with a broader torso, thicker neck and larger limbs. Exact dimensions are tuning/art targets rather than final lore measurements.

Use 14 starting health versus 10 for a regular Krag, with the same natural armour 1 and the same two actions. The boss does not gain free attacks, extra vehicle moves or a fear aura that contradicts other Krags' fearlessness.

As a passenger the boss consumes 3 transport load instead of 2, subject to seat/exit fit. Dedicated operating stations still use the chassis's baseline crew accounting, but must explicitly fit the boss; changing seats cannot bypass a capacity or headroom restriction. Standard sidecars only provide 2 passenger load and therefore do not fit the boss in the POC.

Gorr is the proposed POC clan boss and starts at the standard truck's suitably enlarged gun station. Fiz drives and handles repairs. Brok remains the ordinary-sized claw-and-jaw boarder on the sidecar. This demonstrates the size difference without adding another character to the roster. Boss status is a role/body template within the Krag species; automatic growth on promotion and campaign leadership systems are future decisions.

## 2. Equipment and compatibility

Start with a weapon, sidearm/tool, armour, utility item and back-equipment slot. Jetpacks occupy the back slot. Bionic implants occupy anatomical sockets rather than a generic backpack inventory.

Check compatibility in the loadout screen: body size, harness fit, station clearance, required hands, carried mass and conflicting equipment. A pack may fit an open bed but not a narrow enclosed cab. These are declared fit rules, not unpredictable animation collisions discovered after commitment.

The POC needs a basic gun profile, a portable heavy-gun profile, basic melee, one repair tool, one jetpack, a crusher-claw strike and an iron-jaw bite. The claw wearer uses a compatible one-handed firearm or integrated support fitting rather than an impossible two-handed grip. Grenades, mines and shields remain later content. Heavy bionics and oversized guns are part of the initial personality, not merely cosmetic rewards to add at the end.

## 3. Jetpacks: proposed burst-jump model

Jetpacks should make height, gaps and boarding approaches useful. The starting proposal is a short powered jump from a valid launch location to a valid landing location. It is not indefinite hovering or a second vehicle movement system.

### First POC rules

| Parameter | Initial test setting |
| --- | --- |
| Action cost | 1 of the character's 2 actions |
| Fuel | 2 charges per encounter; 1 per jump |
| Recharge | No automatic in-battle regeneration |
| Horizontal reach | Up to 10 m |
| Positive height gain | Up to 5 m |
| Supported downward landing difference | Up to 5 m for the first implementation |
| Frequency | At most 1 powered jump per character activation |
| Persistent flight | None; every jump has an endpoint |

These are editable prototype values. Tune the jetpack as a vertical-access tool; it should not replace the bike for sustained travel. More powerful, heavier or quieter variants are later content.

### Validation and resolution

1. Verify the pack is equipped and functional and that the character has fuel and actions.
2. Check launch clearance, equipment fit and any need to leave a confined station first.
3. Validate range, height change and the entire swept flight path against solid geometry.
4. Reserve a landing footprint on stable, reachable terrain or a valid vehicle node.
5. Preview known reaction exposure, cover at arrival and any risk check.
6. On commitment, spend fuel/action, resolve reactions and then resolve arrival or failure.

A routine jump onto a clear stationary roof succeeds if legal. Do not add a random crash chance merely because the equipment is improvised. Moving-vehicle boarding, damaged equipment or a hazardous landing can require an explicit check.

Choosing the destination does not reveal concealed enemies. If an unknown occupant or reaction invalidates the arrival, use a defined failure rule rather than clipping entities together.

### Interruption and failure

The POC uses a small, explicit outcome set: successful landing, forced landing at the last validated reachable fallback, or a fall with height-based damage when no fallback exists. A fallback is found from the same trajectory and geometry; it is not a teleport to arbitrary safe cover. Reserve action/fuel once at launch and never charge them twice after interruption.

Pack damage that happens before take-off prevents launch and updates the preview. Damage during flight triggers the same interruption rules. A hazardous check should state the likely failure location or uncertainty region before commitment.

### Combat limitations

Flight is exposed: ground cover does not protect the character while they are above it, and known anti-air or normal weapon reactions can intersect the flight path. Landing does not grant automatic cover or a free attack. A character with a remaining action may attack from their resolved landing position.

No hovering fire or mid-air target selection is needed for the POC. Similarly, jetpack ramming, chain boosts and emergency mid-fall recovery are later proposals, not hidden requirements.

### Boarding with a jetpack

Target the same rails, decks and roof nodes as ordinary boarding. The pack provides approach reach; it does not bypass occupied positions, cab access or hostile crew. A moving target is evaluated at its current resolved position using the turn-based motion abstraction.

A jet-assisted board spends one jump action and one fuel charge. It does not additionally charge the ordinary approach action, but any subsequent climb, attack or hijack has its normal cost. The character carries forward remaining actions and cannot activate again in the same round.

### Why other traversal still matters

Stairs, ladders, ramps and cover provide repeatable access without fuel. Jetpacks offer a faster or less predictable approach but expose the user and compete with other back equipment. Some interiors have too little clearance. Important objectives still have a viable route for a gang without jetpacks.

## 4. Bionics: replacement and augmentation

**Confirmed user correction — 6 October 2026:** Nib bionics are lightweight **replacements, not upgrades**. Restore the ordinary function of the replaced anatomy without stronger grip, extra movement, better aim, built-in tools or another implant-granted capability. This supersedes the earlier draft's Nib enhancement examples. Krag upgrades and separately carried tools/equipment retain their own compatibility rules; numerical strain values remain proposals.

Bionics restore a wounded crew member's function. Krag variants may also specialise a character through a named equipment perk or elective upgrade; strain, compatibility, parts and recovery time make this an equipment decision. A Nib's restored function is the benefit of its replacement and does not imply an extra perk.

Installation is a between-battle Sawbones activity with real deployment downtime. Initial scenario equipment may be pre-authored, but earned wounds in a continuing run cannot be instantly cured by changing a loadout. The POC adds one part, one treatment place and a three-campaign-day fitting/recovery demonstration; it does not need surgery animation, item trading or a full economy. XP and selected perks remain during recovery.

### Species compatibility and implant burden

Krags are physically suited to heavy replacement machinery and have no assumed aversion penalty for it. Nibs' smaller, more fragile frames require explicitly lightweight parts. This is an anatomical limit, not a restriction on learning to drive, shoot or use a suitably supported vehicle weapon.

Prototype total implant strain is 8 for Krags, including the boss, and 2 for Nibs. Each Nib implant is lightweight and at most strain 1; heavy-class parts are forbidden regardless of spare capacity. A crusher claw uses 3 and is Krag-only; the iron jaw uses 1 but is also Krag-only. Brok's claw, jaw and reinforced piston leg total 7/8. A Nib may instead combine an ordinary-function replacement hand and replacement eye for 2/2, without grip or aiming upgrades.

Body-fitted entry servo replacements cost 1 strain in the draft tune. Krag versions may grant a named perk: a servo hand supplies Built-in Tool, while a servo leg supplies Assisted Step (+1 m ordinary foot Move). Nib versions restore ordinary function only. Both still need a free compatible socket, species-rated construction and recovery. Medical restorations count towards the same total: a Nib cannot exceed two lightweight implants by labelling additional parts restorative. Disabled installed parts still count. Ranks/perks do not increase these limits. [10-experience-wounds-and-recovery.md](10-experience-wounds-and-recovery.md) owns the exact item table, progression and timing rules.

### Proposed anatomical sockets

Begin the data model with left/right eye, left/right arm, left/right leg and jaw. The jaw socket is now included explicitly for the iron-jaw concept. Keep torso and neural sockets as extensions. Left/right is always the character's anatomical side, independent of camera direction.

| Implant family | Useful effect | Trade-off or restriction |
| --- | --- | --- |
| Servo hand / replacement arm | Restores hand function and provides Built-in Tool for repair/sabotage | Ordinary AP, repair charges, access and strain still apply |
| Powered arm | Improves a chosen physical task such as grip or boarding | More mass; does not grant extra attacks or universal accuracy |
| Tool arm | Enables efficient repair/sabotage interactions | Mechanical specialisation competes with heavy combat fittings |
| Servo leg | Restores walking and gives Assisted Step (+1 m ordinary Move) | Lightweight strain-1 part; strongest leg movement bonus only |
| Reinforced piston leg | Restores walking and gives Power Step (+2 m Move, +3 m Sprint) | Heavy Krag-only strain-3 fitting; recovery required |
| Braced leg | Better stability or resistance to being thrown | Reduced sprinting or more load |
| Optical implant | Better identification or a defined aiming benefit | Still requires line of sight; no vision through walls or hidden-state knowledge |
| Crusher claw arm | A powerful adjacent strike against exposed crew/components plus strong grip | Replaces a hand, restricts fine manipulation and two-handed weapons; attack spends AP |
| Iron jaw | A bite attack while hands are occupied at a supported/hanging position | Requires reachable exposed target and ordinary AP; not a free follow-up |
| Later neural/torso implant | A narrow specialised ability | Needs separate balance and art validation before inclusion |

These are candidate families subject to species/socket/strain validation. All additional abilities in this table apply to Krag upgrade candidates; Nib versions may restore the corresponding ordinary anatomical function only. The revised first POC features a Krag crusher claw and iron jaw, with light restorative Nib variants as loadout comparisons. A visibly wounded/replaced state still proves persistence. The heavy-bionic action rules and starting numbers are defined in [08-outrageous-machinery-and-weapons.md](08-outrageous-machinery-and-weapons.md).

### Functional benefits, bounded stacking

Resolve body values and learned/equipment perks, identify functions restored by completed functional replacements, combine compatible flat movement bonuses before unresolved structural multipliers, then enforce restrictions and caps. A replacement suppresses the applicable loss of function; it does not erase the character's injury history or charge both the penalty and its replacement indefinitely. Use the worked examples in file 10 as the modifier-order contract.

One socket holds one implant. Set caps for repeated bonuses and reject incompatible combinations in the loadout validator. No implant resets actions, grants infinite reactions or removes the need for a valid landing/boarding position.

For the POC, the powered grip arm adds 10 percentage points to genuinely risky grip/boarding checks, capped at 95%; it adds no bonus to shots or jump range. Clear automatic climbs remain automatic. The optical implant gives a small, explicitly displayed aimed-shot benefit, initially +10 percentage points capped at 95%, with ordinary line-of-sight and cover rules retained. These are test values, not canon.

Elective augmentation is now an explicit option: choose a compatible available part and pay the same fitting/recovery cost even for a healthy limb. The fixture can supply the part without a market. Implant abilities require the part to be functional and recovery complete; they do not cost XP perk points. Removing a healthy limb records an elective modification, not a fabricated injury or XP event.

## 5. Wounds, treatment and persistence

Separate immediate combat states from the lasting injury record.

| Layer | Examples | When it matters |
| --- | --- | --- |
| Current combat state | Health loss, downed, burning, grip impaired | Immediately, with clear tactical consequences |
| Active structural wound | Damaged leg: Move ×0.6, no Sprint, -15 points to risky boarding in the POC | Persists through debrief; low pain does not filter it |
| Persistent injury record | Damaged eye, lost limb, permanent scar | Survives the battle and reload |
| Treatment or replacement | Fitting, recovery, then functional prosthetic/implant | Blocks deployment while in treatment; completion restores declared functions while preserving history |

Combat should report the immediate effect concisely. Detailed treatment and implant choices belong in debrief/loadout rather than interrupting a boarding action with a surgery screen.

Zero health normally produces a stable downed character with no bleed-out timer. Fatal results are rare; the initial 2% first-incapacitation tune, recovery sling, vehicle escape and capture/rescue rules are specified in [11-campaign-events-rescue-and-retreat.md](11-campaign-events-rescue-and-retreat.md). Repeated waiting/damage cannot create fresh mortality rolls. A downed character does not automatically return at debrief.

Implants may later be damageable and field-stabilisable. For the basic POC, use functional/disabled equipment states instead of a second detailed health model for every screw and joint.

### External machines and advanced weapons

A Tin Can supports its own weapons around a Nib pilot; it is not an implant and consumes no bodily strain allowance. Its pilot retains existing wounds, equipment and AP. The machine cannot board vehicles, although a dismounted pilot can. Advanced Nib weapon proficiency and the first precision carbine are specified in [12-tin-cans-and-nib-technology.md](12-tin-cans-and-nib-technology.md).

## 6. Visual and modelling implications

Use modular body regions and stable attachment sockets. A character's left-arm replacement must remain on the left across all views, animation clips, equipment fits and saves. Jetpack harnesses must leave room for shoulder motion, and exhaust should clear the body and carried equipment.

Keep species silhouettes identifiable with and without gear: Krags retain the broad low-set head and heavy frame; Nibs retain their ears and smaller silhouette. Equipment should not depend on generic human proportions to work.

The generated concept sheets guide form, materials and modularity. They are concept references, not dimensionally authoritative blueprints. Authoritative scale, sockets, collision and asset acceptance belong in [07-art-direction-and-model-briefs.md](07-art-direction-and-model-briefs.md).

## 7. POC demonstrations

The player should be able to equip a jetpack, preview and reach a gantry, use a remaining action, and see the fuel count persist. The same roof must remain reachable by a slower ground route.

A character with the powered arm or crusher claw should show a different calculated risky boarding chance while using the same action rules as another character. Brok should also be able to spend an action crushing an exposed component or biting an adjacent opponent from a supported rail position. Those are mutually budgeted actions, not a free three-hit combo. A wound, its debuffs, XP, chosen perk, species-compatible replacement and remaining recovery days must survive a save/load. The first debrief/recovery fixture must show Brok unavailable until fitting and rehabilitation complete. No full campaign economy is required to prove those interactions.
