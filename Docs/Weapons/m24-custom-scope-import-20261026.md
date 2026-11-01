# M24 Custom Scope — 2026-10-27

> 当前模型、骨架、动作及图标见 [M24 比例与材质修复](m24-repair-20261027.md)。
> 首次导入和首次模块化版本的比例与 UV 存在错误，保留下文作为历史记录。

后续模块化版本见 [M24 拆分与独立瞄准镜](m24-modular-20261027.md)。下文保留首次
全装导入记录；当前运行网格及可拆装范围以该后续记录为准。

Selected model: [M37_R — M24 Sniper Rifle, Custom Scope](https://sketchfab.com/3d-models/m24-sniper-rifle-custom-scope-84b72eaf37a54ecb945017e3955455a0).
Compatible original motion: [DJMaesen — sniper animated](https://sketchfab.com/3d-models/sniper-animated-b48999a250b2433da59f705c371a49b2).
Custom optic: [MaximDeduytsche — Rifle Scope w/ Laser & Sight](https://sketchfab.com/3d-models/rifle-scope-w-laser-sight-d82ec237ad2f49a384d59f84fcde5429).
All three public source records identify CC BY 4.0. Attribution, archives and
license records are in `SourceAssets/M24CustomScope20261026/`.

## Saved assets

The native/source import is complete: **48 saved UE packages**, recorded by
`import_receipt.json`, under `/Game/Weapons/M24/CustomScope20261026`.
It contains the assembled static rifle, 14 static parts, mechanically rigged
weapon, original-arm viewmodel, PBR materials/textures, skeleton and six source
animation files. The custom remix itself has no animation; the linked original
has the compatible arm and mechanical animation.

The game adaptation is saved separately: **10 UE packages**, recorded by
`gameplay_import_receipt.json`, under `/Game/Weapons/M24/Gameplay20261026`.
`SK_M24_V9` uses the installed M4 V9 hand surface and native arm bind, including
81 corrective morphs plus the basis in the editable source. It has a private
mechanical skeleton and does not overwrite the M4. Fitted M4 hand/arm equipment
is mapped by the same unchanged arm bones.

| Game role | Source seconds | Origin |
| --- | ---: | --- |
| idle / aim | 0.0333, constant loop | Original held pose, retargeted |
| fire / aim_fire | 1.8333 | Original shot and bolt cycle plus recovery |
| reload | 2.0000 | Original magazine action plus lead/recovery |
| reload_empty | 3.6667 | Original magazine action and second bolt cycle |
| cycle | 2.0667 | Original second bolt cycle, retained standalone |
| equip | 0.8000 | Newly authored raise on the M24 grip |
| inspect | 3.0000 | Newly authored supported inspection |
| quick_melee | 0.9000 | Newly authored stock strike and recovery |

Aim shares idle and aim-fire shares fire. Regular locomotion uses existing
procedural movement; no incompatible M4/SVD sprint clip is applied.
Interrupted cycling resumes through the cycle section of empty reload,
keeping the normal reload transaction clock.

The complete native timeline remains `Animations/A_M24_source_all` (201
frames at 30 Hz). Two unnamed native tail segments retain frame-range names;
their names do not claim artist-supplied inspect/equip/melee semantics.
The imported native final segment is 0.7 seconds after FBX sampling.

## Runtime integration

Definition `ue_m24`, display name **M24**:

- Private model/animation loading and source clocks in `M24WeaponAssets.h`.
- One trigger press per shot; the full fire cycle scales with the effective
  interval. Busy state blocks another shot while allowing ADS to remain.
- `FPSGAMECharacterM24.cpp` schedules bolt sounds and preserves an interrupted
  cycle against the outgoing weapon instance. Existing persisted item fields
  and reload transactions perform recovery.
- Casing emission occurs during withdrawal; an interrupted local casing
  resumes at the reload-cycle ejection contact.
- Fixed factory 6x scope uses existing scope UI and sight calibration. The
  selected suppressor remains part of the factory model.
- Third-person motion uses the existing active mechanical channel. A buttplate
  marker supplies stock contact and the melee origin.
- Inventory, asynchronous icons, pickup studio, initial armory, ammunition
  pouch, crafting and V9 outfit profile are registered.

This import exposes the complete selected factory assembly. Separate source
parts remain available for future gunsmith work. Alternative fitted attachment
recipes, auxiliary sight switching and a functional laser are not added.

Game balance is configuration, not real-world performance: 5-round capacity,
1.8333 s base interval, 2 s normal / 3.6667 s empty reload, 650 m effective
range and 820 m/s game projectile speed. Damage uses the shared evaluator:
base 80 + 2×int + 5×wis, with registered enhancement terms.
The NATO group `ammo_m24_762x51` is separate from 7.62×39 and 7.62×54R.
Its crafting recipe is a game resource recipe.

The one-time starting-armory grant includes five rounds loaded and 30 reserve
rounds. No current save file is directly edited. The catalog fallback is
`Content/ColdSteelData/Icons/ue_m24.png`.

Historical description and caliber reference:
[US Air Force — The M24 Sniper Weapon System](https://www.minot.af.mil/News/Article-Display/Article/806191/the-m24-sniper-weapon-system/).
The selected artist's detachable-magazine/custom-optic model is retained;
it is not described as an exact standard-issue configuration.

## Production sources

Task-owned files are in `SourceAssets/M24CustomScope20261026/`:

- `M24_CustomScope_Native_Editable.blend`: original full action and assembly.
- `M24_V9_Gameplay_Editable.blend`: V9 arms and game actions.
- `M24_CatalogIcon_Editable.blend`: catalog image production scene.
- `author_assets.py`, `bind_source_materials.py`: native preparation/export.
- `export_v9.py`: export the installed V9 reference.
- `author_gameplay.py`: retarget and private clip export.
- `import_assets.py`, `import_gameplay.py`: UE save entry points.
- `install.ps1`: existing named mutex; existing editor bridge or background
  commandlet. Pass `-Stage import_gameplay` for V9 assets.
- `register_data.py`: add only M24/ammunition entries to fresh catalog reads.
- `connect_runtime.py`: initial source connection anchors; later narrow edits
  are in the current C++ sources, which remain authoritative.
- `delivery_status.json`: final asset/build/manual-testing status.

The source archive contains no audio. Gameplay reuses project SVD mechanical
sounds and the existing suppressed-shot bank; these are not original M24
recordings.

The final background `FPSGAMEEditor Win64 Development` build succeeded on
2026-10-27 after the M24 source changes, producing the ordinary editor module.
Build log: `Saved/BuildEditor/build-20261027-084355.log`.

No PIE, gameplay, animation contact, visual, audio, multiplayer or automated
test is run. The catalog icon is a production asset, not an acceptance image.
Saving and compiling do not establish visual or gameplay acceptance; user
testing is pending. No editor/game is launched for delivery.
