# Attribute panel and equipment-card replication QA

- Date: 2026-09-09
- Reference runtime: Godot 4.7.1, `E:\3d\3-dfps`
- Target runtime: Unreal Engine 5.8, `D:\FPS3D\FPSGAME`
- Viewport: 1280 x 720
- Reference states:
  - `E:\3d\3-dfps\docs\preview\attribute-str-1280.png`
  - `E:\3d\3-dfps\docs\preview\equipment-format-1280.png`
- UE runtime states:
  - `D:\FPS3D\FPSGAME\Saved\UIAudit\2026-09-09\ue-attribute-panel-1280.png`
  - `D:\FPS3D\FPSGAME\Saved\UIAudit\2026-09-09\ue-equipment-card-1280.png`
- Combined comparisons:
  - `D:\FPS3D\FPSGAME\Saved\UIAudit\2026-09-09\attribute-compare-1280.png`
  - `D:\FPS3D\FPSGAME\Saved\UIAudit\2026-09-09\equipment-card-compare-1280.png`

## Checks

- 45 percent right drawer, cold-steel palette, four-tab hierarchy, active underline, section accents, two-column attributes, and viewport-clamped overlays match the reference structure.
- Status hover card has title, separator, description, calculated rows, note, and dismisses when leaving the attribute or switching tabs.
- Equipped weapon hover opens the three-card enchant, modification, and main-item presentation; click pins it and the close button dismisses it.
- Health, movement speed, magazine, reserve ammunition, weapon damage, fire interval, reload time, and magazine capacity are read from runtime character/component properties.
- Magic, stamina, experience, and the standalone six-attribute gameplay component do not exist in the current UE gameplay layer; their migrated slots are explicitly labelled as not connected instead of presenting invented runtime authority.
- Final UE 5.8 Development Editor build succeeded after the visual pass.
- No P0, P1, or P2 clipping, overlap, unreadable-text, wrong-active-tab, or viewport-bound issues remain in the captured states.

final result: passed
