# Super90 loader R17 — hand only

User scope: arms are fine; repair the hand during the overhand bolt pull after the accepted R16 fast push.

Only left thumb/index/middle/ring/pinky joint quaternion curves in eight empty/cycle actions change. Wrist rotation/position, all arm tracks, all location/scale keys, gun/props, R16 timing, R15 sounds and measured camera remain unchanged. No arm IK, skin edit or ordinary reload replacement.

Reference: existing Delta Force capture, frames 293/298/302/308. Index hooks the actual Super90 handle; middle finger curls separately; ring/pinky stay relaxed; thumb stays open. Release the fingers before the existing bolt return, then rejoin the existing fore-end grasp.

Authoring: Blender `prepare_hand.py`, Python `fit_hand.py`, Blender `author_r17.py`, then `run_r17.ps1`. Eight animation assets and four grip profiles have been saved through the existing editor bridge. Normal loader and other profile entries are preserved by exact target path. See `import_receipt.json`; overwritten assets are in `Before/Content/`.

No C++ edit/build, game launch, preview render or runtime test. User review remains pending. Detailed record: `Docs/Weapons/super90-speedloader-r17-hand-hook-20261009.md`.
