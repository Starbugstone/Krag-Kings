# Macroface numerical v3 — diagnostic only

No native source or render was produced by this calculation. It evaluates the exact saved regional Head Basis and all 17 facial targets (18 arrays including Basis), with the same volume field applied to each.

Blocking findings are retained in `numerical.json`: Volume-field Jacobian determinant <=0.10, Volume field collapses a local direction below25%, Morph-combination nonlinear error exceeds0.25mm Playful. The minimum sampled volume Jacobian determinant is -0.020102; exact globe/iris similarity error is below1e−15 m. Existing nearest opposite-lid point distances increase by the explicit1.12 scale; this is not proof of zero contact gap or self-collision absence.

Rejected: composing the proposed oral domain without coefficient amplification still introduces a negative transition Jacobian. Do not generate this candidate.
