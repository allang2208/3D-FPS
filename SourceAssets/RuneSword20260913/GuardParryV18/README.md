# 双手剑防御与弹反 · GuardParryV18

**后续状态（2026-09-14）：V18 姿态被用户指出不符预期；后续 V19 也未获满意，当前暂停。以下机制与制作过程为历史记录，不是已接受的格挡母版。** 见 [当前作者入口](../README.md)。

计划与机制说明：`Docs/Weapons/RuneSwordGuardParry20260914.md`。

右键按住举剑格挡、松开收剑。基础机制取自原 gamedev 的 `shield-system.js` 和 `shield-config.js`：1 秒/左右各 120° 弹反，普通格挡承伤 50%、消耗 20 体力，不足时清空并破防 1.5 秒；防御步速减半、停回体力。近战弹反使攻击者眩晕 1 秒并短时扫掠击退 100 cm；远程/魔法抵消该次伤害及其命中附效。持续中毒和腐蚀地面不进入剑防。

## 动作源

`AzureRunesword_Manny_Editable.blend` 保留现有 Manny 双手、剑和已接受攻击；新增三个非循环动作：

- `A_RuneSword_Guard`：0.20 秒抬剑，运行时保持末帧，松开按 0.18 秒反向收回。
- `A_RuneSword_GuardHit`：约 0.22 秒吸收冲击后复位；受击时剑与双手共同运动。
- `A_RuneSword_GuardBreak`：0.40 秒破防压开和回待机；游戏僵直独立保持至 1.5 秒。

`guard_motion.py` 给出斜向左上剑身、胸前偏右握点及关键姿态；`author_guard.py` 是可直接执行的作者脚本，重复且无调用的 `author_guard_body.py` 已归档到 trash。`arm_solver.py` 和 `diagonal_motion.py` 延用现有双手与肩肘腕求解。`Export` 保存 480 Hz FBX。

## 反馈声音来源

本机原 gamedev 资产：

- `E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/shield/wood_hit_crisp_cavity_1s.wav` → `Audio/S_RuneSword_Block.wav`。
- 同目录 `wood_thud_1s.wav` → `Audio/S_RuneSword_Parry.wav`。

沿用原防御机制的声音区分；不是新生成的金属撞击录音。源文件留本机，不因本轮移植获得额外的公开再分发许可。

## 接入与记录

运行时逻辑主要在 `RuneSwordGuard.cpp`；`RuneSwordGuardTuning.h` 为基础数值。伤害在当前 UE 护甲计算后进入剑防，弹反在发送受伤事件前归零。原有中毒与恐惧攻击根据本次实际伤害返回值决定是否施加附效。

破防输入锁由玩家独立的 `PlayerGuardBreakComponent` 管理，拥有独立计时和成对输入锁；切换装备不会清除僵直，结束时右键仍按住则重新尝试举剑。怪物眩晕与扫掠击退在 `MonsterParryReaction.cpp`。

`authoring.json`、`author.log` 为制作记录；`import_receipt.json` 与导入日志为资产交付记录。`Before` 保存本轮已有源码快照。`build_install.ps1` 执行必要 Editor 构建，成功后保存后缀 `49158` 模块及清单。

本轮未执行实机测试、截图、渲染或验收，交由用户试用。

2026-09-14 交付记录：动作制作及五项 UE 资产导入均正常结束。最终 Editor 必要构建 `Succeeded`（181.92 秒），构建脚本退出码 0，模块快照已保存至 `NativeBuildSnapshot`。完整记录见 `author.log`、`import.log`、`build.log`。重启编辑器后加载本轮原生修改。
