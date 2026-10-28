# 双持尼泊尔弯刀：待机／走／跑／三连击／双刀突刺／双持重击／双持拔刀

2026-10-25～28。工程 `D:/FPS3D/FPSGAME`，发布到 `allang2208/3D-FPS` 的 `main`。本批只包含双持尼泊尔弯刀（一手一把）的动作、第一人称运行时、作者源与文档；不含其他任务。

## 内容

- **待机／行走／冲刺**（`A_Kukri_DualIdle` 3.0 s、`DualWalk` 0.9 s、`DualRun` 0.667 s）：X 交叉握持，左拳是已认可右拳的镜像；冲刺右手反握、刀朝正前方（参考 16.75–18.4 s）。
- **三连击**（`DualAttack` / `DualAttack2` / `DualAttack3`）：前两段右手先按单持挥完沉下、左手按镜像晚 56/60 帧再挥；第三段双刀同时向前突刺（参考 84.20–85.33 s #5），左右镜像、左拳低 3 cm 错开。
- **双持重击**（`DualHeavyCharge` 2.0 s / `DualHeavyRelease` 1.0 s）：参考 78.20–79.30 s #3 的「X」，两臂交叉、刀拖在拳后；两条直线组成 X 的空间扰动带（`KukriDualRiftRibbons.h`），劈完双手和刀交叉出画面下方再回握姿。
- **双持拔刀**（`DualEquip` 0.917 s）：右手单持抛刀接刀，左手镜像晚 0.067 s，两拳各外移 6 cm、接刀前后前后错开，自然进双持握姿；左刀飞行按 60 Hz 表（`KukriDualEquipBlade.h`）由运行时驱动。
- 运行时：第二把 `SM_Kukri` 挂 `hand_l`；出入双持时左臂单独淡化 0.25 s；两把刀各自结算伤害、顿帧、剑气与命中集合；冲刺反握由运行时在拳里转刀。
- 作者源 `SourceAssets/DualKukriIdle20261025`（拟合脚本、键表、检查脚本、导入入口、README），记录 `Docs/Weapons/dual-kukri-idle-20261025.md`。

## 直接进入运行树的文件

`Source/FPSGAME/Weapons/Kukri/`：`KukriArmsMeshComponent.*`（左臂单独淡化、反握锁）、`KukriRhythm.h`（双刀三段的表与节奏、突刺/重击镜头与打击时刻）、`KukriHeavyRhythm.h`（双持蓄力镜头）、`KukriRift.cpp`（镜像与双 X 扰动带）、`KukriStrike.cpp`（打击档位）、`KukriWeaponComponent.*` 与 `KukriHeavy.cpp` 的差量、`KukriDrawRhythm.h`（双持拔刀的两声）、`KukriDualEquipBlade.h`、`KukriDualRiftRibbons.h`。

`KukriWeaponComponent.cpp/.h`、`KukriHeavy.cpp` 在本机同时带有另一会话尚未发布的网络层（`KukriAttackTiming`、`KukriAttackReceipt`、`KukriNetworkAttack.cpp`、模块外观 `KukriModuleVisual`、`HeavyChargeStaminaPerSecond` 等），**本提交只放双持相关的 hunk**；这些文件在干净检出里因此不是完整可编译单元，需要另一会话的层合入后才闭包。

## 共享宿主差量（Integration/，5 份补丁）

**此提交不是完整本机工程的可构建检出。** 下列宿主由多方并行编辑，本批只发布按 HEAD 对齐的差量：

1. [FPSGAMECharacter.cpp](Integration/Source__FPSGAME__FPSGAMECharacter.cpp.patch)：`IsLeftHandHeldForCast()` 把双持弯刀算作左手被占。
2. [FPSPotionUseComponent.cpp](Integration/Source__FPSGAME__Items__FPSPotionUseComponent.cpp.patch)：进食／喝药时副手刀与双持弯刀都会收起。
3. [ColdSteelProfileRuntime.cpp](Integration/Source__FPSGAME__UI__ColdSteelProfileRuntime.cpp.patch)：快捷装备自动选槽时，弯刀只有在同组主手是双持手枪或弯刀时才进副手。
4. [ColdSteelPlayerState.cpp](Integration/Source__FPSGAME__Multiplayer__ColdSteelPlayerState.cpp.patch)：双持单手近战的命中申报令牌消耗折半。
5. [FPSMeleeMovementNetwork.cpp](Integration/Source__FPSGAME__Movement__FPSMeleeMovementNetwork.cpp.patch) + [FPSCharacterMovementComponent.h](Integration/Source__FPSGAME__Movement__FPSCharacterMovementComponent.h.patch)：服务端查询「这名玩家的某类位移刚被批准且在窗口内」，供双刀突刺的联机击退判定。

[integration-prerequisites.json](integration-prerequisites.json) 给出每份的规范化前置／结果 SHA-256 与依赖说明。

## 本机未发布、但本批运行时代码依赖的层

这些是并行会话在本机的未提交工作，本批**没有**发布；干净检出缺少它们时，上面的 Kukri 文件不可编译：

- `KukriAttackTiming.h`、`KukriAttackReceipt.*`、`KukriNetworkAttack.cpp`、`ColdSteelKukriAuthority.cpp`、`KukriNetworkAuditCommandlet.cpp`（命中回执与服务器动作编号）。
- `KukriModuleVisual.*`（模块外观）与 `MainModules/OffhandModules`。
- `ColdSteelMelee::PairedOneHandedWeapon` / `ComboAttackStamina` / `HeavyChargeSeconds(…,BothBlades)` / `HeavyReleaseStamina(…,BothBlades)`：见 `Docs/Publication/KukriMods20261028/modification-integration.patch`。
- `HeavyChargeStaminaPerSecond`（状态模型差分，同见 `KukriMods20261028`）。
- 双刀突刺的服务端击退实现（`ColdSteelPlayerState` 的 Kukri 回执块）随上述回执框架一起发布，本批不单独出补丁。

## 归档与技能

56 项废案（R3–R15 的中间预览、旧拟合轮、旧作者脚本、重击键存档）移到本机 `trash/dual-kukri-20261028-closeout/`，逐文件记录原路径、字节数、SHA-256、原因与替代物（`manifest.json`），没有永久删除。

技能沉淀：[双持弯刀镜像与双刀编排](../../../skills/ue5-fps-arms-animation/references/dual-kukri-mirror-and-pairing.md)，并在 `ue5-fps-arms-animation/SKILL.md` 与 `ue5-weapon-workflow/references/melee.md` 增加入口。

## 未覆盖范围

本批未启动 UE、未实机测试、未联机验收；构建历史见 `Docs/Weapons/dual-kukri-idle-20261025.md`（Game 与 Editor 目标均构建成功）。第三人称拔刀仍是单持身体动作，双持下的上挑／冲刺攻击／F 刀把仍用单持动作。
