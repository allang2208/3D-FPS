# Magic Arrow Rain — Cone V3

User request: all arrows start at the airburst point, spread as a cone into the targeting circle, fly twice as fast, and each produces green impact effects plus dust on contact.

Runtime: `FPSMagicArrowRain.cpp`, `MagicArrowRainTypes.h`, `ColdSteelMagicArrowRainModel.cpp`. The existing 28 destination samples cover the same 4 m horizontal radius, including the selected slope. Each arrow begins at `Flight.Burst`. Its diagonal trace stops on the first solid blocker. Impact position and surface normal are captured once; paths do not teleport through walls. Magic damage now uses a direct burst-to-body visibility route consistent with the new cone, retaining friendly filtering, body samples, one hit per target and one training award batch.

The fall interval is 0.125 s, half the previous 0.25 s. A blocker shortens that interval by the traveled fraction. Existing launch delays remain 0.10–0.30 s. Clear-ground contacts therefore occur at 0.225–0.425 s after the airburst. The single area damage event and one existing aggregate impact cue occur at the middle of the volley, 0.325 s. Damage amount, skill levels, cooldown, costs, guide-arrow flight speed and airburst V2 are unchanged.

Author: `Tools/Skills/build_magic_arrow_rain_cone_impacts_v3.py`. It saves only `/Game/Skills/MagicArrowRain20261026/NS_ArrowRainDust`. The full skill recipe applies V2 and then V3. Materials are read-only dependencies: the V2 pressure-front material, existing arrow glow, and existing Mantaflow rolling impact smoke.

Each contact has one 0.13 s green flash, one 0.19 s ring oriented to the hit normal, two 0.55–0.80 s smoke puffs, and three 0.16–0.28 s green chips. One pooled Niagara component receives up to 32 positions, normals and times. Normal 28-arrow peak is 196 particles; the slot limit caps it at 224. Slot selection is cached in a particle-spawn module, so update does not repeat the 32-way lookup. Particle alpha and smoke normalized age start at each contact time, and elapsed burst age is supplied for late presentation. No per-arrow Actor, Niagara component, dynamic light or sound playback is added.

`Before/` retains the prior owned impact system when the author first runs. Production receipts and build logs go to `Saved/MagicArrowRain20261026/ConeV3/`. The legacy vertical-path fixture expectation was updated to the requested common-apex cone; this does not mean that fixture was run. No new gameplay, preview, render, performance or network test is authorized by this production step.

Delivered 2026-10-26 at 23:01: both regular Editor and Game Development builds succeeded; the impact Niagara was compiled/saved and its authoring commandlet exited 0. No gameplay or visual test was run. This did not rebuild the packaging job that was already in progress when the user requested V3. Two unrelated compiler shadowing errors were resolved with local-variable-only renames (`ButtonSlot` / `BowComponent`), without reverting those modules' other changes.

2026-10-27 repository cleanup: pre-edit package backups moved to `trash/bow-skills-retired-20261027/SourceAssets/MagicArrowRain20261026/ConeV3/Before/`. Current assets and this upgrade recipe remain active.
