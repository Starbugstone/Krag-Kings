# Character, customization and merchandise production contract

5 October 2026 · [Realization plan](15-poc-realisation-plan.md) · [Original art audit](14-source-and-art-audit.md)

This is the production plan for fully realized squad models. It is not a claim that any sculpt, rig, texture, animation or printable model already exists. Asset counts below are proposed starting manifests, to be locked after visual review; the user-confirmed feature categories are mandatory.

## 1. Identity and clothing direction

The selected concepts define the visual target: premium semi-realistic 3D surfaces, exaggerated anatomy and machinery, pale sandstone, dusty fabric, rust, worn steel, restrained teal, brass and copper. Preserve silhouettes and recognizable faces before spending time on small scratches.

**Latest user direction:** Krags prefer armor and bionics, with little clothing because their hardy skin resists the desert. Make armor and mechanical replacements their principal equipment expression; retain recognizable anatomy and exposed cracked skin/tattoos where the selected armor leaves them visible. Minimal clothing does not mean lightly armored. Nibs have fewer bionic options and should express more variation through practical desert clothing and equipment. This is a deliberate species distinction; it is not a requirement to fully dress the Krags or cover the Nib's defining ears with generic helmets.

| Profile | Non-negotiable appearance | Production implication |
| --- | --- | --- |
| Regular Krag | Low broad head, small tusks, massive shoulders/arms, sandstone skin, amber eyes, assured physical stance | Original sculpt and skin materials; biological hands/feet must exist beneath replacement variants; minimal wardrobe exposes seams and tattoos |
| Boss Krag | Taller **and** broader body, thicker neck and limbs, commanding heavy stance; same species | Separate approved proportions and fit profile, not uniform scaling; dedicated seated/grip corrections and station bounds |
| Nib | Small wiry adult creature, sandy mottled skin, mature muzzle, exactly two large fennec ears, pale hair, goggles, dexterous arms | Separate anatomy/rig proportions, ear/hair shading and motion; more desert garments; lightweight bionics with distinct construction |

Use the old 2.2 m regular Krag / 2.75 m boss / 1.15 m Nib body as blockout proposals only. Approve measurements alongside the concept and fit scene. Do not distort proportions to meet a provisional numeric height or seat dimension.

## 2. Establish one approved source of design truth

For each profile produce front, back, sides and three-quarter views, a head sheet, hands/feet, neutral production pose, scale comparison and material callouts. Include views hidden under clothing and equipment. Establish consistent shoulder, elbow, wrist, hip, knee, ankle, eye and jaw boundaries.

Resolve the heavy claw's replacement extent, shoulder brace and sleeve fit in a diagram. New complete arms and legs need approved shoulder/hip interfaces and coherent machinery; extrapolating an elbow prosthetic upward without review is not sufficient. Define side-specific machinery rather than blindly mirroring text, gauges and asymmetric joints.

Approve each body uncluttered, then approve its clothing and bionic combinations. Retain the same face/body master for game and merchandise. Record image/master version, approved landmarks, palette, proportions, side conventions and unresolved details. Generated concept views provide direction; the approved turnaround resolves their contradictions once.

### Review stages

| Stage | Required review evidence | Reject when |
| --- | --- | --- |
| Silhouette/blockout | Matched concept view plus front/side/back/turntable; regular/boss comparison at equal camera distance | Generic human anatomy, wrong body mass, distorted Nib face/ears, weak boss distinction |
| Sculpt | Close head/hands/joints and full body without dramatic lighting | Surface detail hides wrong proportions or anatomy; replacement interfaces unresolved |
| Surface | Neutral studio and desert scene; skin/cloth/metal swatches | Plastic skin, uniform rust, overly smooth cloth, exaggerated bloom or color cast conceals material errors |
| Rig/deformation | Motion clips at supported extremes and close-up joint views | Collapsed shoulder/hip, visible gaps, scarf/jaw intersection, disconnected pincer/foot |
| Runtime integration | Actual game camera, customization close-up, all supported fit families, saved reload | Beauty-render likeness does not survive import, motion, LOD or loadout changes |
| Merchandise derivative | Render/physical prototype compared to approved master | Face, body proportion, tattoo or machinery identity changes without explicit review |

Exactness means fidelity to approved design landmarks, proportions, materials and character identity. Pixel equality to several inconsistent perspective drawings is not a meaningful acceptance criterion. The user approves the resolution of discrepancies; technical acceptance does not replace that art decision.

## 3. Anatomy and assembly model

Use stable semantic anatomy with parent/child coverage:

