# 5.56x45mm UI ammunition art

2026-09-21. User asked for the 5.56 tier set M193 / M855A1 / M995 with the same effects as the existing 7.62x39mm LP / PS / AP set, and asked for code plus written record first, **without generating images**. No picture has been generated or edited for this set yet.

Runtime paths are reserved and already referenced by `Content/ColdSteelData/ammo_types.json`. They currently hold placeholders:

- `Content/ColdSteelData/Icons/Ammo55620260921/556_m193.png` — green tier
- `Content/ColdSteelData/Icons/Ammo55620260921/556_m855a1.png` — blue tier
- `Content/ColdSteelData/Icons/Ammo55620260921/556_m995.png` — red tier

Each placeholder is a byte-identical copy of the existing caliber icon `Content/ColdSteelData/Icons/ammo_556.png` (1254x1254, 1,590,709 bytes, sha256 `e716b0005397a61ed9e87caa0dcb4439297026c1ecc251bbaa1836112de6f259`). It is caliber-correct stand-in art, not the final tier artwork: it carries no tier backplate, so only the catalog-driven tier colours (`tier_name` / `tier_color`) distinguish the three rows today. Hash and status per file: `runtime-images.json`.

## What the final set still needs

Replace the three PNGs at the reserved paths, keeping the file names so no catalog edit is needed. Follow [仅数值弹药的等级图标](../../skills/ue5-item-asset-workflow/references/numeric-ammo-icons.md): UI picture only, no three-view, no 3D package, no world pickup, no inventory cell. Tier assignment stays M193 green, M855A1 blue, M995 red, matching `ammo_types.json`.

## Shared generation prompt (not yet run)

Create a high quality photorealistic inventory icon for a fictional FPS game, matching the supplied existing ammunition icon's visual style exactly: a small worn cardboard ammunition box with open lid, rows of brass and copper cartridges, two loose rounds standing beside it and two lying in front, isolated product photography, three-quarter view from above, soft neutral studio lighting, crisp real paper fibers, restrained patina and natural metallic roughness, not cartoon, not overly shiny, no scenery. Square 1024x1024 composition with 10 percent safe margin. Opaque tier backplate, no floor scenery, no drop shadow. This is purely a 2D game inventory illustration, no diagrams or internal mechanisms. Keep consistent box proportions, camera, lighting, and cartridge proportions across the M193 / M855A1 / M995 set, and keep the visual scale and negative space of the 7.62x39mm LP / PS / AP set.

## Per-asset suffixes (not yet run)

M193: Variant M193, standard ball tier. Tier backplate and packaging in the green tier colour. Realistic 5.56x45mm short bottleneck rifle cartridge silhouette, copper/brass projectiles with no tip marking. Clear cream stencil printing on FRONT of box, exactly two lines: '5.56x45 mm' and prominently 'M193'. No other text, no performance stats, no percentages. Generate this single M193 icon.

M855A1: Variant M855A1, improved-penetration tier. Tier backplate and packaging in the blue tier colour, otherwise the same box, cartridges and composition. Realistic 5.56x45mm case with an exposed steel-tip projectile as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '5.56x45 mm' and prominently 'M855A1'. No other text, no performance stats, no percentages. Generate this single M855A1 icon.

M995: Variant M995, high-performance penetration tier. Tier backplate and packaging in the red tier colour, otherwise the same box, cartridges and composition. Realistic 5.56x45mm case with a black-painted armour-piercing tip as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '5.56x45 mm' and prominently 'M995'. No other text, no performance stats, no percentages. Generate this single M995 icon.

Prompts deliberately avoid embedding the damage and penetration percentages: those numbers live in `ammo_types.json` and are shown by the UI, so a rebalance must not invalidate the artwork.

## Publication and recovery

The final PNGs stay local under the project asset-publication policy and are not publicly uploaded; the same boundary as the 7.62 tier art applies. Restore the exact installed files from the host backup — random regeneration is not byte-identical recovery. When the real art lands, record its hashes in `runtime-images.json`, move the placeholder entries to generation history in `trash/`, and keep the reason each earlier attempt was superseded.