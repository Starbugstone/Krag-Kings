# Actual Krag material comparison — export held

Both frozen native jobs completed with exit 0 and fresh guard markers. All six saved images were individually inspected: Front, Head and Eyes for the authored `fe15213d…` source and its `4387bd3f…` portable derivative. Camera positions, studio lights, exposure and color management match exactly. These are Blender source/material comparison images, not game-engine evidence.

The body pattern, armor color and facial/iris pigment transfer, but the baked eyes lose visible highlights and white reflections. The source authoring code sets an ocular coat (weight 1, roughness 0.065, IOR 1.376); the portable helper copies only the SSS, base IOR and specular defaults, omitting those coat controls. That is a concrete code-level omission consistent with the images. Direct saved-socket attribution is still pending; no render-difference magnitude or exact optical parity is claimed.

`materialTransferAccepted` is false. No five-variant or clip export has started from this candidate. Preserve the successful 104-map bake and this failed material comparison; repair only the relevant shader constants/portable metadata in a separate derivative, then inspect the affected views. Source anatomy, mouth, hand, jaw-overlay, clothing and concept likeness failures remain independent blockers.

Raw images, native logs, memory CSVs, recipe copies and inspection findings are retained with exact hashes. The parent has the next heavy slot; no extra rendering or export ran after this boundary.
