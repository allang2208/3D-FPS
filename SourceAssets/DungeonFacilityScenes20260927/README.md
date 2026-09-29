# Facility scenes production batch

Reusable assemblies and compatible room-local recipes for Drainage, VentilationLoop and FreightTransfer. See `Docs/Gameplay/dungeon-facility-scenes-20260927.md` in the project for integration details and the untested scope.

- `Authored/FacilityAssemblies.blend`: editable source; nine local-origin FBX exports and `manifest.json` sit beside it.
- `Scripts/author_assemblies.py`: Blender background authoring, including UCX boxes and final triangle UVs.
- `Scripts/prepare_recipes.py`: three functional recipes per family, each with three compatible environmental states.
- `Scripts/extend_catalog.py`: idempotent pure catalog layer; does not enlarge the room pool or change ports/cells.
- `Scripts/import_assets.py`: import and save this batch's meshes, using source hashes and ownership receipts. Large objects retain UCX collision; small clutter has none.
- `Scripts/install.py`: merge into the saved generator's current catalog, retain existing dependencies, save the generator ExternalActor and canonical catalog. Does not generate a level or run PIE.
- `Scripts/background_install.py`: commandlet entry for the two preceding stages. Use only while no editor is holding the project assets; otherwise use the existing mutually exclusive MCP bridge.
- `Receipts/import.json`, `Receipts/install.json`: actual mesh and map save receipts. Completed pre-install snapshots were moved to `trash/dungeon-upgrades-20260927/`; their hashes and paths are recorded in `Docs/Gameplay/dungeon-retired-20260927.json`.

Current production status: nine meshes saved; generator catalog saved; Editor base DLL compiled by the regular project build recorded in `Saved/BuildEditor/build-20260927-181044.log`. No gameplay, visual or performance tests were run. Re-enter the dungeon to generate a new layout using the recipes.

All geometry in this batch is authored by the included script. Material references reuse the project's existing materials; their original licensing and redistribution restrictions continue to apply.

2026-09-28：移除随机维修桌台 RepairBench 及其四处布置与避让占位；后续仅导出八种组合件。原模型保留在本机，生成器已解除其硬引用。未运行游戏测试。

2026-09-28：货箱与配电柜改用 `../DungeonFacilityPropPolish20260928` 的精修作者函数和共用 PBR 图集；本目录的两件 FBX、清单项及合集 Blender 同步更新，其余组合件保持。两件原始简模函数已移除，避免重建恢复旧效果。先由精修批安装共享贴图/材质及网格，实际保存记录见该批 `Receipts/install.json`。未运行游戏或视觉验收。
