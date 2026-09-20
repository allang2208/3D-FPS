# 双持快速近战 · 改造后保留转枪与 recover 腕臂 V5

2026-09-20。用户要求做一版保留改造枪转枪恢复的动作，同时优化 recover 手腕形变。本版以 VideoRefV3 的横击为源，替代 V4 对改造枪取消转枪的处理。

## 动作与配件分档

保留 0.80 秒总长、0.18 秒单次接触、左右主攻轮换。0.32 秒以后进入恢复调整：主手前送并外展，枪在食指接触点附近绕倾斜轴完整转一圈，再握紧收回。转枪发生在 0.435–0.675 秒；手臂自身不作整圈扭转。

| 轨迹 | 当前选择 | 作者外展 / 前送增量 | 转轴倾角 |
| --- | --- | --- | --- |
| compact | 裸枪、制退器、容量/数值改造 | 2.8 / 1.8 cm | M1911 38°；DW715 48° |
| wide，`_fitted` | 全息/全景镜、激光、手电 | 6.5 / 4.5 cm | M1911 64°；DW715 74° |
| long，`_long` | 普通/战术消音器；优先于其他配件 | 8.0 / 7.5 cm | M1911 78°；DW715 上限 82° |

倾角是从原横向转轴朝前臂方向倾斜的制作参数；长配件版本呈更明显的侧向转枪，枪口不会照搬原来经过腕部的大幅后翻路线。仍保留完整 360°，不是把转动幅度降为零。

这是针对现有配件类型的三套作者轨迹，不是按任意新网格实时求碰撞的系统，也不把一组参数称为所有组合均无穿模。已有 M1911 枪口长度定义作为分档参考；没有缩小配件、隐藏手臂或改变枪匠挂点。

两只手根据各自装配独立选择 profile；副手恢复阶段使用相同的延后回收时钟，不受另一把枪的配件类型影响。M1911 正常/空仓、DW715、双持同型及混搭均沿用原独立手配置。

## recover 腕臂处理

旧 V3 把前臂及两根 lowerarm twist 都按持枪手掌的朝向一起旋转，腕部折角与整段扭转没有分别分配。

- 固定骨段长度，在可达肘圆上有限调整肘方向，优先给腕部提供自然支撑，不强制两侧对称。
- recover 对手掌方向的修正同时作用于未翻转的枪体基准，保留握住时的枪根相对手掌矩阵；不是单独把手腕拧离握把。
- 前臂方向与手骨 rest 轴之间的角差用于作者约束，目标 24°、单次校正上限 65°；它们是该 rig 的制作参数，不是人体医学关节限位或已通过的验收数值。
- 上臂有限分担轴向旋转，肘侧跟随上臂支撑。根据原 Manny 蒙皮的辅助骨分布，将扭转逐渐传到腕侧，所有辅助骨位置随完整骨段搬运。
- 转枪时放松拇指、中指、无名指与小指；食指接触点作为枪体转轴中心。拇指先接柄，其余手指随后合拢。恢复修改在交回 idle 前平滑退出，首尾回到各枪各手原待机。
- 副手恢复最多延后 55 ms，给主手的转动留出时间和空间。击打段、伤害、输入门槛、冷却、弹药事务、镜头与音效逻辑保持原合同。

## 文件

- `prepare_author_geometry.py` / `author_geometry.json`：读取既有四套作者源与 Manny 前臂蒙皮辅助骨位置，供制作使用，不运行验收。
- `recovery_solver.py`：三个 profile、腕部与肘位配合、分段扭转、分指回握和倾轴转枪。
- `author_actions.py -- M1911|DW715`：只复用 V3 的纯函数与参数，不执行或覆盖旧作者脚本。生成四份完整 Blend、36 条 120 Hz FBX。
- `<Weapon>/<side>/`：可编辑 Blend 和 `Animations/` 导出。
- `import_assets.py`：导入新的 `/Game/Weapons/DualPistolQuickCombat20260920/SpinRecoveryV5` 目录，逐条保存回执，不覆盖 V3/V4。
- `Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp`：加载 V5，分别选择 compact / fitted / long；近战识别包含整个 quickcombat 动作家族。
- `Before/PistolDualWieldComponent.cpp`：本轮修改前的完整文件快照，仅供定位本轮修改，不能整文件回滚覆盖后续并行改动。

仅进行制作、导出、导入与必要编译，不运行新测试、PIE、截图或验收渲染。自然程度、实际装配穿插与动作手感由用户试玩；本版是供体验的候选，不宣称全部配件组合已通过验收。

接入状态另见 `import.json`、`compile-result.txt` 与 `integration-status.json`。Live Coding 成功只代表当前编辑器补丁生效，不代表基础 Editor DLL 已常规重编译。

本次已完成：36 条动画保存、运行分支接入，`LiveCodingToolset.CompileLiveCoding` 返回 `Result: Success` 和 `Live coding succeeded`。保存前结束了原 PIE，编辑器保持打开；未启动新的试玩。用户重新进入试玩后加载 V5 候选。

整理记录：本文的 `Before/` 旧覆盖快照已移至 `trash/dual-melee-overhead-retired-20260920/SourceAssets/DualPistolQuickCombat20260920/SpinRecoveryV5/Before/`；恢复以 `Docs/Rejected/dual-melee-overhead-retired-20260920.json` 为准。保留源与最新安装顺序见 `Docs/Weapons/dual-melee-overhead-publication-20260920.md`。历史回执不改写为本次测试结果。
