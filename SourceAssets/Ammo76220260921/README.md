# 7.62x39mm UI ammunition art

Created 2026-09-21 using the built-in image_gen tool (not CLI). Project reference: `Content/ColdSteelData/Icons/ammo_762.png`, the existing realistic red cardboard ammunition box icon. Three separate generated assets; no 3D models.

The user subsequently specified tier backgrounds: LP green, PS blue, AP red. The final installed outputs have corresponding opaque colored backplates and matching box paint. Initial colors and transparency attempts below are retained as generation history only, not the installed result.

Runtime outputs:

- `Content/ColdSteelData/Icons/Ammo76220260921/762_lp.png`
- `Content/ColdSteelData/Icons/Ammo76220260921/762_ps.png`
- `Content/ColdSteelData/Icons/Ammo76220260921/762_ap.png`

## Shared generation prompt

Create a high quality photorealistic inventory icon for a fictional FPS game, matching the supplied existing ammunition icon's visual style exactly: a small worn cardboard ammunition box with open lid, rows of brass and copper cartridges, two loose rounds standing beside it and two lying in front, isolated product photography, three-quarter view from above, soft neutral studio lighting, crisp real paper fibers, restrained patina and natural metallic roughness, not cartoon, not overly shiny, no scenery. Square 1024x1024 composition with 10 percent safe transparent margin. True transparent alpha background, no floor, no drop shadow, no checkerboard baked into pixels. This is purely a 2D game inventory illustration, no diagrams or internal mechanisms. Keep consistent box proportions, camera, lighting, and cartridge proportions across LP PS AP set.

## Per-asset suffixes

LP: Variant LP: muted oxblood red cardboard packaging like reference, natural copper tips with no marking. Clear cream stencil printing on FRONT of box, exactly two lines: '7.62x39 mm' and prominently 'LP'. No other text, no performance stats. Retain realistic short bottleneck rifle cartridge silhouette. Generate this single LP icon.

PS: Variant PS: muted military olive-gray green cardboard packaging, same composition as reference, copper/brass cartridges. Clear cream stencil printing on FRONT of box, exactly two lines: '7.62x39 mm' and prominently 'PS'. No other text, no performance stats. Retain realistic short bottleneck rifle cartridge silhouette. Generate this single PS icon.

AP: Variant AP: matte charcoal dark-gray cardboard packaging, small restrained ivory border on the front, same composition as reference, brass and copper cartridges with black-painted tips as a fictional visual identification only. Clear cream stencil printing on FRONT of box, exactly two lines: '7.62x39 mm' and prominently 'AP'. No other text, no performance stats. Retain realistic short bottleneck rifle cartridge silhouette. Generate this single AP icon.

## Transparent-background edit

Initial PS and AP outputs were RGB on black; a second built-in image_gen edit requested transparent alpha. Targets were the corresponding initial output; LP was the supporting example of real transparent alpha. Prompt (with PS/AP and green/charcoal substituted):

Image 1 is the PS inventory icon to edit. Image 2 is only an example of the required real transparent alpha file. Background extraction only: preserve ALL foreground pixels, text '7.62x39 mm PS', green packaging, bullets, layout, material, resolution and lighting in Image 1. Remove its black background COMPLETELY and return a genuinely transparent RGBA PNG with alpha=0 outside the objects. Remove dark floor/contact shadows outside the object silhouettes. Do NOT replace the black with white or checkerboard or any color. Do NOT draw a transparency checkerboard. Do not change the box or any text. Deliver only the isolated PS icon with actual alpha transparency.

Original generation paths (historical locations; superseded originals moved to `trash/a762-ammo-publication-20260921/GeneratedImages`, not deleted):

- LP: `C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-54f07ff1-2c32-4a35-b2fb-c8ed9fc8b5d8.png`
- PS initial: `C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-0a23a8dd-402a-431d-ab35-c081a637f7e3.png`
- AP initial: `C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-653d8846-bf6d-4660-b851-85040f6a49a4.png`

## Final tier-color edits

Exact final prompts are in `final-prompts.json`. Final built-in outputs copied to the three runtime PNG paths above:

- LP green: `C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-d4e6aed0-9329-4b71-aac6-f903f7f89341.png`
- PS blue: `C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-183ef2ef-47ba-4b29-b013-d32d6717e3bc.png`
- AP red: `C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-06112973-359e-41e1-a88d-af7b2dee00e4.png`

## Publication and recovery

Final runtime PNGs and adopted concept art remain local under the project asset-publication policy. Restore these exact files from the host backup; random regeneration is not byte-identical recovery. Runtime image hashes and final prompts are in `runtime-images.json` and `final-prompts.json`. Superseded source images and failed alpha variants are archived; see [archive manifest](../../Docs/AssetArchives/a762-ammo-publication-20260921.json). No API credentials or generated service responses are included in the public recipe.
