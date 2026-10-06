# Krag v9m neck composition and draped scarf

The read-only all-mesh audit has run. Its actual 70 portrait samples hit Body skin first on 40 mouth-area rays and Scarf on seven. The inner mouth itself is visible first on only one ray. This explains the cracked skin in the mouth despite the new dark inner lining.

The prepared source job removes only Body faces whose vertices are in the high Neck skin domain and strictly concealed inside the Head exterior. All Body vertices, shape coordinates and rig binds remain unchanged. It requires the 40 proved oral Body occlusions to resolve before continuing.

Scarf is then rebuilt as a broad asymmetrical wrapped sheet, with a low front edge, diagonal folds, unequal sag and rear/shoulder pins. A bounded 54-frame cloth simulation uses self-collision plus actual head, corrected neck, armor and harness colliders. The settled mesh is baked, given thickness and weighted to Chest/Neck. This is not an offset of the old stacked collar.

Generation and actual OpenMouth/profile/front/raised-arm reviews have not yet run. Neither a numerical ray check nor a completed simulation constitutes artistic acceptance. The complete Head neck is retained; final cinematic seam welding is not claimed. Shared assets and body-motion recipes remain unchanged.

The first actual v9m generation has now stopped before simulation/save: the neck composition clears all 40 original Body occlusion rays in memory, but one initial cloth contact requires 56.910 mm correction and exceeds the unchanged 55 mm bound. No v9m blend or render exists. The read-only diagnostic preserves that failure and records the actual offending vertex/collider contact before any pattern correction.
