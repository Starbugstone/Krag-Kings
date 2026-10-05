# Experience, wound debuffs and bionic recovery

Draft 0.5 · 4 October 2026 · [Pack overview](00-overview-and-campaign.md)

**Established:** crew gain experience that can unlock perks; wounds impose debuffs; replacing Brok's damaged leg requires downtime. Krags readily accept machinery replacing body parts and can sustain heavy implants. Nibs have more fragile bodies, cannot sustain those heavy replacements, and support only limited bionics. Every bionic implant supplies a useful equipment perk/ability as well as restoring any linked function; elective replacement of a healthy body part is allowed. Campaign time can generate events, and downed crew need recovery or a rescue mission rather than a bleed-out timer.

**Draft proposals:** every number, recovery duration, perk name and capacity rule below is a starting tune. These are fictional game rules. The [Rusthook narrated playthrough](09-rusthook-narrated-playthrough.md) demonstrates them; the character document owns core anatomy and combat compatibility.

## 1. Keep four kinds of progression separate

| Layer | Changes | Does not change automatically |
| --- | --- | --- |
| Experience and perks | Learned capabilities earned through missions | Body size, species limits, AP or injury history |
| Wounds | Physical function and relevant action modifiers | Earned XP, rank or learned perks |
| Bionics | Restores linked functions and grants a named equipment perk/ability | Every wound, species identity, learned perk points or all physical restrictions |
| Recovery | Deployment availability until fitting and rehabilitation finish | XP already earned or ownership of selected perks |

A veteran can become more skilled and less physically capable in the same raid. A replacement addresses its linked wound; it does not reroll the character into a healthy novice. Krags' enthusiasm for replacement parts removes no fitting or recovery time. Do not add an aversion, fear or morale penalty to a Krag simply for having machinery installed.

## 2. Experience awards

Award XP in the debrief, once per encounter instance, to participating crew who were recovered alive. Recovered means actually extracted from that encounter; they still need to finish the return journey before becoming available at the fort. A recovered downed character can qualify. Deployed characters must have completed at least one meaningful action: movement into the encounter, an attack on a hostile target, repair of genuine enemy/terrain damage, or an objective/support interaction. An unused deployment slot is not participation. Characters left at the fort, unrecovered characters and cosmetic spectators receive no XP in this initial rule.

| Award | XP per eligible character | Limit |
| --- | ---: | --- |
| Participated and returned | 1 | Once per encounter |
| Gang completed the primary objective | 2 | Shared by eligible returning participants, regardless of who used the console |
| Made a useful role contribution | 1 | At most once per character per encounter |

Maximum: **4 XP per successful mission**, or up to **2 XP on a retreat/failed primary objective**. No separate kill XP. Useful contributions include damaging a hostile character/component, successful enemy boarding, releasing/loading mission cargo, or repairing actual hostile/terrain damage. Driving the carrier through extraction with the objective cargo also qualifies. Each contributes to the same capped role award, not an additional category to farm.

Self-inflicted/friendly damage, repeatedly dropping and collecting an item, failed commands, and repeating an already-complete objective do not create contribution credit. No reward for receiving a wound. Reloading a debrief or replaying an animation must not award XP again. A new mission instance can award XP normally; a full fresh-run restart resets the roster rather than adding to it.

Retain an encounter-ID award ledger and contribution flags. Apply the mission result, XP and earned perk points in one persistent transaction. The first POC can use one battle and this debrief; it does not need an enemy respawn loop or campaign generator.

### Ranks and perk points

Prototype cumulative thresholds are **4, 10 and 18 XP**, each granting one perk point. XP is cumulative and is not spent. Crossing several thresholds grants each crossed point once. Implement only the first threshold for the basic POC; keep later thresholds as campaign tuning data.

Choose perks in the debrief or at the fort. A recovering character may choose a perk, but remains unavailable for deployment. Initial perks are shared training options, each purchasable once, with no respec required for the POC.

| Perk | Exact initial effect | Constraints |
| --- | --- | --- |
| Sure Grip | +5 percentage points to a legal risky boarding/grip check | No effect on automatic climbs, maximum range or invalid positions; final chance still capped at 95% |
| Measured Shot | +5 percentage points to a shot using a valid Aim token | Adds to normal Aim/optical effects before the final 95% cap; no free Aim or shot |
| Long Stride | +1 m to the character's ordinary on-foot Move allowance | Added before structural movement multipliers; no sprint, jetpack or vehicle benefit |

Perks do not grant free activations, extra chassis moves, pain immunity to Nibs, larger implant capacity or permission to ignore required hands. Later driving, repair and leadership perks should create similarly explicit choices; they are not prerequisites for this demonstration.

