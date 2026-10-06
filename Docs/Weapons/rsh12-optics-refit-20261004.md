# RSH-12 瞄具尺寸与 PSO 原侧挂架修订

用户要求三个 1× 瞄具缩小以贴合枪身，PSO 恢复原侧挂衔接架。用户关闭编辑器后，8 个模型资产和共享 PSO 图标 Texture 已后台导入并保存，枪匠描述已更新。基础 `UnrealEditor-FPSGAME.dll` 已后台编译成功；实际保存与构建记录见本轮 `import_receipt.json`、`catalog_receipt.json` 和 `build_receipt.json`。

## 镜体与安装接口

- `holographic`、`panoramic_red_dot`、`eoth_holographic` 的镜体缩为上一版的 78%，按各自实际底脚锚点烘焙到顶点，保留 UV、材质槽和光学部件。`SightRear`、`SightFront`、`SightUp` 等光学坐标同步变换。
- 三款安装座的上安装面由 6.5 mm 降至 3 mm，长度缩为原来的 78%，上层冠面半宽调整为 8.1 mm；下层夹爪仍匹配 RSH 实际导轨肩宽 16.536 mm，止退键仍落在原横槽位置。
- 二倍棱镜、LPVO 和倍率环保留当前版本。缩小只写入 RSH 私有资产，不改变共享瞄具或其他枪械。
- PSO 改用已修复接缝的 `PSO1_AKM_Editable.blend` 中原镜体、镜片和 `PSO_ScopeMount`，保留原侧挂夹具与锁杆、原尺寸、UV 和材质分区，取代上一版切脚后重建的上方支柱。
- 新增薄接收座 `SM_RSH12_PSOReceiverShoe`，接触面由固定枪身 `1_l`、`2_l`、`3_l` 的实际侧表面生成。两组接触垫位于弹仓前方；夹具、锁杆和连接座均跟随固定 `WPN_root`，不附着活动弹仓或摆臂。
- PSO 光心允许随原侧挂结构横向偏置约 4.52 mm，并更新光学插槽供既有 ADS 求解；不修改已认可的手臂姿势、715 动作或五发快速装填器。

## 生产文件与接入

作者目录：`SourceAssets/RSH12OpticsRefit20261004/`。

1. `read_fit_inputs.py` 读取原侧挂架与 RSH 固定枪身接口；`author_refit.py` 生成 8 个 FBX、可编辑 Blend 和 `authoring.json`。
2. `run_stage.ps1 -Stage Import` 在共享批次互斥下后台导入 3 个缩小镜体、3 个底座、PSO 镜体和 PSO 侧接收座。`import_refit.py` 保留原材质绑定、保存光学插槽，并补存已有 PSO 共享图标 Texture。已有目标资产先备份到本目录 `BeforeAssets/`。
3. `publish_catalog.py` 只修改 RSH 的 PSO 安装描述，保留现有选项数值、图标键和其他枪械数据。
4. `run_stage.ps1 -Stage Build` 更新基础 `UnrealEditor-FPSGAME.dll`，使 `RSH12OpticAssets::RailPath(pso1_4x)` 解析新的侧接收座。`build_receipt.json` 记录实际构建结果。

运行路径继续沿用 `/Game/Weapons/RSH12/Optics20261004/Meshes/` 与 `/Game/Weapons/RSH12/PSO20261004/Meshes/`。只有 PSO 的底座路径改为后者的 `SM_RSH12_PSOReceiverShoe`；镜体资产路径与枪匠选项 ID 不变。

恢复工程时，先恢复早期公共瞄具/PSO 的材质等基础接入，最后应用本目录的模型导入与构建。仅重跑早期 `author_mounts.py` 或 `author_pso.py` 会恢复旧尺寸或旧支柱，不代表当前用户指定的修订版。

本轮没有进行游戏、PIE、截图、渲染或回归测试。后台导入与构建结果不代表实机效果已验收，观感和操作由用户测试。
