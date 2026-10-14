V5 reconciled sphere-only patch

Reconciled against GodSpaceCore_V4_CurrentFormal_SourcePatch.zip SHA256 77c5ab595fe05f9c9193dee6d2f23561f025b074dc6b4bb0b048dab4818dbd16. Formal V4 HLSL exactly matches the baseline used for cloud comparisons.

For the authorized desktop executor: do NOT run the full V5 importer or any FBX installer. This patch modifies only the existing formal sphere parent material M_CoreStarfield_V4's audited MaterialExpressionCustom_0.code. All 11 custom inputs and their existing connections remain unchanged. All material instances, mesh slots, texture settings, gold shader/roughness, geometry and the altar remain unchanged. Existing V1 completion metadata cannot skip this direct-node patch.

The two new glow strengths are local HLSL constants 2.8 and 2.4, numerically identical to the Blender previews. No new graph pins are needed. Existing controls and five texture samples remain unchanged.

Run apply_sphere_only.py with APPLY_APPROVED=True only once the parent authorizes that exact edit. Prechecks stop for PIE, dirty packages/maps, unexpected parent/overrides, changed shader hash, changed input list, or changed known effective scalar parameters. The script saves only the sphere parent material, never the map. It has not been executed or compiled in UE by the cloud worker. Desktop executor should verify its installed UE API before running, retain standard asset backup, and confirm compile and reload.

After application: capture near/mid/far with unchanged original daylight/exposure. Verify gold, altar and scene settings unchanged; inspect streaming and exposure only if the surface remains unexpectedly black. Do not claim PIE validation; that requires separate authorization. Preserve source by replacing the formal source HLSL with Starfield_BlueGlow_V5_SamePins.hlsl in the same authorized workflow. Retain Starfield_V4.hlsl for rollback.

Cloud previews/package remain valid: the only difference from their V5 shader is declaring two constants instead of adding two external custom pins.
