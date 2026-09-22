# 5.8x42mm UI ammunition art

2026-09-22. User asked to design three 5.8mm tiers for the QBZ-191, following the same ladder as the existing 7.62x39mm LP / PS / AP, 5.56x45mm M193 / M855A1 / M995, .45 ACP FMJ / +P / AP and .357 MAG SP / JHP / AP sets. Code and written record first, **no image generation**; the tier pictures are placeholders.

Runtime paths are reserved and already referenced by `Content/ColdSteelData/ammo_types.json`:

- `Content/ColdSteelData/Icons/Ammo5820260922/58_dbp87.png` — green tier (DBP87)
- `Content/ColdSteelData/Icons/Ammo5820260922/58_dbp10.png` — blue tier (DBP10)
- `Content/ColdSteelData/Icons/Ammo5820260922/58_dbp191.png` — red tier (DBP191)

Each placeholder is a byte-identical copy of the caliber's existing runtime icon `Content/ColdSteelData/Icons/ammo_58.png` (256x256, 46,740 bytes, sha256 `2b35682371ebd233ae9468b675dcce0ca3f654d1575b6323d01aa75a624ae05f`). This is the caliber-correct stand-in, and it is exactly the picture the HUD and pouch already show for 5.8mm today, so nothing visually regresses — but all three tiers are the same image and it carries no tier backplate, so only the catalog-driven tier colours (`tier_name` / `tier_color`) and the printed names distinguish the three rows. Hash and status per file: `runtime-images.json`.

Note the resolution difference: this caliber's icon is 256x256 from the older generic icon set, while the 7.62 / 5.56 / pistol tier art is 1254x1254. Final 5.8 tier art should match the tier-art family (square, same camera and negative space), not the 256px stand-in.

## What the final set still needs

Replace the three PNGs at the reserved paths, keeping the file names so no catalog edit is needed. Follow [仅数值弹药的等级图标](../../skills/ue5-item-asset-workflow/references/numeric-ammo-icons.md): UI picture only, no three-view, no 3D package, no world pickup, no inventory cell. Tier assignment stays DBP87 green, DBP10 blue, DBP191 red, matching `ammo_types.json`. 5.8x42mm is a small-calibre bottleneck rifle cartridge — keep the case proportions close to the 5.56 set, do not reuse the pistol silhouettes.

## Shared generation prompt (not yet run)

Create a high quality photorealistic inventory icon for a fictional FPS game, matching the supplied existing ammunition icon's visual style exactly: a small worn cardboard ammunition box with open lid, rows of brass and copper cartridges, two loose rounds standing beside it and two lying in front, isolated product photography, three-quarter view from above, soft neutral studio lighting, crisp real paper fibers, restrained patina and natural metallic roughness, not cartoon, not overly shiny, no scenery. Square 1024x1024 composition with 10 percent safe margin. Opaque tier backplate, no floor scenery, no drop shadow. This is purely a 2D game inventory illustration, no diagrams or internal mechanisms. Keep consistent box proportions, camera, lighting, and cartridge proportions across the DBP87 / DBP10 / DBP191 set, and keep the visual scale and negative space of the 7.62x39mm LP / PS / AP set.

## Per-asset suffixes (not yet run)

DBP87: Variant DBP87, standard ball tier. Tier backplate and packaging in the green tier colour. Realistic 5.8x42mm short bottleneck rifle cartridge silhouette, copper/brass projectile with no tip marking. Clear cream stencil printing on FRONT of box, exactly two lines: '5.8x42 mm' and prominently 'DBP87'. No other text, no performance stats, no percentages. Generate this single DBP87 icon.

DBP10: Variant DBP10, improved-penetration tier. Tier backplate and packaging in the blue tier colour, otherwise the same box, cartridges and composition. Realistic 5.8x42mm case with an exposed steel-tip projectile as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '5.8x42 mm' and prominently 'DBP10'. No other text, no performance stats, no percentages. Generate this single DBP10 icon.

DBP191: Variant DBP191, new-generation high-performance penetration tier. Tier backplate and packaging in the red tier colour, otherwise the same box, cartridges and composition. Realistic 5.8x42mm case with a black-painted armour-piercing tip as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '5.8x42 mm' and prominently 'DBP191'. No other text, no performance stats, no percentages. Generate this single DBP191 icon.

Prompts deliberately avoid embedding the damage and penetration percentages: those numbers live in `ammo_types.json` and are shown by the UI, so a rebalance must not invalidate the artwork.

## Publication and recovery

The final PNGs stay local under the project asset-publication policy and are not publicly uploaded; the same boundary as the 7.62, 5.56 and pistol tier art applies. Restore the exact installed files from the host backup — random regeneration is not byte-identical recovery. When the real art lands, record its hashes in `runtime-images.json`, move the placeholder entries to generation history in `trash/`, and keep the reason each earlier attempt was superseded.