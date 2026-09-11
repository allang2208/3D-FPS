# Magic scroll — 2026-09-11

User requested a tied rolled scroll turnaround, an extracted inventory icon, RTX 5080 modeling and game integration.

## Image source

Generated with the built-in image generation tool. Prompt: Photorealistic game item modeling turnaround sheet, one tightly rolled tied magical parchment scroll. Wide triptych, equal panels: front, right side, back. Same object, scale, orientation. Vertical cylinder axis; ivory aged parchment with layered curled rims, fibers and naturally uneven edges. Dark violet woven cord around the middle, compact front knot and short ends; small antique brass bead. No rods, opened flap, writing, runes, glow or debris. Approximately 24 cm tall and 6 cm wide. Neutral photographic PBR lighting, fully visible, transparent background requested.

Original: `magic_scroll_source.png`, copied from the generated image `exec-4f28d535-8b9e-4c25-bf41-c1afd82c638c.png`. Generation returned an opaque studio backdrop. A subsequent background-removal image edit returned a painted checkerboard and was rejected. `extract_views.py` performs the requested view extraction using U2Net foreground masks, preserves source object pixels, and crops the front and rotates it 35 degrees for legibility in a single inventory cell, producing a 512-square transparent PNG. No new drawn details are added by extraction.

## 5080 source and delivery

Live node and hardware snapshots: `nodes.json`, `system_stats.json`. Queue was empty before submission. Prompt ID `78151b41-007f-4515-b5ea-d17a67d2cf4e`; exact settings and execution history retained. Front/right/back are separate crops connected to the multi-view node, not one image connected to a single-view generator. TRELLIS.2-4B, 512, 12/16/12 steps, Euler, seed 91103, 2K textures, 100K export target. Raw geometry: 6,677,298 triangles. Raw and textured exports downloaded with SHA-256 verification against the remote outputs.

Textured master: 95,091 triangles. Delivery: 19,999 triangles. Original mesh had excessive girth compared with the reference; XY was scaled by 0.6 before normalization to approximately 24 cm height. One duplicate face produced during decimation was removed with mesh validation. Original high master remains intact.

Normal bake from textured master: 2K, 0.2 mm cage, 0.5 mm ray distance. Unhit/backward thin-wall normal texels (545,161, including unused UV background) use the geometric tangent normal instead of invalid black/backward normals. These areas do not claim recovered high-poly detail. The game model has less cord fiber detail than the reference image; no claim of exact image reconstruction.

Editable delivery: `magic_scroll_lod0_editable.blend`; portable model `Delivery/magic_scroll.glb`; UE FBX/maps and channel manifest in `UE/`. Base color, roughness and metallic come from TRELLIS; tangent normals are locally baked. Studio preview `magic_scroll_beauty.png` renders the delivered 19,999-triangle GLB.

Game mapping: four existing `enchant_scroll_*` items share this artwork, while names, effects, rarity, count and stack limit remain unchanged. Actual runtime proof and limitations are recorded in `Docs/Art/magic-scroll-20260911.md`.

Wrong-axis upright previews and two superseded pre-fix Blender backups were moved to `trash/non-weapon-items-20260911/SourceAssets/MagicScroll5080_20260911/`. See `Docs/Art/non-weapon-items-archive-20260911.json` for exact paths and hashes. Raw master, valid editable source and delivery remain in place.
