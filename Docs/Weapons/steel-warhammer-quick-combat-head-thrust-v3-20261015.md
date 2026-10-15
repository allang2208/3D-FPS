# 战锤快速近战：锤头向前直击 V3

用户否定横柄短顶，要求替换成剑类第三下连击式的向前捅，用锤头直击。V3 替换当前快速近战序列；原方案留存备份。

2026-10-15 后续：用户确认运行状态修复后已能正常播放，随后否定 V5 的紧凑节奏。当前继续制作 [V6 分阶段前捅](steel-warhammer-quick-combat-reach-v6-20261015.md)：独立 V6 资产扩大前伸行程、实际总长 0.72 秒。下述 V3 参数保留作历史源记录，V3 原资产不覆盖删除。

## 动作

- 参考 `SourceAssets/RuneSword20260913/StrideThrustV16/thrust_motion.py`：收低对准前方、快速直送、沿接触轴卸力撤回、再恢复原待机。实际读取剑的第三击伸展轴，按战锤原握距重新制作。
- 总长 0.5 秒；0–0.09 秒收低蓄势；0.09–0.15 秒直送；0.15 秒命中；0.175 秒达到伸展顶点；0.33 秒附近撤回后开始恢复原待机方向。
- 命中时握柄中心相对蓄势前进 20.5 cm，接触时仍有 2.6 m/s 前进速度；最终行程 24 cm。锤柄与锤头在出手段沿同一前向轴运动，回收连续减速，无停帧段。
- 双手沿柄的握点、握距、径向距离与五指包握姿态保留。蓄势时整只闭合手掌沿圆柄调整握持角度，随后随锤头直送，收尾恢复待机握姿；不松手、不缩短握距、不单独掰腕。
- 采用 `ThrustElbowRepair20260923/Standard/Thrust_ElbowSupport_Editable.blend` 中已做肘部支持修正的完整剑类动作，按两套原生参考骨架转换肩肘引导，再适配战锤宽握距。原生骨长保持，额外前臂旋转按实际蒙皮站位分配；支撑肩部降低 4.5 cm。未采用早期从参考姿态绝对扭转角重新求解整臂的候选，候选脚本仅保留在 `Before/`。
- 制作约束用于控制关节扭曲和镜头遮挡，不代表游戏验收。
- 保留快速近战独立时钟和现有镜头反馈。没有套用剑普通第三击的一米角色突进或普通攻击伤害。

## 接入

- 正式资产保持 `/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat`，由现有快速近战入口加载。
- `WarhammerQuickCombatMarker.h` 改由锤头最前端实际几何生成，不再使用两掌之间的锤柄接触点。
- 判定沿锤头的高度和横向位置，从视点平面向前扫描，仍使用快速近战原有范围、32 cm 查询半径和既有单目标/改造 AOE 分支；不把整把锤子的伸展距离额外加到技能射程，也避免从障碍物另一侧起查。
- 保留快速近战技能伤害、体力、削韧、击退、附魔、修炼和服务器结算。
- 身体动作标识改为 `WarhammerHeadThrust`，继续使用工具原生姿态链。

## 落盘

- 源：`SourceAssets/SteelWarhammer20261014/QuickCombatHeadThrustV3/author_head_thrust.py`；`author_quick_combat.py` 为兼容入口。
- 可编辑动画：`Warhammer_QuickCombat_HeadThrust_Editable.blend`；导出：`Export/A_Warhammer_QuickCombat.fbx`。
- `Before/` 保留替换前的正式序列、运行时代码以及 V1/V2 入口脚本。
- 实际制作参数、保存、构建、交付状态分别记录于 `authored.json`、`import_receipt.json`、`build_receipt.json`、`delivery.json`。只有对应实际回执代表完成。

正式动画已通过后台 commandlet 完成导入、动画编译与保存，版本 `HeadThrustV3_20261015`、`complete=true`。排队等待已有构建结束后，Editor 和 Game 正式构建均返回 exit 0、`Result: Succeeded`，本轮实际构建分别为 13.86 秒和 19.48 秒。V1/V2 制作与导入入口均已转向 V3，交付回执已写入磁盘。

按用户规则不追加运行、渲染或测试；关节外观、视野遮挡和打击手感由用户在游戏中体验。