```text
body
  torso / neck / head
    eye_l / eye_r / lower_jaw
  arm_l / arm_r
    upper_arm / forearm / hand
  leg_l / leg_r
    thigh / lower_leg / foot
```

Full arm replacement owns upper arm, forearm and hand on its side. Full leg replacement owns thigh, lower leg and foot. A partial replacement owns only its declared descendants. A full limb and a separate part in one of its covered regions cannot both be installed unless a specifically designed modular assembly defines their relationship. Initial POC catalogue should use mutually exclusive full versus partial fits for predictable assembly.

Each item declares species, body-profile/fit variant, anatomical side, coverage, interface version, strain, supported functions, lost functions, ability/effect IDs, rig requirements, equipment envelope, clothing conflicts, visibility masks and replacement history. Visual meshes never infer these rules from their names or parents.

Biological regions are segmented at approved seams or hidden through authored section masks. Adjacent boundaries share positions, weights and shading intent. Do not leave a hidden whole arm deforming underneath a prosthetic or show an empty hole when a sleeve lifts. Give exposed interfaces a designed cuff/cap and coherent tissue/mechanical transition without inventing an unapproved gore style.

Keep the character ID, face, body profile, XP and injury history stable across swaps. The appearance recipe references content IDs and parameters, not engine object addresses. Save schema versions cover anatomy and material-layout changes, with explicit migration or rejection.

## 4. Clothing and visible armor

Clothing is separate skinned/attached geometry with authored coverage and fit variants. Proposed slots: lower-body garment, footwear, torso layer, neck/shoulder cloth, belt/utility, head/eye accessory and left/right armor pieces. Not every profile needs every slot or option.

Krags use a minimal clothing foundation of trousers/waist coverings, boots, belts, harnesses and a modest scarf. Armor plates and bionic fittings provide their main loadout variety; armor coverage follows the actual equipped pieces. Avoid adding cloth layers merely to increase cosmetic count. Nibs can vary overalls, desert trousers/tops, wraps, scarf, light outerwear, gloves, boots, goggles and utility equipment. New designs must retain the concept silhouette and adult mechanic identity.

Separate cosmetic clothing from armor values. Every armor item has a visible corresponding mesh and explicit gameplay definition; unequipping it changes both. Do not introduce invisible statistical armor or a paid-looking cosmetic catalogue. Keep color controls within authored material masks so metal corrosion, seams, buckles and bare skin are not recolored as fabric.

Author a layer ordering and occlusion map: body → underlayer → main garment → outer garment/armor → belts/attachments, with specific exceptions recorded per item. Mask only covered skin, never a joint that becomes visible in motion. Include shoulder/hip cutouts and rolled/cut sleeves/trousers for replacement limbs. Boots and gloves must not render over an incompatible mechanical foot/hand; supply an approved fit variant or show a clear incompatibility.

Harnesses and shoulder plates must clear jetpack straps, claw supports and ear motion. Cloth simulation is optional secondary presentation; an authored, stable fit must remain correct when simulation is disabled. Avoid making cloth physics responsible for hiding intersections.

### Proposed finite cosmetic manifest

| Content family | Proposed production floor | Purpose |
| --- | --- | --- |
| Krag clothing | Concept-matching base pieces plus one alternate minimal outfit, fitted to regular and boss profiles | Prove real garment swaps while keeping exposed anatomy dominant |
| Nib clothing | Concept outfit plus two coordinated desert-equipment outfits, built from compatible separates | Give Nibs richer clothing expression without disguising identity |
| Armor | One concept-derived kit and one alternative set of pieces per supported profile; empty state where appropriate | Demonstrate visible equipment and compatible layering |
| Colors | Authored fabric/paint masks with a compact palette; preserve underlying weathering | User-controlled identity without arbitrary material failure |
| Tattoos | Proposed eight original motifs, body-region placement, rotation/scale and approved ink colors | Demonstrate identity on visible skin; no imported user artwork needed |
| Squad identities | Four proposed friendly identities; three enemies reuse approved species rigs with deliberate visual variation | Avoid seven completely separate production pipelines while keeping the squad memorable |

These counts are a scope proposal, not approved final wardrobe designs. Record exact mesh/fit counts after G2; a “single outfit” can require several body and prosthetic variants.

## 5. Tattoos

Create original authored motifs that fit the game's identity, then approve a placement sheet on both species. Do not invent faction insignia or final lore through tattoos. A small visual vocabulary can support several placements without making every character look stamped from one texture.

