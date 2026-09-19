# Cold Steel UI migration

## Current vertical slice

- Runtime root: `UColdSteelHUDWidget`, hosted by `AFPSGAMEPlayerController`.
- CommonUI is enabled and `CommonGameViewportClient` owns input routing.
- `Tab` or `B` opens a right-side, 45%-wide inventory panel. `Tab`, `B`, `Esc`, or the close button returns to game input.
- The first panel preserves the source contracts: 3x5 equipment cells, 18x4 initial spatial inventory cells, and the Q/E/X + 1-4 hotbar.
- The ammo card reads live AKM magazine and reserve values from `AFPSGAMECharacter`; no placeholder gameplay value is used.
- UI gameplay tags are ready for Smart Modular UI's tag-based menu manager.

## Smart Modular UI boundary

The Fab entitlement is present, but no Smart Modular UI `.uplugin` is installed in UE 5.8 or in this project yet. The project therefore does not declare an unknown marketplace module. Once Epic Launcher installs a UE 5.8-compatible build, inspect its `.uplugin` and example project, then bind:

- `UI.Menu.Inventory` to the cold-steel inventory activatable widget.
- `UI.Menu.Settings` to the plugin's generated settings menu.
- plugin global text/background/button style assets to the values in `Config/ColdSteelUI.json`.
- notification/message channels to `UI.Message.Notification`.

## Not yet claimed complete

The current inventory cells are a visual and interaction shell. Item definitions, item instances, 5x2 rifle footprints, stack splitting, drag/drop validation, equipment exclusion, warehouse/shop flows, save migration, tooltips, processing badges, and responsive render acceptance remain separate implementation stages.

The local SimSun and Consolas files are used for editor parity when present. They have not been copied into the project; shipping font licensing and packaged font assets remain an explicit release task.
