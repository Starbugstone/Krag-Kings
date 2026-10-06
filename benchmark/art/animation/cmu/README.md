# Captured human motion reference

Original data from the [CMU Graphics Lab Motion Capture Database](https://mocap.cs.cmu.edu/), created with funding from NSF EIA-0196217. CMU's [FAQ](http://mocap.cs.cmu.edu/faqs.php) permits copying, modification and redistribution without requesting permission. This is CMU's stated permission, not a claim that these files are CC0. Exact download URLs, original-byte hashes and acquisition details are in `provenance.json`.

The repository keeps original ASF/AMC bytes without line-ending conversion. The accompanying AVI files are CMU's reference visualizations, not Krag Kings character renders. The locally authored parser follows CMU's linked ASF/AMC format specification and converts the supplied length units to meters. Captures use 120 samples/second.

The actual first study used subject104's neutral walk, frames212–360, and jogging frames91–191. It showed coordinated human motion but also noisy swing-knee behavior in the jogging clip. The second study retains that walking cycle and uses subject09's running frames35–123. Subject127's running take was inspected but starts stationary and accelerates late; it remains reference data only.

Retargeted clips remove linear horizontal root travel, preserve captured torso and limb motion, and fit the characters' existing skeletal proportions. Character cadence, foot contacts, carrying pose and species acting remain authored tuning proposals requiring actual mesh and engine review. CMU motion is a starting point, not artistic acceptance of the result.
