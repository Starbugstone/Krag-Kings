# Actual Unity terrain-coordinate and sand validation

The imported terrain originally sampled source `h(-UnityX,-UnityZ)`. Its measured initial heights were 1.290237 m at Krag X=-1.35 and .912832 m at Nib X=1.2/Z=.1. The first X-only correction matched one height but failed the strict slope-normal check by 4.84 degrees. That rejected build did not overwrite the previous executable.

Rotating only the imported terrain 180 degrees about Unity world Y preserves a positive determinant and gives the common scene `h(UnityX,UnityZ)`, equivalent to Unreal `h(UnrealX,-UnrealY)` after metre/centimetre conversion. Shared geometry, UVs and characters are unchanged. Four actual editor and packaged-runtime downward traces pass within .000463 m height and .205 degrees normal error.

Windows build `b5fa6342a69f462d8e2f6510ee0056e6`, shared fingerprint `07aec9123d923b67e4243380b6f0b283992aac70a9ec2c68bcd4865cce1202d1`, passes all 17 functional checks across seven variants, overlapping actions, facial/body corrective activation, dune movement and actual Krag discharge directions. Both guards exited 0. Seven unchanged character import settings were reused; changed source/settings still require import and all asset/clip checks remain active.

The included images show the actual 1080p Balanced runtime with the promoted [sand-v2 maps](../../shared/20261006-sand-v2-promotion.json). Grain is more visible and repetitive ridges are quieter. Character likeness, raised-arm skin and grip remain unaccepted. This is a functional/render review run, not a performance sample or native OS input check. Unreal's small capsule-floor clearance still creates a minor vertical framing difference; no final camera/quality parity is claimed.
