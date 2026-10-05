# Source and concept-art audit

5 October 2026 · [Project decisions](../PROJECT_CONTEXT.md) · [Realization plan](15-poc-realisation-plan.md)

All 14 supplied documents were read and all 10 original PNG sheets were visually inspected. This audit distinguishes what exists from what the POC must produce. New strategic concepts produced during planning are recorded separately in [18-strategic-concept-art.md](18-strategic-concept-art.md).

## 1. What exists

The workspace contains a substantial design specification and concept images. It contains no game source, engine project, editable 3D models, production rigs, animation clips, texture source projects, builds, or measured test results. The pack references an original `game-design-notes.md` that is absent from this workspace; its contents were not reviewed. No earlier conversation beyond the supplied pack is presumed available.

The strongest foundation is the relationship between persistent people, crew stations, vehicles, boarding, component damage, salvage, and visible consequences. The major production gap is a coherent, tested asset pipeline that can preserve the concept likeness while clothing, tattoos, armor, and complete limbs change.

## 2. Document-by-document disposition

| Source | Useful foundation | Required treatment for the investor POC |
| --- | --- | --- |
| [00 — overview](00-overview-and-campaign.md) | Turn-based mixed-scale combat; gang identity; salvage loop; setting proposals | Preserve pillars. Replace browser-first delivery assumptions. Keep final story, geography, public title, and campaign length open. |
| [01 — combat and vehicles](01-combat-vehicles-and-boarding.md) | Character-owned AP; chassis-owned movement; station graphs; boarding; control distinct from allegiance | Retain these invariants. Integrate collision, interruption, casualty recovery, and extraction as first-class work. Treat numerical costs as draft tuning. |
| [02 — characters and implants](02-characters-jetpacks-and-bionics.md) | Species traits, larger boss, hand/fit restrictions, jetpack, elective bionics | Extend partial-limb sockets to complete limbs. Add clothing layers, tattoo ownership, visible armor, and shared compatibility validation. |
| [03 — terrain and missions](03-terrain-missions-and-forts.md) | Vehicle lanes, infantry cover, height, alternative exits, wreck obstruction | Use a measured salvage map, not the diorama as a blueprint. Base building remains concept presentation. |
| [04 — UX and controls](04-ux-ui-and-controls.md) | Select → preview → commit, contextual actions, explicit risk, accessible markers | Add premium close-up squad customization, layered appearance controls, treatment preview, full Windows menus/settings and onboarding. |
| [05 — old POC scope](05-poc-scope-and-backlog.md) | Small roster, useful mechanics sequence, many good acceptance cases | Keep it as a mechanics reference. Placeholder presentation and optional character polish no longer satisfy delivery. Events, rescue, missiles and Tin Cans are not automatically playable requirements. |
| [06 — technical foundation](06-poc-technical-foundation.md) | Single authoritative state, pure preview, ordered events, seeded outcomes, versioned saves | Carry the architecture forward. Babylon/TypeScript, browser storage, Y-up export, GLB-only assumptions need replacement after the native engine comparison. |
| [07 — art briefs](07-art-direction-and-model-briefs.md) | Identity, handedness, preliminary scale, component pivots, fit checks | Preserve selected images. Add approved multi-view masters, modular topology, full-limb concepts, wardrobe/tattoo sheets, material standards, deformation and likeness gates. Old polygon budgets are not a quality ceiling. |
| [08 — machinery](08-outrageous-machinery-and-weapons.md) | Claw, jaw and wrecking-ball identity; clear AP and sweep constraints | Keep these signature actions in the proposed core mission. Missile art remains useful campaign presentation; playable missile content requires a separate scope decision. |
| [09 — Rusthook story](09-rusthook-narrated-playthrough.md) | Personality, humor, examples of relationships and consequences | Lore/tone reference only. No forced injury, dialogue, victory, turn sequence or campaign chapter. |
| [10 — progression and treatment](10-experience-wounds-and-recovery.md) | Learned versus equipment perks, anatomical function, treatment locks, idempotent XP | Implement the compact persistent loop. Extend compatibility/overlap to full limbs. Brok's exact history and three-day example are not a required scripted scene. |
| [11 — events and rescue](11-campaign-events-rescue-and-retreat.md) | Stable casualties, physical recovery, explicit abandonment, usable foot exit | Keep tactical casualty recovery and truthful loss accounting. Daily random events, rescue mission, emergency detachment and travel simulation remain outside the selected playable slice. Specify its bounded ending without promising an unavailable rescue button. |
| [12 — Tin Cans](12-tin-cans-and-nib-technology.md) | External Nib machinery and technology identity | No Tin Can in the original ten sheets and no model. A new barrel-shaped exploration is now in file 18; the user confirmed concept/integration-plan scope only for this POC. |
| [13 — relay story](13-relay-station-narrated-mission.md) | Further tone and examples of persistent identity | Lore reference, not an approved second mission or final plot. |

