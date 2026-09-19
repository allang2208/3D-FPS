# HK416 audio

## Current selection — 2026-09-06

User-selected files copied without editing from `E:/无尽轮回/游戏/素材库/音效/开枪音效/HK416/`:

- `equip.mp3`: bolt/charging sound, played by the existing weapon equip/charge action.
- `reload.mp3`: reload sound, used for both normal and empty reload through the existing reload action.
- `fire.mp3`: firing sound, played once per shot at original pitch, without extra mechanical or reflection layers.

Both `weapon_data/hk416.tres` (playable weapon) and `weapon_data/hk416_audio.tres` (audio-only preset) now reference these files. Original files were not trimmed, normalized or retimed. The shared gun system no longer adds per-shot mechanical impacts, reverb or randomized pitch; suppressors retain the existing volume reduction. Upstream rights remain with the source owners; user selection does not establish a new asset license.

## Previous selection (removed on 2026-09-06 after verifying no runtime references)

Copied without editing from E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/weapons/ at the user's request.

- m416_fire.mp3: used by the source project's M416 fireSound configuration.
- m416_equip.wav: dedicated M416 equip asset present in the source directory; the source runtime currently maps M416 equipment to the generic rifle_equip.mp3 instead.
- m416_reload.wav: dedicated M416 reload asset present in the source directory.

These sounds retain their original upstream rights; this copy does not assign a new license. They are not covered by the Sketchfab model's CC BY license.

weapon_data/hk416_audio.tres is an audio-only WeaponData preset for the staged HK416. It has no model_scene and is not a playable weapon entry. Copy its three sound fields into the HK416 weapon data during model integration. Existing AKM/P9 sound assignments are unchanged.