## 3. Wounds and debuffs

Distinguish current health, active physical impairment and the permanent injury record. Healing health does not clear a damaged limb. A visible scar can remain after its functional penalty is treated. Do not add a penalty to every cosmetic scar or make all wounds permanent stat losses.

| Example wound | Active debuff | Restoration boundary |
| --- | --- | --- |
| Damaged load-bearing leg — POC case | Ordinary foot movement ×0.6; Sprint unavailable; -15 percentage points to risky boarding/grip checks | Completed replacement restores this leg's function and removes these effects; unrelated wounds remain |
| Unusable hand/arm — later wound fixture | That hand cannot meet weapon, grip or fine-control requirements | Compatible replacement restores only declared hand functions; a crusher claw is not a precision hand |
| Damaged eye — later wound fixture | -10 percentage points to ranged hit chance | Treatment or a functional replacement linked to that eye restores the lost function |

The leg wound is tagged **structural**, so it affects Krags despite their low pain response. Brok can still use a safe, supported route to a stopped friendly truck if actual geometry and required supports permit it. Risky movement becomes worse, not secretly impossible. An unusable limb or invalid landing is a hard restriction and cannot be overcome by rolling 95%.

For the first slice, implement this one leg-wound definition and a deliberate test fixture that can emit its injury event. Do not script every Rusthook run to injure Brok. A broad hit-location, multi-injury and treatment catalogue remains later work; file 11 now defines the minimal rare-fatal/stable-downing result. The narrated run shows one possible outcome, not a guaranteed injury roll.

### Modifier order

1. Select body/species base values and learned perks.
2. Determine functions restored and equipment perks granted by completed, functional implants.
3. Combine compatible flat modifiers, including learned and implant movement bonuses, then apply unresolved structural multipliers; enforce hand/fit/action restrictions.
4. Clamp probabilities and produce identical preview/resolution values. Filter pain/fear causes separately through the species traits.

For movement, add learned and functional implant bonuses to the base Move, then multiply by active movement factors; keep fractional metres in simulation. Before replacement, Brok's base 10 m becomes 6 m with the leg wound, or 6.6 m with Long Stride. A restored piston leg grants Power Step, giving 12 m Move and 20 m Sprint without Long Stride. A remaining unrelated structural wound would still modify those values. Any unresolved no-Sprint restriction takes precedence.

For a risky board with otherwise neutral modifiers, base 70% plus Brok's claw 10 points plus Sure Grip 5 points minus the wound's 15 points gives 70%. After the replacement is operational, the same check is 85%. Apply relative speed, gap and height modifiers where relevant. A replacement never grants the wound's lost value twice.

Repeated application of the same wound event is idempotent. For this POC, only one active leg-wound modifier is supported; a repeated event does not multiply it again. Later multi-limb injury combinations need explicit definitions.

## 4. Species limits for bionics

Use both anatomical compatibility and a small **implant strain** budget. Strain is an abstract burden on the body, not cargo load, AP or kilograms. Krag acceptance is cultural and physical; Nib limits are structural, not cowardice or reluctance.

| Rule | Krag, including clan boss | Nib |
| --- | --- | --- |
| Total implant strain capacity | 8 | 2 |
| Supported implant construction | Light and explicitly Krag-rated heavy | Nib-rated lightweight only |
| Largest implant on one socket | Up to the item/body compatibility limit | Strain 1 maximum; heavy class always forbidden |
| Ordinary restorative prostheses | Body-compatible versions allowed | Lightweight Nib versions allowed |
| Attitude to replacement | Comfortable, often enthusiastic | No assumed emotional aversion; physiology supplies the limit |

No perk or higher rank increases these caps in the POC. The boss's greater size does not silently create extra capacity. Disabled but installed implants still occupy their sockets and count towards strain. Removing/replacing installed anatomy is a treatment task, not a way to temporarily toggle the loadout budget.

### Initial item compatibility

