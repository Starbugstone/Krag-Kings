# POC audio, music and character voice plan

5 October 2026 · [Realization plan](15-poc-realisation-plan.md) · [Decisions and acceptance](17-decisions-and-acceptance.md)

**Confirmed user requirement:** the POC includes music, sound effects and character speech, with distinct Krag and Nib personalities and quips. Audio is part of the finished playable slice. No music, recordings or sound implementation are delivered merely by this document.

**Confirmed voice direction:** English, using AI-generated voices for the POC. Krags are deep and gruff; Nibs are higher-pitched and speak faster. Nibs remain capable adults, and both races must be intelligible. Actor recordings may replace generated voices later if finances allow. No particular accent or generation provider has been selected; choose through auditions. Original music style also requires an audition. All dialogue below is proposed tone testing, not a final scenario or story script.

## 1. Sonic identity

The world should sound heavy, repairable and inhabited: loose metal, piston weight, rough engines, cloth, boots on grit, wind through industrial gaps and machinery with distinctive rhythms. Keep the oversized equipment memorable without turning each action into a prolonged gag. Sound should communicate control, contact, failure and consequence at the same moment as the rules and visuals.

Use the same physical language across foot gear, replacement limbs, vehicles and the workshop. A piston-leg character has an identifiable mechanical accent in their footsteps; a dead engine is audibly different from an idling one; an empty/disabled gun does not keep playing a ready loop. A Nib remains an adult person inside a Tin Can, not a separately voiced robot.

## 2. Music production

Audition short original treatments against actual concept art and an early gameplay capture. Proposed directions to compare are a sparse desert-industrial score, a more rhythmic scrap-percussion treatment, and a warmer character-led treatment with mechanical accents. These are audition briefs, not locked instrumentation or copied soundtrack references.

| Cue family | Function | Required behavior |
| --- | --- | --- |
| Title / identity | Memorable project theme without establishing final story | Clean intro, looping bed, short exit; suitable for build launch and presentation |
| Workshop / customization | Support close inspection and personality | Low distraction, long-form variation, room for preview speech and mechanical sounds |
| Tactical planning | Sustain concentration between turns | Sparse tension, no artificial urgency or loud loop fatigue |
| Tactical escalation | Reflect visible combat pressure | Layered rhythm/texture, musically aligned transitions; does not expose hidden enemies |
| Objective / extraction | Mark clear progress and urgency when actually present | Brief sting/layer, no premature victory while crew remain on the map |
| Debrief / recovery | Reflect outcome and continued gang identity | Distinct success/partial-loss treatment without melodrama or forced story beats |

Deliver full mixes, loopable stems, intros/outros and short stingers with documented tempo/transition points. Build a simple state-driven music controller. Visible encounter state and actual outcomes choose layers; rapidly selecting characters must not restart cues. Loading a checkpoint restores the appropriate musical state without replaying rewards or an entire victory fanfare.

Set final cue length and total minutes after audition and mission pacing tests. Approve music in the full mix with voices and combat, not only as a standalone track. Preserve editable session/source stems and recording/license records with the handoff.

## 3. Sound-effect manifest

| Group | POC coverage | Integration trigger |
| --- | --- | --- |
| Characters | Footsteps for ground/rubble/metal, cloth/gear, body impacts, stable downed, recovery dragging | Animation contacts matched to actual surface; domain state determines valid outcome |
| Bionics | Light servo, heavy piston, claw open/close/strike, jaw mechanism/bite, full-limb gait accents | Correct fitted/functional item and action; distinct material contact |
| Firearms | Basic firearm, heavy gun, mounted gun, mechanical handling, hit material, miss/ricochet only where allowed by visual result | Shot event and visible impact; no extra damage implied by audio |
| Truck / bike | Start/idle/rev, travel, tire surfaces, steering/brake, chassis creak, metal collision | Current resolved motion and animation; no false background movement while planning |
| Vehicle damage | Wheel failure, engine sputter/stop, mount disable, frame wreck, repair | One event per state transition; ongoing loops stop correctly |
| Wrecker | Winch start/load, chain tension, boom motion, ball contact, safe return/stow | Validated sequence; contact sound at first resolved impact, no repeated damage cue |
| Jetpack | Ignition, short thrust, airborne loop, cutoff, landing/interruption | Actual launch/fuel/outcome; hard stop on cancel or interrupted state |
| Objectives | Console actuation, engine release/hoist/load/secure, extraction confirmation | Committed objective stage; no sound on a cancelled preview that implies completion |
| Workshop | Garment/plate handling, tattoo UI, replacement preview, treatment start/completion | UI preview versus irreversible treatment clearly distinguished |
| Environment | Wind, distant creaks, fabric flaps, restrained industrial ambience | Zones and scene state; never reveals unseen tactical actors |
| Interface | Select, inspect, valid/blocked feedback, confirm/cancel, AP/end turn, save/load and settings | Short, consistent hierarchy; repeated hover does not chatter |
| Tin Can — future integration only | Distinct barrel resonance, Nib hatch/seat, locomotion modules, attached tools/weapons, damage and repair | Not a POC audio-production dependency: the user confirmed concept/integration-plan scope only |

