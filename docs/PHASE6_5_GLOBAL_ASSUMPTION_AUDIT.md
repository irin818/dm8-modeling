# Phase 6.5 global assumption audit — before fitting

Frozen with `configs/phase6_5_li_equivalence.json` before inspecting any Phase 6.5 computed result. Historical findings and the Li paper are known, so this is a transparent controlled comparison, not blind discovery. We will not tune parameters to make a positive surround appear.

1. Literature prior is a question, not evidence in these five flies. A positive ring alone is not a reproduction.
2. Temporal rules: C0/C1/C2 use all 40 updates; C3 uses one global lag chosen by total RF energy, without surround sign; S2 uses fixed lags 0–9. No per-fly or per-ROI best-surround lag.
3. Center and surround zones remain 0–1.5 px and 3–6 px. Center fit, trimming, alignment, and weighting are fixed above.
4. ROI is a technical observation; animal n=5. ROI-equal is morphology, fly-equal is conserved inference. Report both.
5. Native 40-lag and coarse 4×10 maps will be shown together. Peak lag selection is sensitive to data and is not a source-defined Li step.
6. NaN edge support, support counts, and distance to raw stimulus boundary will accompany any surround claim.
7. Response zscore changes ROI weights after aggregation even when the per-ROI kernel shape is invariant up to scale. RF post-zscore uses all temporal and spatial coefficients per ROI, an explicit assumption because Li does not specify axis.
8. Absolute physical wavelength, irradiance, and retinal angle are unresolved; digital stimulus agreement cannot establish physical equivalence.
9. Image registration, ROI masks, background, and neuropil provenance remain unresolved. These may dominate algorithmic differences.
10. Dataset information ceiling will be judged from sensitivity, five-fly agreement, spatial coverage, and provenance. More algorithms will not compensate for missing experimental records.