| Item | Strain | Species fit | Function |
| --- | ---: | --- | --- |
| Servo hand / tool hand | 1 | Separate Krag and lightweight Nib variants | Restores ordinary hand function and grants Built-in Tool: satisfies repair/sabotage tool requirement without holding a separate tool; AP, access and repair-charge costs remain |
| Servo leg | 1 | Separate Krag and lightweight Nib variants | Restores leg function and grants Assisted Step: +1 m ordinary foot Move |
| Optical enhancement | 1 | Species-fitted versions | Existing aimed-shot benefit; restores that eye if linked to its wound |
| Lightweight grip replacement | 1 | Species-fitted versions | Existing +10-point risky grip/boarding benefit; does not duplicate a same-arm claw bonus |
| Precision tool-arm candidate | 1 | Nib or Krag fitted version | Future repair specialisation; detailed ability remains deferred |
| Iron jaw | 1 | Krag only | Existing Bite action; low strain does not override species fit |
| Crusher claw | 3 | Krag only, heavy class | Existing Crusher strike and grip effects |
| Reinforced piston leg — Brok's POC fitting | 3 | Krag only, heavy class | Restores leg function and grants Power Step: +2 m ordinary foot Move and +3 m Sprint |

Brok's claw (3), jaw (1) and new piston leg (3) total **7/8 strain**. A Nib could use a lightweight grip arm (1) and an optical enhancement (1), reaching **2/2**. A third lightweight implant, including a servo replacement, is rejected. A heavy claw is rejected even if the Nib currently uses zero strain.

Entry-level servo replacements cost **1 strain** and grant the modest equipment perk stated above. Medical purpose does not bypass a Nib's limited capacity. A Nib may fit two lightweight implants in this initial tune, whether elected or used to restore a wound. At capacity, another replacement needs a compatible revised treatment/loadout plan. The edge case of a Nib requiring more replaced functions than this provisional allowance supports remains a later medical/retirement balance decision; do not silently allow heavy parts or pretend every multi-limb casualty is already solved.

External equipment is checked separately. A compatible jetpack or vehicle-mounted heavy weapon remains available to Nibs because its harness/mount distributes the load. It does not turn a heavy anatomical replacement into a safe Nib implant. Future powered exoskeletons require a separately designed system and cannot be used as an undocumented bypass.

### Elective upgrades and perk ownership

A healthy character can choose a compatible bionic replacement at the Sawbones. Preview the gained perk, lost hand/slot capabilities, strain, part cost and downtime. A prior injury is not a prerequisite and grants no discount in XP or free perk points. Record an elective modification event rather than fabricating a wound. The same three-day fitting/recovery rule applies initially.

Equipment perks require the relevant implant to be installed, recovered and functional. They cost no learned perk point, and stop when that implant is disabled or replaced; previously learned XP perks remain. A replacement for an injured limb both restores its linked function and grants the same equipment perk a healthy elective recipient would receive.

A disabled replacement also loses its declared anatomical function even when installed electively: a disabled leg uses the structural leg impairment, an unusable hand fails that hand's requirements, and a disabled replacement eye uses the eye penalty. Apply a missing function once, not once for the original injury and again for the broken implant. This need not fabricate a new injury-history entry.

For leg movement bonuses, use only the strongest functional leg-implant bonus for Move and Sprint, then add any learned Long Stride bonus. Two piston legs do not double Power Step. A servo leg and piston leg yield +2 m Move/+3 m Sprint, not +3/+3. Existing same-arm grip non-stacking and final probability caps remain. Perks never bypass recovery locks, invalid geometry, required hands or the two-action budget.

The first equipment comparison is a light servo leg versus Brok's heavier piston leg: both restore function, but the piston provides greater mobility at three strain. Item prices and supply rarity remain economy tuning; the initial fixture supplies the chosen part. Removing a healthy limb is an explicit player-selected treatment, never an automatic level-up event.

## 5. Installation and downtime

Use an integer **campaign day**, independent of combat rounds and real-world time. No browser timer, offline wait, account service or paid speed-up is involved. The player advances time through explicit rest or travel. Process elapsed days individually, with scheduled and random events able to interrupt; [file 11](11-campaign-events-rescue-and-retreat.md) owns that clock and its saved event state.

The initial Sawbones has one treatment place. Start treatment only with an available place, required part, compatible anatomy/budget and the character at the fort. Commit the part to the treatment once at start. The POC supplies one suitable replacement part; purchasing, crafting and prices are later economy work. Reject unavailable or incompatible treatment without consuming the item or time.

| Stage | Brok's illustrative timing | Availability and effects |
| --- | --- | --- |
| Wounded, treatment not begun | Day 0 | Can deploy with the stated leg debuffs if otherwise eligible |
| Fitting/operation | Day 0 → Day 1 | Unavailable for deployment; chosen part reserved/consumed once |
| Rehabilitation/calibration | Day 1 → Day 3 | Still unavailable; installation visible, functional restoration not yet released for combat |
| Ready | At Day 3 | Linked leg debuffs removed, implant perk enabled, injury/elective history and new model retained |

