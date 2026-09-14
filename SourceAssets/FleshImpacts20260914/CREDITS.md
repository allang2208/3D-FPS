# Flesh impact assets

Project-authored shaders in this folder; runtime materials in /Game/Weapons/GunplayFX/Impacts/Blood.
Texture dependencies: /Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Smoke_Wisp (8x8, alpha density)
and T_Droplets_A (3x2, blue silhouette). Existing imported source pack is unchanged.

Source: Realistic Starter VFX Pack Vol 2
https://www.fab.com/listings/ac2818b3-7d35-4cf5-a1af-cbf8ff5c61c1
Local Fab Library records previously identified this listing as acquired.
Keep the account's acquisition/license records; project use does not grant standalone
redistribution of the pack, exported source textures, or texture-bearing assets.
No purchase or new Fab download was performed for this implementation.

The source P_Blood_Splat_Cone is Cascade; it is not spawned per hit here. T_Splat's ring-like
mask and the pale RGB of transparent atlases are not used as blood color/opacity.
Small instanced cards and shared decal materials use the existing project's hard budgets.
Recreate mist/drops with Tools/AssetPipeline/build_flesh_impact_assets.py after restoring the pack.
Then run Tools/AssetPipeline/build_flesh_ground_v2.py for the accepted ground stain.
Only asset authoring/material compilation and necessary native build are part of this delivery;
in-game appearance and performance remain for the user to test.
