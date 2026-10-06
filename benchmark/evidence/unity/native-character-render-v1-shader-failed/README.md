# Actual full-character Unity render attempt: shader failure

PID 17372 closes native/guard 1 before capturing an image. All 339 frozen inputs matched before launch. Existing character materials import and all five native groom groups/data textures are built, but the authored RGB/diameter shader fails D3D compilation: `point` is a reserved HLSL token. Both key and fill also requested cascaded directional shadows, producing an atlas error. These are diagnostic implementation defects, not model-data failures.

The exact executed shader/C# source, readiness, raw logs and imported vertex-color alpha readback are preserved. No rendered character, native attachment, appearance or performance result is claimed. The next bounded revision renames the local shader variable and leaves only the key casting shadows; production projects remain untouched.
