# M870 Urban animation revision

Production entry: run `author_animations.py` with Blender 5.1 in background, then execute `install_animations.py` through the project's serialized UE authoring interface. The output is `M870_Urban_Editable.blend`, six animation FBXs and six saved replacements at the existing M870 animation paths.

This revision supersedes the six matching animation roles from `M870Tactical20261015`; that earlier folder remains the gun/skin/bind and locomotion/melee production input. Recreating the original M870 assets requires applying this revision afterwards. Original animation packages are retained under `Before/Animations` before import.

The runtime consumer remains `M870WeaponAssets::AnimationPath`. No C++ changes, new skeleton, duplicate locomotion variants or new outfit bindings are required.

## Action contract

- Equip: 0.60 seconds, adapted from UC draw.
- Fire: 0.90 seconds, UC recoil plus pump, pull 0.16 / rear 0.35 / forward 0.40 / close 0.62 seconds.
- Cycle only: 64/60 seconds; pull 0.12 / rear 0.35 / forward 0.40 / close 0.62 seconds.
- Reload: right-hand feeding, left-hand pump support. Seven source loops are composed with contacts at 44/60 + n * 50/60 seconds and a common tail boundary at 6 seconds. The existing runtime skips unused loops and owns ammo commits/cancellation/network receipts.
- Normal tail: native regrip and return, 399/60-second complete source.
- Empty tail: native regrip followed by pump; source clock pull 6.30 / rear 6.43 / forward 6.48 / close 6.62 seconds, ending at 424/60 seconds.
- Inspect: newly authored 2.50-second left/right side presentation; pauses and easing are staged. Current hand grips are maintained with individual arm solving.

All six roles use one native base sequence. Aim fire and regular fire share the current fire asset. The source does not supply extra grip variants, so no duplicate sequence families or grip profiles are introduced.

No editor/game launch, gameplay test, screenshot, render or audio audition is part of this revision. The user handles visual and gameplay acceptance.

## Saved delivery

On 2026-10-16 the background Python commandlet saved all six animation packages and exited with code 0. `install_receipt.json` has `completed: true`; `delivery.json` records the delivered paths. The first import stopped before saving because sample-rate settings required `set_editor_property`; the corrected production run is `install_console_04.log` / `install_animations.log`. Source processing and asset saving are complete; runtime, audio and multiplayer remain untested.