Use skin-bound UV/region coordinates and an authored mask/compositing approach that remains attached during deformation. Preserve skin cracks, pores, roughness and shading beneath pigment. Bound placement/scale to supported skin zones and show the actual result while editing. Support undo/reset in the customization interface.

Tattoo records include design, anatomical region/side, region-local transform, color and layer order. Avoid mirrored UV regions for independently customized left/right skin. Prevent projection through the body, onto another limb, onto clothing or onto a replacement. Bake/cache the supported layers when appearance changes if needed; do not rebuild textures every frame. Cache invalidation includes UV/content version and all tattoo parameters.

For a replaced limb, retain the original tattoo record in character history but omit it on the mechanical region. A surviving upper-arm tattoo remains when only the forearm is replaced. A full-arm replacement hides the whole side's skin artwork. Test forearm/upper-arm boundaries, joint bending, LOD changes, clothing removal and reload.

## 6. Bionic catalogue and fit

The confirmed categories are partial arms/hands, partial legs, eyes, jaws, complete arms and complete legs. Support anatomical side explicitly. A mirrored socket name alone does not create a valid left/right visual or functional variant.

| Family | Required design/implementation |
| --- | --- |
| Grip/tool forearm-hand | Actual replacement and functional hand, sleeve/cuff variants, tool/weapon grip checks; lightweight Nib construction |
| Servo/braced lower leg | Knee interface, ankle/foot articulation, trouser/boot fit, seated and gait corrections |
| Reinforced piston lower leg | Heavy Krag silhouette and load-bearing motion; distinct from the lighter restoration |
| Optical replacement | Fits and follows eye/head, retains lid/muzzle identity, changes the actual eye region |
| Iron jaw | Krag lower-jaw replacement with cheek hinges, teeth and expressive motion; scarf/tusk clearance |
| Crusher arm/claw | Anatomical replacement, articulated pincer, load brace, hand-function restrictions and attack reach |
| Complete arm | New shoulder-to-hand assembly with coherent shoulder motion, chest/armor clearance and distinct light/heavy versions |
| Complete leg | New hip-to-foot assembly with hip clearance, seated compression, stance, foot contact and cloth variants |

The existing heavy claw/jaw restriction remains Krag-specific. Nibs have fewer lightweight options; full-limb support does not imply they can wear every Krag mechanism. Final strain and full-limb item effects are unresolved design data. Validate the full resulting assembly, count replaced functions once, preserve the strongest-leg-bonus convention unless deliberately changed, and do not let a full arm also receive a separate grip bonus from nonexistent biological fingers.

Fit both Krag profiles with authored variants rather than silently scaling hardware through body proportions. For Nibs, design slender mechanisms with appropriate interfaces and exposed machinery scale. Full arm/leg capability means those categories are playable; it does not establish unlimited simultaneous replacements or remove species limits.

A healthy elective replacement follows the same fitting/recovery rules as a restorative one. Newly selected gear in the workshop must not instantly erase an earned wound. Provide a clear before/after inspection, parts/strain summary, lost/gained functions and downtime before committing.

## 7. Sculpt, topology and materials

1. Block out approved proportions and test silhouette, body bounds, seat/door reach and equipment envelopes.
2. Sculpt clean primary and secondary anatomy, facial planes, fingers and joint structures; resolve interfaces before tertiary cracks and wear.
3. Build editable clothing patterns/forms and hard-surface bionics as separate source objects. Model real pivots, joints and supported attachment chains.
4. Retopologize for deformation, controlled seams and supported modular boundaries; retain high-resolution sculpt masters.
5. Lay out UVs with consistent texel density, stable material/region masks and independent tattoo zones. Bake normals and supporting maps with documented tangent settings.
6. Author layered textures: skin/pigment, fabric/weave/dirt, leather/edge wear, painted metal/chips/rust, brass/copper and optical parts. Use meaningful roughness variation; dirt must not flatten every material to brown.
7. Rig and weight, then iterate on corrective shapes/fit variants from actual movement tests.
8. Export, rebuild/verify materials in the chosen engine, compare with the master and create LODs from the approved runtime result.

Blender is a suitable editable source hub; specialist sculpt/texturing tools may be used if production selects them. Preserve source layers and a reproducible export process regardless of tool. Do not depend on an offline material node graph transferring perfectly into either engine.

No hard polygon or texture ceiling is approved before the engine/hardware proof. Allocate detail by visible importance: face, fingers, silhouette, mechanical articulation and close-up materials first. Test 4K-class hero source/runtime maps where justified, alongside lower-resolution variants, rather than assuming every object needs the largest texture. Log actual VRAM, texture residency, material passes, bones and draw calls. Preserve higher-resolution masters independently of runtime budgets.