Use variation pools and modest controlled pitch/volume differences where appropriate, without changing recognizable cues or producing comic chipmunk speech. Group concurrency so dozens of fragments cannot drown an objective cue. Keep stable identifiers linking each sound to its owning ability/item/component.

Author perspective layers for close workshop, normal tactical view and distant actions. Camera zoom must not make everything inaudible or turn distant guns painfully loud. Test a tactical listener strategy and limited attenuation ranges in engine; visible active-unit information may use a controlled foreground layer. Avoid presenting off-screen/hidden threats through spatial audio that the observation rules would conceal.

## 4. Race and character voice bible

| Voice aspect | Krags | Nibs |
| --- | --- | --- |
| Core personality | Fearless, hardy, delighted by combat and enormous machinery | Capable adult desert technicians; practical, quick-thinking and often impatient with bad engineering |
| Delivery | Deep, gruff voice; weight, confidence, economical words, dry literal humor and amused enthusiasm | Higher-pitched, faster speech; clear articulation, technical specificity, dry corrections and contained exasperation |
| Physical damage | Annoyance at lost function, determined exertion and physical impact | Alert practical response, vulnerability without childish squeaks |
| What to avoid | Constant screaming, fear/panic barks, mindless stupidity, repeated copied catchphrases | Helpless mascot voice, incoherent jargon, sneering at every ally, “small means infant” casting |
| Equipment relationship | Pride in louder/heavier tools and willing augmentation | Affection for functioning systems, lightweight bodily enhancements and externally supported machinery |

Species tone is a shared direction, not one identical voice for every member. Provisional roster characterization:

- **Gorr:** expansive boss confidence; appreciates a good weapon; fewer words carry authority.
- **Brok:** direct, physical and literal; satisfied by a machine doing exactly one forceful job.
- **Fiz:** seasoned mechanic; precise, protective of the gang's transport, dry corrections rather than constant anger.
- **Tikk:** agile, curious and technically confident; enthusiasm for clever solutions rather than sheer scale.

These are performance briefs to review, not final character biographies. Additional enemy voices may use the same race grammar while remaining distinguishable.

### Tone auditions — proposed short lines

| Situation | Krag example | Nib example |
| --- | --- | --- |
| Selected | “Point me at something.” | “What's the problem?” |
| Good boarding route | “That rail looks friendly.” | “Grip first. Boasting later.” |
| Heavy weapon ready | “Now that's a proper barrel.” | “Support locked. Try to keep it that way.” |
| Structural limb impairment | “Leg won't listen.” | “Joint's gone. Need a different route.” |
| Repair completed | “Still loud. Good.” | “Fixed. Please stop testing it with bullets.” |
| Engine loaded | “Heavy. Worth keeping.” | “Clamps set. We can leave.” |
| Recovery complete | “Better leg. Let's use it.” | “Calibration's done. You're cleared.” |

Do not record these as final until voice direction and script are approved. Quips must remain true to state: no “engine loaded” before a valid load, no “ready” while recovering, no celebration over an ally's fatality.

## 5. Speech content and runtime rules

Create a line manifest with line ID, speaker, race, trigger, condition tags, priority, repeat policy, subtitle, file, duration and recording status. Suggested initial coverage is roughly 25–35 short character-specific lines per friendly voice, plus a compact shared set of combat efforts/enemy responses. Final count follows the supported triggers and casting; this is a planning envelope, not a purchased session or locked script.

Cover selection, move/board acknowledgement, target/weapon support, action success/failure, objective progress, vehicle damage, repair, retreat/recovery, bionic inspection and return to duty. Essential tactical facts appear in UI text as well as speech. Infrequent banter may be tied to true visible combinations, such as an oversized gun beside a claw, but must not establish a new plot or force a conversation during time-sensitive input.

