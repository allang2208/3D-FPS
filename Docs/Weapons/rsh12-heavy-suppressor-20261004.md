# RSH-12 专属大口径消音器接入

用户先要求参考 ASH 完成模型，随后授权接入游戏。作者源位于 `SourceAssets/RSH12HeavySuppressor20261004/`。UE 模型、纹理、四个材质槽、插槽及专属图标已后台导入保存，枪匠选项已发布，包含本次全部源码的基础 DLL 已构建成功并落盘。

## 模型与安装

- 网格：`/Game/Weapons/RSH12/HeavySuppressor20261004/SM_RSH12_HeavySuppressor`。
- 选项：仅 `ue_rsh12 → muzzle → rsh12_heavy_suppressor`，显示名“RSH 大口径消音器”，菜单使用现有专属边框样式。现有 RSH 原厂枪口和其它槽位保留。
- 使用已完成的短粗模型、八道纵槽、斜纹套环和 RSH 原枪管端面接座。原网格四个材质槽保留。
- `RSH12MuzzleAssets.h` 的安装矩阵由原端面与当前 RSH native alignment 推导；厘米静态网格挂 `WPN_root` 时只转换一次单位，不使用 ASH/M4 枪口后退量，也不依赖整枪包围盒。
- 出口为模型局部 +X 轴 18 cm，静态网格保存 `MountFace` / `Muzzle` / `AimGuide` 插槽。开火表现使用同一出口，弹仓独立运动不拖动配件。
- 三个外部材质实例使用共享 WeaponSurface 的 CleanSatinSteel 基线，但保留本件实际 BaseColor、粗糙度、法线和 AO。粗糙度和 SurfaceMask 从作者 ORM 按既有 WS 通道合同导出，天气沿用标准单层淋湿；深色端口保持独立消光材质。

## 行为与数据

- RSH 的枪口装配在 715 与通用配件回退之前分派；只接受本专属 ID。恢复原厂时移除消音器并清除运行选项。
- 单持消音状态连接既有声音、枪口火光抑制和 AI 枪声范围。声音沿用用户指定的 `PistolAudioAssets::Suppressed`，保留普通 RSH 开火音源。
- 双持和法杖副手通过既有共享装配复制同一网格和出口，独立消音状态与声音同时接入。长枪口附件使用既有长型近战动作选择。
- 枪匠草稿、应用、取消、实例保存、库存/掉落装配沿用现有 `gunsmith_parts.muzzle`。选项数值与说明效果复制发布时 ASH 专属消音器的当前基线，不另建结算规则，不修改用户存档。
- 发布数值为 `recoil_mult=0.7`、`stability_mult=1.3`、`bullet_speed_mult=0.8`、`ads_percent=0.1`，对应后坐力 −30%、稳定性 +30%、弹速 −20%、开镜耗时 +10%。
- 库存异步配方预加载本专属模型及其依赖。现有 `/Game/Weapons/RSH12` Cook 根已覆盖新增资产。
- 图标由实际模型灰阶素材和既有金属框母版生成，写入 PNG 及同键 Texture2D：`FramedFirearms/ue_rsh12_muzzle_rsh12_heavy_suppressor`。这是产品 UI 制作，不是游戏验收截图。

## 制作入口与状态

1. `prepare_integration.py`：材质通道派生、接口头文件与 `integration_inputs.json`。
2. `author_icon.py`：实际模型的灰阶图标素材和可编辑图标场景；imagegen 使用该素材与现有框体母版制作最终图。
3. `run_stage.ps1 -Stage Import`：后台保存纹理、材质、网格和插槽；完成记录为 `import_receipt.json`。
4. `run_stage.ps1 -Stage Icon`：保存实际菜单路径的 Texture2D 与 PNG；完成记录为 `icon_receipt.json`。
5. `publish_catalog.py`：只更新 RSH 枪口选项并保留并行目录修改；记录 `catalog_receipt.json`。
6. `run_stage.ps1 -Stage Build`：后台构建基础 Editor DLL；记录 `build_receipt.json`。

本次 DLL 采用同一工程已完成的共享构建成果：两次构建均实际编译了 `ColdSteelIconResources.cpp`、`FPSGAMECharacter.cpp`、`M4GunsmithLayout.cpp`、`M4MuzzleVisual.cpp` 和 `PistolDualWieldComponent.cpp`，并成功链接 `UnrealEditor-FPSGAME.dll`。最近一次结果为 `Succeeded`，DLL 保存于 2026-10-04 14:39:55（本地时间）。具体构建日志与时间见 `build_receipt.json`；尚未启动的重复构建排队已取消。

未启动图形编辑器、游戏或 PIE，未进行听感、视觉、存档或回归测试。资产保存、原生编译与用户实机效果分别报告。
