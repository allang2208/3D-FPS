# .45 ACP / .357 MAG UI ammunition art

2026-09-22. User asked to give both pistol calibers three tiers so the dual-wield two-disc R wheel has something to switch between, with the same effects as the existing 7.62x39mm LP / PS / AP set. Code plus written record first, **no image generation**; the tier pictures are placeholders.

Runtime paths are reserved and already referenced by `Content/ColdSteelData/ammo_types.json`:

- `Content/ColdSteelData/Icons/AmmoPistol20260922/45acp_fmj.png` — .45 ACP green tier
- `Content/ColdSteelData/Icons/AmmoPistol20260922/45acp_p.png` — .45 ACP blue tier
- `Content/ColdSteelData/Icons/AmmoPistol20260922/45acp_ap.png` — .45 ACP red tier
- `Content/ColdSteelData/Icons/AmmoPistol20260922/357_sp.png` — .357 MAG green tier
- `Content/ColdSteelData/Icons/AmmoPistol20260922/357_jhp.png` — .357 MAG blue tier
- `Content/ColdSteelData/Icons/AmmoPistol20260922/357_ap.png` — .357 MAG red tier

Each placeholder is a byte-identical copy of `Content/ColdSteelData/Icons/ammo_556.png` (1254x1254, 1,590,709 bytes, sha256 `e716b0005397a61ed9e87caa0dcb4439297026c1ecc251bbaa1836112de6f259`), the same stand-in the 5.56 tier set used. It carries no tier backplate and no caliber-specific packaging, so today only the catalog-driven tier colours (`tier_name` / `tier_color`) and the printed names distinguish the six rows. Hash and status per file: `runtime-images.json`.

Placeholders for both calibers are intentionally the same picture: the point of this batch is to make the two pistol groups multi-tier so the wheel opens, not to ship art. Replace them before any visual review of the pistol tiers.

## What the final set still needs

Replace the six PNGs at the reserved paths, keeping the file names so no catalog edit is needed. Follow [仅数值弹药的等级图标](../../skills/ue5-item-asset-workflow/references/numeric-ammo-icons.md): UI picture only, no three-view, no 3D package, no world pickup, no inventory cell. Tier assignment stays green / blue / red per caliber, matching `ammo_types.json`. Pistol cartridges are short and stubby — do not reuse the 5.56 bottleneck silhouette.

## Shared generation prompt (not yet run)

Create a high quality photorealistic inventory icon for a fictional FPS game, matching the supplied existing ammunition icon's visual style exactly: a small worn cardboard ammunition box with open lid, rows of brass and copper cartridges, two loose rounds standing beside it and two lying in front, isolated product photography, three-quarter view from above, soft neutral studio lighting, crisp real paper fibers, restrained patina and natural metallic roughness, not cartoon, not overly shiny, no scenery. Square 1024x1024 composition with 10 percent safe margin. Opaque tier backplate, no floor scenery, no drop shadow. This is purely a 2D game inventory illustration, no diagrams or internal mechanisms. Keep consistent box proportions, camera, lighting, and cartridge proportions across all six icons, and keep the visual scale and negative space of the 7.62x39mm LP / PS / AP set.

## Per-asset suffixes (not yet run)

.45 ACP FMJ: Variant .45 ACP FMJ, standard ball tier. Tier backplate and packaging in the green tier colour. Realistic .45 ACP silhouette: short straight-walled large-diameter pistol case with a round-nose full-metal-jacket bullet. Clear cream stencil printing on FRONT of box, exactly two lines: '.45 ACP' and prominently 'FMJ'. No other text, no performance stats, no percentages. Generate this single icon.

.45 ACP +P: Variant .45 ACP +P, improved-penetration tier. Tier backplate and packaging in the blue tier colour, otherwise the same box, cartridges and composition. Same .45 ACP silhouette, fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '.45 ACP' and prominently '+P'. No other text, no performance stats, no percentages. Generate this single icon.

.45 ACP AP: Variant .45 ACP AP, high-performance penetration tier. Tier backplate and packaging in the red tier colour, otherwise the same box, cartridges and composition. Same .45 ACP case with a black-painted armour-piercing tip as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '.45 ACP' and prominently 'AP'. No other text, no performance stats, no percentages. Generate this single icon.

.357 MAG SP: Variant .357 MAG SP, standard tier. Tier backplate and packaging in the green tier colour. Realistic .357 Magnum silhouette: long straight-walled rimmed revolver case with a soft-point bullet showing exposed lead at the tip. Clear cream stencil printing on FRONT of box, exactly two lines: '.357 MAG' and prominently 'SP'. No other text, no performance stats, no percentages. Generate this single icon.

.357 MAG JHP: Variant .357 MAG JHP, improved-penetration tier. Tier backplate and packaging in the blue tier colour, otherwise the same box, cartridges and composition. Same .357 Magnum case with a jacketed hollow-point bullet, cavity visible at the tip, fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '.357 MAG' and prominently 'JHP'. No other text, no performance stats, no percentages. Generate this single icon.

.357 MAG AP: Variant .357 MAG AP, high-performance penetration tier. Tier backplate and packaging in the red tier colour, otherwise the same box, cartridges and composition. Same .357 Magnum case with a black-painted armour-piercing tip as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '.357 MAG' and prominently 'AP'. No other text, no performance stats, no percentages. Generate this single icon.

Prompts deliberately avoid embedding the damage and penetration percentages: those numbers live in `ammo_types.json` and are shown by the UI, so a rebalance must not invalidate the artwork.

## Publication and recovery

The final PNGs stay local under the project asset-publication policy and are not publicly uploaded; the same boundary as the 7.62 and 5.56 tier art applies. Restore the exact installed files from the host backup — random regeneration is not byte-identical recovery. When the real art lands, record its hashes in `runtime-images.json`, move the placeholder entries to generation history in `trash/`, and keep the reason each earlier attempt was superseded.
## 2026-09-22 退役与留空（用户规则：有本口径图标就接入，没有就空着）

这 6 张占位图（内容为 `Icons/ammo_556.png` 的逐字节副本）已退役到 `trash/AmmoPistolIconsRetired20260922/`，
同目录 6 个 `.uasset` 一并退役（不再被任何 JSON 引用）。`ammo_types.json` 里 ammo_45acp_* 与 ammo_357_*
六行 `icon` 改为空串，界面按"缺图不留占位"处理（轮盘不画图标与凹槽、弹药袋行不加图标槽）。

**这里是将来专用美术的保留位置**：新图放回 `Content/ColdSteelData/Icons/AmmoPistol20260922/<同名>.png`，
再把 `ammo_types.json` 的 `icon` 与 `items.json` 的 `ue_icon` 指回对应文件即可，不改代码。
生成提示词与规格仍以本目录 README 为准（轮廓按口径：.45 ACP 短粗直壁、.357 MAG 有底缘）。
