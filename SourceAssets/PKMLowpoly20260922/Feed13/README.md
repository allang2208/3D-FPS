# PKM firing belt feed — Feed13

Source: `../Wrist12/PKM_WristContact_Editable.blend`.

## Authored changes

- Replace only the old belt's 21 cartridge and 20 connecting-link tracks in `fire` and `aim_fire`.
- Each shot moves the visible cartridges toward the preceding position on the existing curved belt path. The nominal exposed spacing remains about 18.3 mm.
- Feed begins at 0.012 s and reaches the next slot at 0.080 s. The clip ends at 0.100 s. Its FBX samples at 240 Hz; the complete editable Blender scene stays at 60 Hz with subframe keys, preserving the other actions' timing.
- Add a small authored ripple along the free bend with zero offset at the receiver and box endpoints. This is an authored follow-through effect, not a new runtime physics simulation.
- The innermost round and link advance under the closed cover, shrink out locally, and refill at the hidden end inside the box. Only these two recycling units change scale. The body, remaining belt, ammunition box and arms do not inherit that scale.
- The rest of the firing animation comes from Wrist12. Reload, idle, wrist fitting, mesh, weights and materials are unchanged.

Editable source: `PKM_FiringFeed_Editable.blend`. Exported animations: `Exports/A_PKM_fire.fbx`, `Exports/A_PKM_aim_fire.fbx`.

## Runtime changes

`Source/FPSGAME/FPSGAMECharacter.cpp`:

- Use actual shot age for PKM firing animation time instead of adding a whole frame at the trigger event.
- Speed the clip up when the effective firing interval is shorter than its duration.
- Keep full firing-action weight until the idle handoff. Blending indexed belt bones back to their original positions would visibly reverse the feed.
- Preserve the last shot's visible belt through the end of its firing cycle. The real magazine count and reload rules remain immediate and unchanged.

These runtime changes and the animation assets are one revision and should be used together.

## Integration status

Both animations were imported and saved to `/Game/Weapons/PKMLowpoly20260922/Animations/`; `motion_import.json` records the two asset paths and their 0.1 s lengths. No mesh import was performed.

Live Coding could not compile: UBT reported 192 pending build actions above its limit of 100 (`Saved/pkm13-build-01.txt`, UBT log at 2026-09-22 18:07:24). Runtime code is pending a normal Editor build after the editor is saved and closed. The current editor must not be treated as the complete Feed13 revision until that build is finished.

No game test, preview render, screenshot, or runtime acceptance was performed. User testing remains outstanding.
