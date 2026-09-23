# PKM 材质与换弹分区修复

2026-09-22。用户报告：枪体变绿，换弹时枪体主体及上盖消失，仅剩零散部件。

## 定位

UE 旧 FBX 重导入保留了编辑器 `MaterialSlotName`，而新的几何身份在 `ImportedMaterialSlotName` 中。Belt08 合并导出后顺序变化，原导入脚本仍按保留的槽名绑定材质，运行时也按该名称判断新旧换弹道具。

- 材质槽 11 的导入身份是 `PKM_QBZ_Body`，保留槽名却为 `PKM_AmmoBoxPaint__OldBox`，绑定绿色弹箱涂漆材质。枪体因此变绿，并在旧箱隐藏时被同时隐藏。
- 槽 8 的导入身份是 `PKM_QBZ_Body__OldBox`，保留槽名却为 `PKM_BluedSteel`，旧箱反而没有正确归入换弹道具分区。
- 部分 QBZ 金属分区仍因旧槽名绑定着 Refinement06 材质。

原始记录：`mapping_before.json`。

## 修改与保存

- 将槽名规范为对应的实际 FBX 导入身份，并按该身份重绑当前 QBZ / PKM 材质。
- 原位保存 `/Game/Weapons/PKMLowpoly20260922/SK_PKM_Manny`。未修改几何、骨骼、动作、弹药结算或 C++。
- 在 `Belt08/material_binding.py` 集中此绑定逻辑，由 `reimport_mesh.py` 和 `finish_import.py` 调用，后续重新导入或恢复未完成导入时使用同一规则。
- 实际读取修复后的 16 个 LOD0 分区，枪体为槽 11 `PKM_QBZ_Body`，旧箱为槽 8 `PKM_QBZ_Body__OldBox`，新箱为槽 3 `PKM_QBZ_Body__NewBox`。结果与保存收据为 `mapping_fixed.json`。

本轮按用户要求完成材质和分区排查；未启动游戏复测。用户重新进入 PIE 后检查待机颜色、普通/空仓换弹中枪体与上盖的可见性。
