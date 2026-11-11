# 弯刀/斧头双持组合、副手单持与冲刺攻击整理（2026-11-11）

本批对应 2026-11-04 至 11-10 期间的连续工作：

1. 双持斧头的冲刺就绪跑姿（就绪前保持待机移动姿态，就绪循环右手与左手同频同幅）。
2. 双斧抛接装备；斧+弯刀混搭各手按自己的武器播；主手空、副手单持弯刀/斧头时镜像单持全套到左手（右手隐藏）。
3. 副手单持的同步/穿插修复；吊坠与附魔组件识别副手单持。
4. 双持冲刺攻击双手向下劈；单手武器上挑参考双手剑前置蓄力（出手 0.7 s）。
5. 联机复查：三处只读主手的结算改走 `ActiveKukriWeapon()`。
6. 第三人称补齐：副手单持镜像到左手；斧+弯刀第三击各手各的。

## 主树内容与接入边界

**直接提交（武器自有宿主 + 生成头 + 作者源 + 文档）**

- 生成的节奏头：`HatchetPairRhythm.h`、`KukriDualDashRhythm.h`、`HatchetReadyRhythm.h`（注释更新）。
- 副手抛接：`OffhandBladeDraw.h/.cpp`（`OffhandBladeDraw20261104` 生成）。
- 只读复核：`LoneOffhandBladeAuditCommandlet.h/.cpp`。
- 作者源：`SourceAssets/HatchetPairs20261104/`、`SourceAssets/DualSprintAttack20261104/`、`SourceAssets/OffhandBladeDraw20261104/`、`SourceAssets/HatchetSprint20261103/` 的脚本与说明。
- 文档：`Docs/Weapons/tactical-hatchet-20261101.md`、`Docs/Weapons/kukri-20261020.md`、`skills/ue5-fps-arms-animation/references/hatchet-dedicated-actions.md`。

**Integration 补丁（共享宿主，`Integration/`）**

`KukriWeaponComponent.{h,cpp}`、`KukriStrike.cpp`、`KukriRift.cpp`、`KukriArmsMeshComponent.{h,cpp}`。

这些文件在工作区里同时叠着其他会话尚未发布的层（SwiftFalcon 钩爪、网络重击回执、模块外观 `MainModules`、staff-offhand 旋风等）。整文件提交会连带发布他人工作，因此只以 HEAD 相对补丁发布本任务的 hunk。补丁由 `make_patches.py` 从 `git diff HEAD` 的 hunk 中按标记筛选生成，全部在 HEAD `77df964b` 的干净导出上用 `git apply --check` 验证通过。校验值见 [integration-prerequisites.json](integration-prerequisites.json)。

**整文件提交（无法做 HEAD 相对补丁）**

`KukriWhirlwind.cpp`、`KukriDashAttack.cpp`：HEAD 版本分别是 staff-offhand 重构与网络回执层之前的旧版，本任务的改动叠在那层之上，无法表达成 HEAD 相对补丁。随本批提交工作区整文件，前提写在 `integration-prerequisites.json` 的 `whole_file`。

## 联机复查修复

副手单持时以下三处仍只读主手（为空），改为 `ActiveKukriWeapon()`：

- `Skills/ColdSteelDashAttackModel.cpp` `DashAttackStats`：客户端出招和服务端 0x16 冲刺攻击的伤害、距离。
- `Skills/ColdSteelSkillModel.cpp` `QuickCombatStats`：快速连击的狂战倍率。
- `Skills/ColdSteelSkillRules.cpp` `GrantBerserkOnWeaponHit`：命中叠狂战层数的来源武器。

这三个文件同属共享宿主，按 `Integration` 补丁发布（见清单）。

## 第三人称补齐（2026-11-10）

1. **副手单持镜像到左手**：身体装备的刀挂 `hand_l`（`FFPSBodyWeapon::bLoneBlade`），动画在动作混合完成后、手型抓握之前把整段上半身按骨架绑定位姿镜像（`FControls::MirrorLoneBladeUpperBody`，写法同已认可的单持左手手枪 `FSinglePistolMirrorLayer`）。`FFPSBodyState::bLoneBlade` 由本地采样、服务端影子档案与 observer 三方同判。腿保持原步态。
2. **斧+弯刀混搭第三击各手各的**：新增第三条姿势输入 `SwordAlt`；主取（右手）按主手武器选 `Kukri.Hatchet.DualChop` 或 `Kukri.FullBody.Dual.Thrust`，另一取只提供左手整条链，共用双刺 2.05 s 时钟。`FPSBodyKukriMotion::Clip` 按 `HatchetPairAttack3HK/KH` 分派，`PreserveHands` 与 observer 剑气窗口同步放开。
3. 副手单持旋风沿用既有转向约定，本轮未调整。

这些是角色身体动画共享宿主（`FPSPlayerBody*`、`FPSBody*`），同样只以 `Integration` 补丁发布。

## 构建

- `FPSGAME Win64 Development` Succeeded（`Saved/BuildEditor/build-3p-lone-mixed-r3-20261110.log`）。
- `FPSGAMEEditor Win64 Development` Succeeded（`Saved/BuildEditor/build-3p-lone-mixed-editor3-20261110.log`）。
- Game 目标与 Editor 目标均已链接；构建期间因其他会话占用 UBT 锁与 DLL，按规则等待而非抢占。

## 验证边界

- **未运行游戏、未测试、未验收**。动作观感、第一人称与联机表现由用户测试。
- 第三人称的双斧/混搭**装备动作**仍走双弯刀装备表 `Kukri.FullBody.Dual.Equip`（需要新动画资产，本轮未做）。
- 网络测试未执行；本轮只做静态复查与编译。

## 废案归档

见 [cleanup-manifest.json](cleanup-manifest.json)。trash 不进 Git。
