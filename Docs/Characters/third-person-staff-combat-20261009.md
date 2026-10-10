# 法杖普攻体力与第三人称拳击／挥杖

> 这是对应阶段的制作记录。当前接入、替代关系和恢复依赖以[第三人称动作发布说明](../Publication/ThirdPersonActions20261010/README.md)为准；旧手工抓握表及被否定的腕臂姿态不作为当前基线。

## 游戏规则

- 法杖普通攻击在开始时调用 `ColdSteelMelee::UnarmedAttackStamina`，与普通空手出拳共用 `PunchCost`（当前基础 8 点）、临时体力倍率和角色近战体力倍率。
- 体力不足不进入挥杖；每次开始仅扣一次，挥空和中途取消不返还。原有攻击间隔、伤害、命中暂停与范围不变。
- `AttackStamina` 对法杖使用同一入口，HUD 的可攻击次数与实际扣除一致。

## 本地来源与适配

源包为 `SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1`，包内 License.txt 为 CC0。

| 正式动作键 | 本地来源 | 适配 |
| --- | --- | --- |
| Unarmed.FullBody.PunchRight | Melee_Unarmed_Attack_Punch_A | 保留出拳节奏，去除大幅前移，按 Jason 臂长和拳架调整 |
| Unarmed.FullBody.PunchLeft | 同上 | 根据左右骨骼绑定基准镜像，保持骨长 |
| Staff.FullBody.Strike | Melee_1H_Attack_Chop | 将单手下劈适配为持杖攻击，使用当前抓握掌坐标 |

也读取了本地 UAL2 的 Melee_Hook／Melee_Hook_Rec；动作偏大幅勾拳与俯身，未用作普通左右拳。本次挥杖是单手近战素材的适配，并非作者原生法杖动画。

三个动画放在 `/Game/Characters/JasonPlayer20261003/StaffPunch20261009/Animations`。`assets-saved.json` 是实际资产保存和 `player_body.json` 注册回执；Donors 是制作来源，不作为正式播放入口。

## 动作接入

- 复用现有第三人称库动作混合器。由已有攻击进度驱动，Contact／Release 标记映射到游戏判定时刻；不以动画通知追加伤害或扣体力。
- 下半身继续使用地面接触、行走、蹲伏和空中动作。动画不推动角色胶囊体。
- 普通拳、法杖左拳使用对应左右拳动作；法杖左拳保留右手握杖，挥杖保留副手枪独立姿势。
- 拳头和握杖手指沿用当前原生手指层，后者包含 2026-10-09 的四种杖杆／握把贴合。库动作只替换上身动作和手腕轨迹。

## 交付范围

制作脚本位于 `Tools/PlayerBody/*staff_combat20261009.py`，后台构建日志和交付回执位于 `SourceAssets/ThirdPersonStaffCombat20261009`。

三个正式动画已实际保存并注册。`FPSGAMEEditor Win64 Development`、`FPSGAME Win64 Development` 均构建成功（退出码 0），编辑器模块与游戏程序已落盘；见 `delivery.json` 和两份 `build-*.log`。

按用户规则不启动交互编辑器、游戏、渲染或验收；必要的后台重定向、资产保存与原生编译单独记录，不代表运行效果已验证。最终效果由用户测试。