Use a central dialogue scheduler: one foreground line at a time, with critical gameplay information above optional quips. Set global/speaker/category cooldowns, no immediate line repeats, capped ambient frequency, and a mute/verbosity setting. Save recent-line history only as needed for continuity; reloading must not replay every event in the saved ledger. A stale queued bark is cancelled if the speaker is downed, extracted, no longer present or its factual condition has changed.

Barks do not block input or extend AP resolution. Subtitles identify the speaker, scale with UI settings and remain readable over the tactical scene. Nonverbal critical sounds receive a text/visual equivalent. Iron-jaw processing can add a restrained mechanical resonance while preserving intelligibility; retain clean masters. Lip/jaw motion must fit the actual jaw variant without detaching teeth or cloth. A Tin Can pilot uses the same Nib voice with optional intelligible radio filtering.

## 6. Recording and implementation pipeline

1. Audition AI-generated English race/individual voices against concept close-ups and action clips: deep/gruff Krags and higher-pitched/faster Nibs. Resolve accent and pronunciation direction from samples rather than assuming an accent.
2. Approve the performance bible and a small representative script including humor, functional injury, combat effort and quiet workshop delivery.
3. Select the AI voice tool and reusable voice profiles for consistent pronunciation, emotional range, direction/revision ability and intended production use. Record provider/model/profile versions and generation settings. Actor replacement is a future option, not a prerequisite for this POC. No voice impersonation or inferred actor casting is part of this plan.
4. Record/generate approved lines with line IDs and consistent session metadata; retain dry unprocessed masters and pickups. Set naming/pronunciation guidance for Krag, Nib, character and item names.
5. Edit breaths/noise judiciously, normalize consistently, apply variant processing, then audition in the mix. Keep game imports separate from source masters.
6. Hook cues through the event/observation layer and animation contact markers; connect subtitles, speaker priority and settings.
7. Test repetitions, overlapping combat, camera zoom, stereo/headphones, quiet speakers, scene changes, alt-tab and save/load. Capture a complete mixed mission and revise pacing.

Use the selected engine's built-in audio workflow for the comparison unless a concrete feature justifies middleware. Do not add a licensing/deployment dependency solely by habit. Source assets should remain usable if that decision changes.

### Later replacement with actor recordings

Keep line IDs, subtitles, speaker/trigger metadata and scripts independent of generated filenames or provider APIs. Ship reviewed audio files rather than requiring a live voice service during gameplay. Archive generation settings and clean masters for consistent pickups. A later actor performance replaces the audio asset under the same line ID, with duration, captions, facial/jaw timing and mix revalidated; gameplay code and save data should not depend on a particular recording length or synthetic voice provider.

## 7. Mix and acceptance

Separate master, music, effects, ambience and voice buses with saved independent volume controls. Duck competing audio gently for essential speech/objective cues; do not repeatedly pump the whole mix for flavor chatter. Offer a reduced-dynamic-range mode for ordinary speakers. Establish loudness and peak targets from the target playback tests, and verify no digital clipping, missing channels or broken loop seams.

| Check | Release expectation |
| --- | --- |
| Intelligibility | Required speech understood on headphones and ordinary speakers during the loudest supported action; subtitles accurate |
| Personality | Blind audition distinguishes the two races and four proposed friendlies without relying on pitch alone |
| State correctness | No barks or effects claim a cancelled action, dead speaker, hidden target, unavailable limb or unfinished objective |
| Repetition | Repeated selecting, long planning and mission replays remain tolerable; no rapid repeated line |
| Spatial stability | Camera zoom/rotation and offscreen actions do not produce abrupt loudness jumps or reveal hidden information |
| Synchronization | Contact and machinery cues align with actual animation/events, and disabled loops stop |
| Music | Transitions and loops have no clicks, abrupt resets or premature victory; no cue restart on every menu action |
| Reliability | Scene teardown, load/reset, pause, focus/device changes and mission endings leave no stuck or duplicate audio |
| Performance | Voice limits, streaming, memory and CPU meet the selected engine/hardware budget |
| Handoff | Editable sessions/stems, dry voices, final imports, cue/line manifests, subtitles and applicable usage records are included |

Audio participates in G1 integration trials, G2 jaw/face tests, G3 event hookup, G4 production, and G6 full-mix acceptance. It is not left until all visual work has finished.
