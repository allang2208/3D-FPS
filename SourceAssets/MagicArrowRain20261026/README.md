# Magic Arrow Rain authoring sources

Owned destination: `/Game/Skills/MagicArrowRain20261026`.

- `magic_arrow_rain_cold_steel.png`: original AI-generated icon, based on the project's existing cold-steel skill frame reference; copied to `Content/ColdSteelData/Skills/`.
- `SM_ArrowRain.obj`: original procedural mesh. Centimeters, +X forward, arrow tip at origin. Simple metallic shaft/head and three fins; gameplay collision is independent of this cosmetic mesh.
- `S_ArrowRainRelease.wav`: CC0 artisticdude Battle Sound Effects `Bow.wav` and `swish_3.wav`, mixed and filtered. Inputs retained at `SourceAssets/HeartPiercingArrowAudioCandidates20261026/Sources/` with that batch's source/license records.
- `S_ArrowRainBurst.wav`, `S_ArrowRainImpact.wav`: original synthesized noise/transient cues, offered under CC0.
- `sources.json`: source summary. Three output cues are stereo PCM 24-bit at 48 kHz.
- Pre-edit copies have moved to `trash/bow-skills-retired-20261027/SourceAssets/MagicArrowRain20261026/Before/`; the archive manifest preserves hashes. They are not active authoring inputs and must never overwrite later shared-source edits.

Rebuild sources with `Tools/Skills/prepare_magic_arrow_rain_sources.py` (NumPy, SciPy, SoundFile); preserve the icon alongside it. Build/save UE assets using `Tools/Skills/import_magic_arrow_rain.ps1`. This script obtains the shared UE authoring mutex and runs a headless commandlet. It only writes the owned skill directory, and does not play the game or render a preview.

Niagara uses project-owned copies of NiagaraExamples `NS_Explosion_Small` / `NE_Core`, plus the existing `M_RollingImpactSmoke` from `/Game/Fluids/ImpactSmokeCorrosion20260924`. These parent resources remain read-only. Their original project license applies; this directory does not relicense third-party assets.

Airburst V2 uses the dedicated core, pressure-front and smoke materials in [AirburstV2](AirburstV2/README.md). Its incremental author only updates five owned assets. The full recipe reapplies V2 after base restoration, so rebuilding the skill does not revert the stronger burst. Ground impact continues using its existing shared smoke material.

[Cone V3](ConeV3/README.md) changes the volley to a common airburst apex and a 0.125 s fall interval. Its incremental author replaces only the ground-impact Niagara system with individually timed, surface-oriented green impacts and dust in one pooled batch. The full recipe applies this after Airburst V2.

[Visibility V4](VisibilityV4/README.md) thickens the falling green trails and keeps arrowheads bright throughout their fall. A stronger core, paired pressure fronts, larger rolling smoke and longer radial streaks replace the V2 airburst layers. Its dedicated trail and blast materials preserve the held-arrow flow and Cone V3 surface rings. The full recipe applies this last; the incremental background entry is `Tools/Skills/import_magic_arrow_rain_visibility_v4.ps1`.

The two one-time `integrate_magic_arrow_rain*.py` source-edit recipes have moved to `trash/bow-skills-retired-20261027/Tools/Skills/`. Do not rerun them; current compiler fixes and refinements are in the real source. Asset reconstruction still uses the retained authoring chain.

The 2026-10-27 dexterity/intelligence formula is owned by the current `skills.json`, `MagicArrowRainTypes.h`, definition loader and `MagicArrowRainStats()`. See `Docs/Skills/magic-arrow-rain-dex-int-20261027.md`. It does not require rebuilding the icon, meshes, sounds or Niagara assets; the one-time integration scripts must not restore the old magic-attack coefficients.

The initial delivery had no tests. The user later requested a review: 51 isolated native cases and 6 source checks passed after fixes; see `Docs/Skills/magic-arrow-rain-review-20261026.md`. No rendered gameplay, listening or multi-process network acceptance was performed. See `Docs/Skills/magic-arrow-rain-20261026.md` for controls and initial tuning.
