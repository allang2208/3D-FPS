# M249 side magazine: framed 45-round icon and left-hand reload

Published on 2026-11-08. The requested model render, asset authoring, imports and saves are complete. No gameplay or animation acceptance tests were run. No UE editor GUI was opened.

## Icon

- Rendered the actual `SM_m249_side_mag_45` mesh in Blender and composited it inside the existing 30-round icon's metal frame, circular ring and rivets.
- Final source: `Icons/ue_m249_magazine_m249_side_mag_45.png`.
- Render scene: `M249_45_Icon_Studio.blend`; reproducible sources: `render_icon.py`, `compose_icon.py`, `icon_recipe.json`.
- Imported and saved the framed texture under `/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_m249_magazine_m249_side_mag_45` and the corresponding root fallback texture.

## Motion

- Authored and saved normal and empty side-magazine reload sequences at 120 fps under `/Game/Weapons/M249/SideMagazine20261108/Animations`.
- Left hand approaches and wraps the magazine, extracts it along the socket axis, brings the replacement to the port, pauses for alignment, inserts and seats it, then returns to the foregrip.
- Authored matching whole-arm, wrist and finger layers for base, vertical, canted, prism and angled foregrips. Both 30-round and 45-round magazines use the same mouth and grip interface.
- Retained the right-hand support and M249 empty-reload charging tail. Added small pull/seat reactions to the weapon root while keeping contact tracks together.
- Existing side-magazine source-clock contacts, audio cues, magazine visibility and ammo commit timing remain shared. The receiver cover remains closed for side-magazine reloads.
- Source clip lengths are 3.8 and 5.0 seconds; the existing runtime clock scales them to the selected magazine's durations below.

## Reload attributes

| Magazine | Normal reload | Empty reload |
| --- | ---: | ---: |
| 30 rounds | 3.6 s | 4.8 s |
| 45 rounds | 3.9 s | 5.1 s |

Updated only the two M249 side-magazine options in `Content/ColdSteelData/gunsmith.json`. Existing gunsmith benefit rows calculate the faster reload attributes from the actual multipliers. Capacities remain 30 and 45 rounds.

## Saved output and scope

- `install_receipt.json`: nine saved UE packages, comprising two animation sequences, five grip profiles and two icon textures.
- `catalog_receipt.json`: published reload attributes; `catalog_before.json`: prior M249 catalog entry.
- `Before.zip` and `before.json`: affected assets before publication.
- No C++ changes in this batch, so no native rebuild was required. Animation build/compression and texture imports ran through the background UE commandlet under the existing batch mutex.
- Gameplay timing, hand contact, clipping and visual feel remain for the user to test in game.
