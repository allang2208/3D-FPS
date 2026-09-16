# 背包转向与抽屉贴边发布记录（2026-09-16）

## 发布

- 仓库/分支：`https://github.com/allang2208/3D-FPS.git` 的 `main`（唯一日常开发与 Git 目录 `D:/FPS3D/FPSGAME`）。
- 提交：`2053b7c2d5283b8f7cc7d16665bd626ddc7db1c8`（`Add backpack item rotation, fix weapon icon materials and dock the drawer right`），快进自 `31aa457`，普通推送 `HEAD:main`，`git ls-remote origin main` 回读一致。
- 发布内容（26 个路径）：背包拖动转向（`ColdSteelInventoryTypes.h`／`ColdSteelInventoryRules.cpp`／`ColdSteelWarehouseRules.*`／`ColdSteelStatusModel.h`／`ColdSteelProfileRuntime.cpp`／`ColdSteelWarehouseModel.cpp`／`ColdSteelInventoryWidget.*`／`ColdSteelDragVisual.*`／`ColdSteelInventoryPresentation.cpp`）、抽屉贴右边缘与打开时让步／左缘 Caps 入口删除（`ColdSteelUIStyle.h`／`ColdSteelPanelNavigation.cpp`／`ColdSteelHUDWidget.cpp`／`ColdSteelCharacterSheet.cpp`）、三份案例文档、三个图标材质审计／修复工具、三条 UI 技能引用与 `Docs/UI/README.md` 索引。
- 精确暂存：本仓库 `git apply --cached` 对本索引不生效（即使完整 diff 也报 `patch does not apply`），改用 `git hash-object -w` + `git update-index --cacheinfo` 只写本次 hunk；`git diff --cached`/`--check` 通过，并以 `TreeGrowth|MeleeWeaponStats|IsTwoHandedSword|ColdSteelMelee|PersistState|DualWield` 等关键字确认未夹带并行会话的未验收改动。

## 验证依据

- 改动期间多次完整构建成功：`build-20260916-210344.log`、`build-20260916-211657.log`（无后缀）、`build-20260916-214132.log`（抽屉贴边 + 删除左缘 Caps 入口）；编辑器在运行时改用后缀模块（`9162031`／`9162120`／`9162140`／`9162230`／`9162351`），日志在 `Saved/BuildEditor/`。
- 发布前只删改 `.cpp` 的部分用 UBT 生成的单文件命令复核（`Saved/BuildEditor/cl-check-*.log`，全部 OK）。
- 未做游戏内测试，实机表现由用户测试；用户此前已确认转向与图标修复可用。

## 未发布/本地内容

- 8 个修复后的武器材质 `.uasset`（QR/Core/Skeleton 枪托橡胶、稳定防滑后握把、QBZ SurfacePolish×3）按仓库规则不提交；备份与报告在 `Saved/BackpackIconModFix20260916/`。
- 定位过程的旧诊断产物（`Saved/QRStockInspect/*`，11 个文件）已按第 4 节退役到 `trash/backpack-icon-fix-20260916/`，含 `manifest.json`（原路径/目标/字节/SHA-256），移动后哈希复核一致。
- 并行会话仍在改的双持/近战评估/树木生长/体素建造等内容保持未暂存；当前工作树因此暂时无法整包构建（`VoxelBuildWidget.cpp` 与 `VoxelBuildComponent.cpp` 重复定义 `NumberKeyIndex`，非本次内容），本提交不含这些文件。
