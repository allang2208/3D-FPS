# 201 Meshy retry 28 reference provenance

Date: 2026-09-29. Scope: one candidate requested by the user, using two new user-supplied screenshots, with smooth surface appearance emphasized. No UE asset replacement or ammo-box gameplay restoration is part of this generation.

## Original references

- `Reference/original_belt_side.png`: exact copy of `C:/Users/allan/AppData/Local/Temp/codex-clipboard-b8c287aa-db95-409c-bd25-2faba3bf305a.png`.
- `Reference/original_opposite.png`: exact copy of `C:/Users/allan/AppData/Local/Temp/codex-clipboard-c1eb1094-75d6-40c2-8c7c-ef727e1e7748.png`.

These are user-provided game screenshots for this reference task. No claim of third-party asset redistribution rights is made.

## Prepared Meshy inputs

Both inputs were prepared with imagegen to remove backgrounds and UI. They are generated reference edits, not pixel-exact extractions; minor generative changes are possible. Original screenshots are preserved above.

Primary: `Inputs/opposite_primary.png`. Secondary: `Inputs/belt_side.png`.

The two images are different views of the same object, submitted together to the multi-image API. The reference includes a box and visible cartridges as visual geometry only.

### Belt-side cleanup prompt

Precise background extraction and game UI cleanup for a 3D game-art modeling reference. Output one isolated cutout of the EXACT weapon in the provided image, same LEFT-facing side view and identical proportions, visible parts, holes, contours and component placement. Remove the background completely to transparent alpha. Remove all thin diagonal UI leader lines and square/crosshair UI markers overlaying the object, remove floating text/callout cards and floor reflection. Keep the original weapon surface appearance and hard-surface silhouette, do not beautify, remodel, round off, reinterpret or add any details. Preserve the cylindrical barrel, smaller lower tube, thin front sight open ring, three vent rows, stepped flat receiver cover, exposed decorative belt and camouflage box, pistol grip, triangular stock opening, all negative spaces. Gun entirely within frame with small transparent margin. No hands, no extra views, no new labels. This is a game-art reference cutout, not an engineering diagram. WIDE LANDSCAPE framing, 3:1 aspect preferred.

Output: `C:/Users/allan/.codex/generated_images/01a0e2fb-9067-7b51-8783-a86c432af5dc/exec-fc7eff2a-5c37-4332-9bfa-f0e0eca77ef7.png`.

### Opposite-side cleanup prompt

Precise background extraction for a 3D game-art modeling reference. Output one isolated cutout of the EXACT weapon in the provided image. Keep this specific RIGHT-facing opposite-side slight elevated three-quarter view: stock on LEFT, muzzle on RIGHT. Preserve the identical camera perspective, exact proportions, surface details, asymmetric side of the receiver, folded-down carrying handle, vents, raised sights, two tubes, buttstock negative spaces, camouflage box and pistol grip. Remove background/floor/reflection to transparent alpha. Original metallic/polymer/fabric surface appearance must stay; no beautification, invented geometry, pose changes, new accessories, or reconstruction of unseen sides. Keep clean borders and all real transparent openings. Whole gun must fit with small margin. One view only. Wide landscape framing 3:1 preferred. Game-art reference cutout, not an engineering drawing.

Output: `C:/Users/allan/.codex/generated_images/01a0e2fb-9067-7b51-8783-a86c432af5dc/exec-73ff4b4d-10cd-4a92-adbd-dfcacf80521a.png`.

## Meshy request

Task: `01a0eab7-c55f-76f0-8df0-921bd934af3a`.

The complete settings and texture prompt are in `meshy_settings.json`; the sanitized submitted request and task receipt are in `Meshy/lmg201_new_reference_smooth_v01/`.

- Model: Meshy 7.1, multi-image to 3D.
- Geometry: 2k (highest supported multi-image resolution for this model), no remeshing.
- Texture: 4k, PBR enabled, remove lighting enabled.
- Image enhancement disabled to reduce reinterpretation.
- One paid generation only; receipt reports 35 credits.

The current multi-image API has no shape-prompt field. The smoothness wording is sent as `texture_prompt`, which controls texturing, not a guaranteed geometry constraint. The geometry is guided by the cleaned reference images and generation settings. This attempt also changes reference images and random generation, so it cannot establish that wording alone improves geometry.

Official API documentation consulted on 2026-09-29:

- https://docs.meshy.ai/en/api/multi-image-to-3d
- https://docs.meshy.ai/en/api/image-to-3d
- https://docs.meshy.ai/en/api/pricing

No API credential is persisted in this directory. The runner accepts a process environment variable or hidden password input.
