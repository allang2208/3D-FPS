# 双手锤第三人称装备副本：额外手臂修复

用户反馈 V5/V6 表现不合格，明确选择“第三人称能看到额外一套手臂或武器”。本轮先修复能从实际网格制作记录与运行源码定位的重复手臂，不把历史接入完成当作动作获认可。

## 原因

第三人称装备通过 `CaptureWeapon` 复制工具网格，再把复制体挂到全身角色的 `hand_r`；身体和装备副本使用各自的骨架。装备副本应保留武器，隐藏原生第一人称手臂。

当前双手锤网格为 `/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1`。导入脚本 `SourceAssets/SteelWarhammer20261014/SprintDragV1/import_sprint.py` 和已保存的 `MaterialRepairV1/repair_receipt.json` 记录了以下分区：

| 材质槽 | 原隐藏规则 | 本轮处理 |
| --- | --- | --- |
| `Skin_UpperArm` | 未命中，额外上臂可见 | 加入第一人称手臂隐藏规则 |
| `Skin_Forearm` | 未命中，额外前臂可见 | 加入第一人称手臂隐藏规则 |
| `Skin_Hand` | `_hand` 后缀已隐藏 | 保留 |
| `M_SteelWarhammerSurface` | 随原厂锤体/模块替换状态隐藏 | 保留 |

因此只隐藏摄像机下的原始第一人称手臂不能修复此问题：遗漏的是已经复制到第三人称手腕上的上臂和前臂分区。

## 修改范围

- `FPSPlayerBodyEquipment.cpp` 的 `IsArmMaterial` 精确识别两个遗漏槽名，不使用模糊 `arm` 匹配，避免误隐藏武器护木等部件。
- 结果写入现有 `FFPSBodyWeapon::HiddenMaterials`；装备创建的全部 LOD、`ApplyMotion` 后续分区更新和既有复制数据均消费此字段，无需另外创建相机隐藏分支。
- 保留 Kwang/KayKit 候选资产、静态握柄适配和头颈稳定；不更改第一人称手臂资产、伤害或动作时钟。现有全身动作路径使用冻结装备绑定，并关闭第一人称动态腕点叠加。

## 状态

源码修复已编入正式 Editor DLL，日志 `Saved/BuildEditor/build-20261016-225724.log`，Succeeded。未启动编辑器、游戏、PIE、截图或测试。此修复针对重复手臂显示错误；用户进一步明确的角色双臂扭曲继续由 [V7 握持返工](steel-warhammer-anatomical-grip-v7-20261016.md) 处理，不宣称动作效果合格。