## 3. Visual audit of the original ten sheets

The three Krag sheets (01, 07, 10) are 1774 × 887 pixels. The other seven sheets are 1536 × 1024 pixels. They establish appearance, but their resolution and generated perspective do not define every production surface or manufacturing dimension.

| Sheet | Observed visual identity to preserve | Gap or conflict to resolve before modeling |
| --- | --- | --- |
| [01 — Krag](concept-art/01-krag-character-sheet.png) | Bald low-set head, broad heavy frame, amber eyes, small tusks, layered sandstone cracking; diagonal leather harness, dusty scarf, teal shoulder plate, trousers and strapped boots | Occluded shoulder/hip interfaces and unclothed body are missing. Separate armor, scarf, belt and clothing rather than sculpting one inseparable outfit. |
| [02 — Nib](concept-art/02-nib-character-sheet.png) | Adult wiry creature with muzzle, mottled sandy skin, pale hair, large furred fennec ears, goggles, dirty overalls and dexterous hands | Earlier text calls the face provisional. Current instruction makes this selected image the likeness target. Back-of-ear, hair/ear layering, skin under clothing, and light full-limb mechanisms need design. No extra human ears. |
| [03 — truck](concept-art/03-scrapjaw-truck-sheet.png) | Four substantial tires, teal two-seat cab, open scrap bed, bolted wedge ram, rails and rear ladder | Gun position differs between views; written forward-bed position preserves loading space. Cab controls must fit Nibs, and the gun station the boss, without rescaling bodies. |
| [04 — bike/sidecar](concept-art/04-bike-sidecar-sheet.png) | Ochre bike, exposed engine, spoked wheels, dusty saddle, distinct sidecar seat/cargo modules | Preserve rider-right sidecar. Scale with a Nib driver and Krag passenger/claw must be proven in a seated blockout; a human-sized-looking seat is not sufficient evidence. |
| [05 — equipment](concept-art/05-jetpack-bionics-sheet.png) | Twin-nozzle pack, padded harness, copper/steel mechanisms, actual replacement eye, articulated hand and lower leg | No complete arm/leg interfaces, no Nib-specific lightweight masters, no wardrobe collision variants. The pictured braced leg does not fully design the stronger piston-leg family. |
| [06 — terrain](concept-art/06-rusthook-terrain-kit-sheet.png) | Pale eroded stone, riveted teal steel, cloth awnings, industrial catwalks, tactile console and suspended engine | Attractive diorama, not a measured playable layout. Stairs, safety rails, landing openings, truck clearance and objective handling need a geometry pass. |
| [07 — heavy bionics](concept-art/07-crusher-claw-and-metal-jaw-sheet.png) | Anatomical-left oversized three-pincer claw, brass gauge, heavy shoulder support, actual mechanical lower jaw and cheek hinges | Written elbow replacement versus extensive upper-arm machinery needs one approved interface drawing. Jaw must open without scarf/tusks clipping; not a rigid face mask. |
| [08 — wrecker](concept-art/08-wrecking-ball-rig-sheet.png) | Continuous chain, industrial boom, flywheel, counterweight, enormous riveted ball, visible travel cradle | Ball scale differs strongly across deployed/stowed views. The old 1.3 m suggestion is a tuning hypothesis, not permission to shrink its signature silhouette. Resolve diameter, cradle, bed and swept volume together. |
| [09 — missile rack](concept-art/09-scrap-missile-rack-sheet.png) | Four different expressive missiles in a 2 × 2 rack, patched fins, teal truck, raised/travel poses | Need consistent sockets, launch clearances and emptied states for future gameplay. Existing sheet is enough to explain intent, not a completed runtime attachment. |
| [10 — boss](concept-art/10-clan-boss-and-krag-comparison.png) | Body visibly taller and broader, thicker neck/limbs, confident face, giant braced gun; same species as ordinary Krag | Boss is not a uniformly enlarged regular mesh. Full rear/side and unequipped forms missing. Gear in the concept is one possible loadout; bare body must retain identity. |

