# 副手近战联机、技能改时序与物品快照（2026-10-26）

来源：手枪＋副手弯刀（`Docs/Weapons/dual-pistol-kukri-idle-20261025.md` R6–R11，补丁包 `Docs/Publication/DualPistolKukri20261025`）。按问题读取。

## 副手武器发起的技能命中

- 客户端用副手物品建 Shot（`ColdSteelSkills::Snapshot(P, 副手物品)`），回执申报的就是副手实例；服务端在"主手为双持手枪 → 配对槽（6→8 / 其余→11）单手近战"上解析。快速近战 0x80、上挑 0x14 的授权、验收、结算、移动放行各处都要做同一解析（本例共 6 处）。
- **伤害公式放进客户端与服务端共用的头文件**（`OffhandKukriThrust.h`），`ComputeServerDamage` 直接调用，避免两边各写一份后漂移。
- **攻击形态**：服务端对所有 0x80 默认按钝击；副手刀突刺是刀刃，需按同一配对判定在服务端取 `Blade`，否则削韧与客户端不一致。

## 技能改时序后检查服务端的配套时长

- 动作提速后，凡是服务端按"另一把武器的时钟"推算的窗口都要复查。本例：`AuthorizeMeleeMove` 对所有上挑突进按双手剑上挑算硬直（约 1.28 s），弯刀上挑提速后只剩约 0.83 s，期间接冲刺斩的位移被服务端驳回。改为按弯刀自身节奏积分（`KukriRhythm::UpperRealSeconds`）。
- 只是"截止时间"类窗口（如 `UppercutUntil`、`QuickCombatUntil = 时长 + 0.35 s`）动作变快仍能容纳，不用改；"最短间隔/恢复期"类才会误拒。

## 同款武器数值不一致

- 物品实例的 `Data` 保存的是**获得当天的目录快照**，`ColdSteelInventory::Number` 读的就是它。物品表改了攻速/距离后，新旧实例就不一样（本例两把弯刀 `attack_seconds` 0.8 vs 1.9792）。
- 本地读档 `ReloadProfile` 现对所有近战武器同步目录调校字段（`melee_damage / melee_reach_cm / attack_seconds / swing_seconds / contact_seconds / melee_stamina / block_stamina / block_reduction`），与联机导入的 `SanitizeNetworkItem` 同一字段集；锻造品质、改造件、强化是实例状态，不同步。
- 排查方法：在存档 `.sav` 里搜物品 id，取实例 `Data` 里的 JSON 逐字段对比。

## 发布

- 共享宿主只发补丁；补丁生成器 `SourceAssets/DualPistolKukri20261025/gen_integration_patches.py` 逐层回退本轮编辑并做 sha256 校验，需在 Git Bash 下运行（依赖 GNU diff/patch）。已发布补丁之后宿主又被其他会话改动时，本轮单独出叠加补丁（`.r8.patch` 形式，注明 `apply_after`）。
