# 连续工装上衣腋下体素桥撕裂修复与水密门禁

本页沉淀自 `LumberMillOps-R59 / R60b`（修复 `SK_Carpenter_Workwear`、`SK_Smith_Outfit`、`SK_MasterArtisan_Workwear` 三套工装腋下漏空与穿模），适用于所有基于体素/SDF 生成并在 A-pose 下绑骨的连续上衣网格。

## 1. 根因识别

1. **A-pose 腋下体素桥（Batwing Bridge）**：在手臂自然下垂的 A-pose 下运行 `marching_cubes` 时，内袖筒与躯干肋侧距离小于体素半径会被焊成实心桥；上臂前伸或高举时，单个 `< 1 cm` 腋下三角面被拉裂至 `22–24 cm`（`42×` 拉伸），形成视觉黑洞。
2. **内层裸肤槽位未遮罩**：`SK_Smith_Body` 槽位 `0 (DefaultSleeves)` 与槽位 `3 (SkinTorso)` 若未在运行时替换为 `M_Smith_Covered`，抬臂瞬间会从袖笼或腋下穿出 `+4–5 cm`。
3. **外展重裁领口误切三角肌孔洞**：外展重建后若仅按 `Z` 高度裁剪领口而不限定横向半径，会切到抬起的双肩三角肌外侧，在肩顶留下 `~3 cm` 破洞。

## 2. 标准修复流程与硬门禁

1. **+46° 外展重建 + 精确逆 LBS**：先按骨骼权重将双臂外展 `+46°` 拉开 `8+ cm` 腋下净空，在展开态重建连续衬衫网格并对腋窝折缝做 `16` 轮权重/顶点光顺，再通过精确逆 LBS 还原至绑定姿态（完整保留口袋、领口、袖口、原材质槽与 3 级 LOD，零新增贴图）。
2. **领口横向半径护栏**：裁剪领口时必须同时约束 **`|X| < 13.5 cm`**，避免触及外展后的三角肌表面。
3. **两项必过量化门禁**：
   - **拓扑水密门禁**：连续上衣主体严格满足 **`boundary_loops == 3`**（仅领口 + 左袖口 + 右袖口，0 额外孔洞）。
   - **极限动作拉伸门禁**：在最高抬臂/挥砍关键帧上测试所有三角边拉伸比，要求 **`max_edge_stretch <= 3.5×`**（实测 `42.73× → 3.05×`、`p99 = 1.67×`）。
4. **运行时双槽遮罩**：共用 `SK_Smith_Body` 且穿全袖上衣的 NPC，在构造/初始化外观时对槽位 `0` 与槽位 `3` 统一应用 `M_Smith_Covered`。

## 3. 参考实现

- 生产脚本：`Tools/WorldGeneration/ForestVillage/repair_lumber_workwear_r59.py`、`repair_master_artisan_workwear_r60.py`、`bake_master_artisan_r60.py`
- 运行时遮罩：`Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp`
