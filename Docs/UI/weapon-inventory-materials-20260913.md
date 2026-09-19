# M1911、AKM 与 M4 背包模型图

本轮处理背包武器图像，复用当前游戏枪械模型和材质。目录图是基础装配的透明背景模型图，运行时按实例已保存的配件组合生成动态图；背包、装备栏、拖动和仓库共用选择入口。

## 原因与修改

- M1911 的物品定义没有 `icon`、`ue_icon`。补入 `Icons/ue_m1911.png`；显示层按武器定义读取当前目录路径，因此已经保存的 M1911 无需重新领取或改写存档。
- 原动态图生成器仅对名称为 `M_QBZ191_*` 的枪体材质等待渲染线程就绪，其他枪型及配件可能提前缓存替代材质。现在收集可见枪体分区和可见配件的最终材质，包括材质实例；所有枪型都等待实际 shader map，重新提交组件后再捕获。
- 将贴图驻留请求覆盖到任务等待期间，并等待纹理 mip 加载完成。隐藏的手臂材质不参与等待，材质错误或超时仍使用目录图并让后续任务继续。
- M1911 使用 480×320，长枪沿用 768×320，均按实际枪体及配件范围保留边距，避免手枪套用长枪画幅过小。
- M1911 无物理资产时沿用的参考姿态剔除范围偏向手臂，窄幅取景把枪体裁掉，首次制作捕获为空。预览组件现在根据蒙皮后实际可见枪体范围计算所需剔除缩放；取景仍用真实枪体尺寸，不改动游戏持枪位置、动画或资产包围盒。

## 资源与制作入口

| 目录图 | 当前游戏模型 |
| --- | --- |
| `Content/ColdSteelData/Icons/ue_m1911.png` | `/Game/Weapons/M1911/Hero20260913/SK_M1911_Manny` |
| `Content/ColdSteelData/Icons/ue_akm.png` | `/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative` |
| `Content/ColdSteelData/Icons/ue_m4a1.png` | `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416` |

`Tools/UI/build_weapon_catalog_icons.ps1` 调用 `ColdSteelWeaponIconCatalog` 制作命令。它复用 `UColdSteelWeaponIcons` 的实际装配、灯光、材质、透明背景与取景流程，只创建未初始化的 GameInstance 作为 UObject 宿主，不初始化玩家子系统，不加载地图或修改装备与存档。

旧目录图备份及制作日志位于 `SourceAssets/WeaponInventoryIcons20260913`。模型、贴图及图像沿用各枪现有资产来源与许可，未新增外部素材或扩大源资产再分发授权。

本轮图像导出属于用户要求的图标制作。未进行游戏测试或视觉验收，实际背包表现由用户测试。

## 制作完成记录

- 三张 PNG 均由当前模型制作并写入正式目录，导出器记录 `WeaponIconCatalog: COMPLETE failures=0`。这是图像制作结果，不是实机验收结论。
- `FPSGAMEEditor Win64 Development` 必要构建完成，最终模块后缀 `9132158`。已打开的编辑器需重启加载原生修改。
- 引擎进程因既有启动错误返回 1，图像导出器自身明确记录三张写入及零导出失败；原始信息保留于 `export.log`。
- 为完成构建，将并行采集模块 `TemperateHillsProduction.cpp` 的 `GenerateLocal` 调用显式传入 UE 5.8 默认网格参数 `PCGHiGenGrid::UninitializedGridSize()`，消除新旧 API 的重载二义性；没有补写或替换采集功能。
