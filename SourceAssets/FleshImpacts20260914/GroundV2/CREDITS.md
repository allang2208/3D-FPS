# Ground blood V2

Original shader/layout; references the unchanged local Realistic Starter VFX Pack Vol 2
T_Droplets_A, using blue as mask from its 3x2 shape atlas. Source/license details are in
../CREDITS.md. No new download or purchase. Do not independently redistribute source textures.

DecalColor R carries shape variation; G carries world-time birth. Shared material interpolates
fresh dark red / low roughness toward dried darker blood / higher roughness over 12 seconds.
Lifetime fade remains controlled by the pooled decal component. No per-decal material instance.
Authoring only; user performs in-game visual/performance testing.