## 4. Cross-document conflicts and missing contracts

| Issue | Consequence | Resolution in the new plan |
| --- | --- | --- |
| Browser prototype versus native investor quality | Wrong export, performance and UI assumptions could become sunk work | Compare Unreal and Unity using one common scene and asset pack before locking tool versions and renderer. |
| Art deferred to P7 | A fun greybox could conceal unusable modular anatomy or poor likeness | Run character proof alongside mechanics from the start. Final art is a delivery gate. |
| Story examples embedded in scope | Brok's injury or relay mission could become accidental mandatory content | User-selected depot objective is now independent of the story. Other story events remain examples. |
| Partial-limb sockets versus full replacements | Duplicate anatomy, clothing seams, tattoo leakage and stacked bonuses | Hierarchical region ownership, mutually exclusive coverage, whole-limb concepts, and per-profile fit variants. |
| Clothing/tattoos almost unspecified | A static dressed model would fail customization | Dedicated wardrobe, armor and tattoo content manifests with in-engine combination tests. |
| Biological lore versus visual material | Uniform rock or generic human skin could lose the concept identity | Material studies and close-up review under neutral and desert lighting; preserve expressive living anatomy. |
| Boss/Nib/body fit | Single human rig and seats will visibly fail | Dedicated body profiles; shared semantic rig names where useful, profile-specific proportions, weights and pose corrections. |
| Heavy machinery silhouette versus navigation | Visually impressive equipment can intersect vehicles and invalidate paths | Approve equipment envelopes and station fit before sculpt detail, then test again after final import. |
| Final extraction versus loss terminology | Old file 05 calls withdrawal without objective a battle loss, while other text describes partial success | Store objective result and crew/asset outcome separately. UI can report “Primary objective failed; survivors recovered.” |
| Persisting captives with no playable rescue | A reduced POC could strand the player behind an inactive mission button | Show persistent captured/missing status and clearly bounded demo ending/restart; approve this POC boundary before implementation. No implied rescue release. |
| No full-limb item tune | New equipment could silently bypass Nib strain or double leg bonuses | Author and approve item definitions; retain species limits and strongest-leg-bonus rule unless deliberately changed. |
| Master for game versus merchandise | A skinned mesh with texture detail is not automatically a printable collectible | One approved design, separate runtime, marketing-render and fabrication derivatives. |

## 5. Art still required

Production needs consistent turnarounds and detail views for all three body profiles; naked-equivalent neutral anatomy with appropriate coverage; complete shoulder/hip replacements; species-fitted light and heavy bionics; alternative wardrobe and armor; tattoo motifs/placement zones; supported station poses; damage/recovery states; and environment construction pieces. New campaign, fort and map sheets explain the wider vision but do not substitute for these production references.

No unresolved silhouette should be “fixed” by a modeler quietly changing the brand. Present alternatives with the relevant concept crop and gameplay constraint, choose one, and version the approved master.