## 8. Rig and animation contract

Use a shared semantic naming scheme, with profile-specific rest proportions and bind poses. Decide compatible Krag/boss skeleton structure from actual tests; Nib anatomy should not be forced into an unsuitable human or Krag rig. Retargeting is a starting tool, followed by per-profile correction.

Provide main deformation bones plus approved twist/shoulder/hip corrections, eyes/jaw, Nib ears, mechanical pincer and joint controls. Clothing follows compatible deformation. Mechanical assemblies need explicit drivers for pistons/hinges without unpredictable stretching. Weapon and station alignment use authored contact targets and controlled IK; the resolver still owns actual position.

| Animation group | Minimum coverage |
| --- | --- |
| Identity/inspection | Breathing, idle variants, Krag eager combat stance, boss weight, Nib alert mechanic behavior, close facial/ear/jaw reactions |
| Foot travel | Walk, faster travel, starts/stops/turns, stairs, uneven support, bionic and wounded variants |
| Vehicle | Nib driving, boss gunner, regular Krag sidecar, passenger and supported rail poses, mount/dismount, station transfer |
| Combat | Aim/fire/recoil by weapon support, melee, crusher, supported jaw bite, brace, impact, downed |
| Traversal | Climb/board, hanging support, jet launch/flight/landing and interrupted landing |
| Interaction | Console, repair, loading/handling, recovery sling attach/drag/release |
| Recovery | Injured inspection/limp, fitted but recovering presentation, ready mechanical gait |
| Speech | Short race-appropriate facial/jaw motion for actual barks, including iron jaw; captions and audio timing remain independent of AP |

Every clip family has tests for biological, partial and whole replacement states, heavy weapon, armor and relevant cloth. Start from shared actions but author enough variant motion to convey mass and fit. A complete lower-body machine assembly cannot simply inherit a foot slide from the biological walk.

## 9. Asset validation and quality gate

Verify scale/orientation with a known-size axis asset; joint names/rest transforms; weights and zero unweighted vertices; sockets; stable material slots; normals/tangents; seams; required texture presence; bounds; LOD transitions; and collision/fit metadata. Use deterministic import settings and stable content IDs.

The visual test scene must include neutral lighting, desert daylight, covered/shadow lighting, workshop close-up, the tactical camera and every supported station. Walk, sit, aim, board, hang, bite, crouch where supported, drag a casualty and use the jetpack. Validate tattoo survival, cloth masking, side correctness, full/partial overlap rejection and persistence.

Automate legal/illegal loadout enumeration and data checks. Exhaustively inspect the small set of dangerous contacts (jaw/scarf, shoulder/claw/sleeve, hip/trouser/full leg, hand/weapon, ear/headwear, pack/harness and seat/big body). Use systematic pairwise sampling for remaining combinations, supplemented by every canonical outfit and extreme supported pose. This reduces omissions; it is not a proof that every possible animation frame is defect-free.

Art acceptance requires no noticeable clipping, joint gaps, float, identity drift, shimmer or LOD popping at agreed inspection/gameplay distances. Record permitted minor distant artifacts explicitly; do not silently redefine “finished” when defects appear.

## 10. Merchandise derivatives

One approved design master produces three related outputs:

| Output | Purpose and work |
| --- | --- |
| Runtime model | Deformation topology, modular parts, efficient materials/LODs, engine rig and verified performance |
| Marketing/print render master | High-resolution sculpt/textures, approved poses, consistent lighting/color, transparent/background variants and composition-specific renders |
| Collectible fabrication derivative | Approved pose, physical joins/keys, manufacturing splits, thickness/support and assembly requirements defined with the chosen producer |

A normal map's skin cracks or embossed tattoo do not automatically exist as printable geometry. Translate details deliberately at the selected physical size. Do not thicken ears, tusks, pincer fingers or chains so much that identity changes without review. A printable statue does not need the game's live clothing rig; it still derives from the same design and selected loadout.

Figure scale, material/process, pose, articulation, part count and manufacturing tolerances remain questions for the merchandising stage. Plan a prototype and comparison review; do not advertise fabrication readiness before those choices and checks exist. Printed artwork needs final dimensions, resolution, color profile and vendor proofs. Store motifs and palettes separately from rendered shots so approved tattoo/clan graphics can be reused cleanly.

Retain design provenance, source versions and the rights/license records for any commissioned or third-party contributions as part of the asset manifest. The current game POC and marketing master do not by themselves constitute a manufactured product.
