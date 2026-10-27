# Magic Arrow Rain — Airburst V2

User-approved scope: make the seed arrow's airburst readable before the single downward volley. No gameplay timing, damage, resource, sound, camera or aiming changes.

Author: `Tools/Skills/build_magic_arrow_rain_airburst_v2.py`. The full `build_magic_arrow_rain_assets.py` recipe also applies this upgrade after restoring its base assets. The incremental author saves only:

- `/Game/Skills/MagicArrowRain20261026/M_ArrowRainBurstCoreV2`
- `/Game/Skills/MagicArrowRain20261026/M_ArrowRainPressureWaveV2`
- `/Game/Skills/MagicArrowRain20261026/M_ArrowRainBurstSmokeV2`
- `/Game/Skills/MagicArrowRain20261026/M_ArrowRainMetal`
- `/Game/Skills/MagicArrowRain20261026/NS_ArrowRainBurst`

The Niagara system keeps its runtime path and pool. It contains one 0.20 s irregular core, one 0.28 s camera-facing elliptical pressure front (about 5.6 m visible width at radius 4 m), 16 smoke sprites (four inner / twelve outer) living 0.60–0.80 s, and ten radially aligned streaks living 0.18–0.26 s. Maximum spawn count is 28; no new runtime component, dynamic light, full-screen flash or camera shake is introduced.

`CoreMask.hlsl` and `WaveMask.hlsl` are original procedural masks with explicit transparent borders. The smoke material reads the existing approved Mantaflow density atlas `/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14` through `SourceAssets/ImpactSmokeCorrosion20260924/RollingSmoke.hlsl`. The source atlas and shared smoke material remain read-only, with their existing provenance and license. The dedicated unlit smoke material provides a dark center, a short green edge glow, and depth intersection fade; this is atlas-based smoke, not runtime fluid simulation.

The four inner smoke sprites fade between 0.12 and 0.30 s. Outer smoke begins thinning at 0.22 s. Core peak holds briefly, then decays from 0.055 to 0.20 s. Pressure-front opacity rises at 0.015–0.04 s and fades from 0.09 to 0.28 s. These lifetimes overlap the existing 0.10–0.30 s arrow birth interval without postponing the volley or its 0.40 s damage event.

Arrow material custom data slot 0 carries the initial 0.085 s head pulse. The original OBJ's U coordinate increases from the tail to the tip, so only U 0.78–0.94 and above glows. Trails start near each birth point and stretch to at most 2.6 m while falling. The existing 28 arrows and 0.25 s fall duration remain unchanged.

`Before/` contains exact pre-upgrade copies of already existing owned assets, captured once by the author. Never restore these across later changes without checking ownership. Compilation and save receipts go to `Saved/MagicArrowRain20261026/AirburstV2/`. This production step does not authorize or perform gameplay tests, screenshots, rendering or listening acceptance.

Delivery at 2026-10-26 22:04: Editor and Game Development builds succeeded; all five packages were compiled/saved, with Niagara `valid=1`. The asset commandlet returned 1 because project initialization logged an existing missing `GameFeatureData` scan rule before the author ran. Keep this process-level error distinct from the successful owned save receipt; no global GameFeature settings were changed. CPU Niagara easing uses the existing polynomial `smooth()` helper because VectorVM cannot compile the HLSL `smoothstep` intrinsic; pixel-material HLSL keeps the supported intrinsic. Gameplay and visual acceptance remain unperformed.

2026-10-27 repository cleanup: pre-edit package backups moved to `trash/bow-skills-retired-20261027/SourceAssets/MagicArrowRain20261026/AirburstV2/Before/`. Current assets and this upgrade recipe remain active.