**Prototype total: three campaign days**, including one for fitting and two for recovery. Treatment does not complete just because a Krag tolerates pain. Attachment stability, physical healing and relearning the limb still matter in the fiction. The same three-day fixture can be used for a compatible lightweight Nib limb initially; differentiated durations are later tuning.

The part stays committed after the operation starts. The initial interface does not offer cancellation midway through surgery. A planned treatment can be dismissed before starting without cost. No extra injury or random failed operation is needed for this slice.

Actual elapsed time advances once per committed day phase, with event choices able to interrupt a multi-day request. Beginning treatment at day D makes Brok ready at D+3. Advancing one day leaves two; advancing two more finishes treatment. Reloading, opening menus, selecting perks or finishing a combat round advances no campaign time. The tutorial/test encounter starts a fresh run at day 0; its first return resolves to day 1, and Brok's treatment then runs from day 1 to day 4. The relative Day 0–3 table above refers to treatment start, not the start of the whole campaign.

A gang may wait all three days or take another expedition without Brok. An example one-day expedition advances his treatment by one day when that elapsed time is committed, not once on departure and again on return. Patients stay at the fort; becoming ready does not teleport them into an ongoing battle. Reserve crew is a later roster feature; the POC can deploy its remaining three characters where the fixture supports that roster, or simply let the player rest.

Advancing recovery time can produce helpful events, setbacks and new opportunities. The connected POC uses a small eligible event table and stops for decisions. It does not invent an unimplemented raid or automatically punish each rest day. Time spent on a slower foot return advances fort patients and uses the same event checks; returning crew cannot start surgery until physically back at the fort.

Low current battle health may be reset to the effective maximum for otherwise deployable crew when preparing a new POC encounter; this simplification does not clear structural wounds or treatment locks. A limb replacement does not heal unrelated wounds. Rare fatal wounds, stable downing without bleed-out, capture/rescue and foot recovery are now defined in file 11. Broader medical care and emergency defence with patients remain later campaign work.

## 6. Brok's worked debrief

Assume Brok began the Rusthook run with 0 XP, made a successful enemy board, survived with the leg wound, and returned with the engine recovered. Participation 1 + objective 2 + contribution 1 = **4 XP**. He reaches the first threshold and chooses **Sure Grip**.

He keeps the perk during treatment but cannot deploy. Start fitting the piston leg on return at campaign day 1; he is ready on day 4. His reserved/installed bionic strain becomes 7/8 once the part is committed, and the linked wound becomes restored only on completion. His permanent record still says that the leg was injured at Rusthook and replaced afterward. The new leg does not change his 10-health body template or two-action budget.

On his next deployment he has 12 m Move and 20 m Sprint from Power Step, the +5-point learned Sure Grip perk, and his existing claw/jaw abilities. The new implant both restores the leg and improves capability. He has become more experienced and mechanically augmented after three days of unavailable deployment.

## 7. POC implementation boundary and acceptance

Add a compact post-mission loop after combat works: one XP award transaction, first perk choice, one structural leg wound, species/socket/strain validation, one treatment slot, Advance day and persistent deployment availability. A loadout screen alone must no longer instantly cure an earned campaign wound. Initial scenario equipment and debug setup may still be pre-authored and should be clearly identified.

| Check | Expected result |
| --- | --- |
| Brok completes the example mission from 0 XP | Exactly 4 XP and one perk point; re-opening/reloading the debrief grants nothing more |
| Fiz repairs and drives the objective carrier | Can earn the same capped XP without a kill |
| A recovering Brok selects Sure Grip | Perk persists; treatment lock remains |
| Start treatment then advance 1 + 2 days | Unavailable after the first day; ready exactly at completion |
| Save/reload with two days remaining | Same day, end day, installed/reserved part, strain, wound, XP and perk state |
| Attempt to deploy a patient through UI or imported roster | Rejected by domain validation |
| Fit Brok with claw + jaw + piston leg | Accepted at 7/8; no duplicate arm/leg or wound bonuses |
| Fit a Nib with a heavy claw or third lightweight implant, including a basic restoration | Rejected, with species or strain reason; no resources consumed |
| Restore a Nib's leg with a fitted servo leg and spare capacity | Allowed at strain 1 with recovery; Assisted Step works; no heavy-part or capacity bypass |
| Electively fit a healthy Krag with a piston leg | Same downtime and strain; Power Step activates only on completion; no fabricated injury or XP award |
| Disable an elective implant | Its equipment perk stops; learned perks remain; unavailable replaced functions follow the implant definition |
| Disable a restoring implant | Its declared function is unavailable again; strain is not refunded; injury history remains |

These are narrow rule checks, not a requirement to build the full strategic campaign before testing a battle.
