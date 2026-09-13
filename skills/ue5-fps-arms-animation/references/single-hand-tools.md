# 单手采集工具：包握、发力与命中恢复

用于斧头、十字镐等第一人称单手工具。FPSGAME 的 2026-09-13 案例已导入并完成普通构建，尚未做游戏内测试；其数值属于当前制作参数，不是用户已接受的视觉标准。遵守当前用户的测试授权范围。

## 先固定接触，再制作挥击

- 先读已有动作的帧率、接触时间和循环方式，并查看已有参考画面。静态抓握源只提供手型，剑的挥砍源只提供运动参考；不能称为自动得到适合斧头或矿镐的完整动作。
- 复用当前 Manny 手臂与已接受的整手包握。左右手迁移依据解剖方向及 rest 坐标系，保留手指局部关节位置、骨长、缩放和权重。具体方法见 [GitHub 抓握迁移](github-grasp-donor.md)。
- 握点取木柄实际截面的中心，不能使用包含工具头的总包围盒中心。弯斧柄尤其需要沿目标高度取截面；握点、握向和大小按每个模型适配。
- 在准备姿态选择圆柱握向，并在整次挥击中保持手相对工具的变换。不要逐帧重新选择最优握向，否则容易换握、跳转或滑手。此例以工具和手掌共用变换制作，工具刚性绑定 `WPN_root`。
- 联动肩、肘、前臂和 twist 辅助骨，避免只扭手腕追工具。求解保留上臂、前臂长度，扭转角跨越正负 π 时连续展开；按辅助骨位置分配扭转。左臂自然下垂并轻微平衡，单手动作不自动增加左手扶柄。

## 力度来自接触前后的时间差

区分起势、加速、接触制动、退开和回收。斧头可用斜劈，十字镐可用抬高下砸；根据工具头和玩家构图设计轨迹，不把同一条剑动画仅换网格。

以现有采集时钟驱动姿态、挥动声、资源结算和命中声。成功提交采集才切入命中恢复；无有效资源、工具不匹配或提交失败时继续空挥。动画不额外结算一次奖励。

本案例保留总长 `0.68 s`、接触 `0.24 s`：`0–0.13 s` 起势，`0.13–0.24 s` 加速。命中后斧头停留约 `33 ms`、矿镐约 `47 ms`，随后轻微回弹并回收；空挥顺势挥过。短暂停留只作用于视模，不使用全局时间膨胀或暂停采集计时。这些数值需要按新工具与实际观感重新选定。

独立 `HitRecover` 的首姿态与 `Swing` 接触姿态采用同一作者变换，结束回到同一待机。挥动声略早于接触，重击声和原粒子在采集提交时触发。避免为了力量感叠加多个互不一致的手、工具和镜头震动时钟。

## 烘焙、导入与运行

- 此例每工具使用 Idle、Walk、Equip、Swing、HitRecover 五条动作。选择能准确覆盖接触与结束时间的烘焙帧率；这里的 `150 fps` 使 `0.24 s` 和 `0.68 s` 落在整数帧，并不要求所有项目都用 150 fps。
- 烘焙帧率不等于运行求值频率。当前组件只在切片时调用 `PlayAnimation`，停止自动播放并按统一时钟 `SetPosition`，每游戏帧求值一次；不要再开启第二套动画 Tick 重复推进。
- 只为当前装备异步加载网格、五条动作、声音和原粒子。切换物品取消旧请求并核对回调归属，完整资源就绪后进入装备动作；菜单、死亡、攀爬、建造或收起时停止视模求值。
- 地面掉落仍用已有静态网格/LOD，第一人称独立使用带手的骨骼视模；旧存档通过物品定义归一化补齐外观字段，不替换物品 ID、采集次数或奖励。
- 静态工具材质复制成视模专用材质并启用 skeletal mesh 用途；按材质槽名复用当前手臂材质，避免依赖不同 FBX 的槽序号。保留原静态材质供掉落使用。
- 当前 UE 5.8 Python 的动画采样设置通过 `set_editor_property('use_default_sample_rate', False)` 和 `set_editor_property('custom_sample_rate', 150)` 赋值；直接属性赋值在本例失败。保持作者、导入采样和压缩设置对应。
- 若 commandlet 明确卡在重复 SDK 探测且另一构建持有锁，可参考本例的 `-Multiprocess` 导入调用；它不替代普通模块构建，也不解决真实的 SDK 缺失。原生构建仍使用工程 `Tools/Build/Build-Editor.ps1` 的编辑器关闭约束。
- 分别记录脚本成功、进程退出码和普通构建结果。本例 Python 导入成功，但 commandlet 因已有 GameFeatureData 配置问题返回 1；不能写成整工程无错。导入器重建 bind pose 也不代表蒙皮观感已验收。

## 现有入口与来源

工程根 `D:/FPS3D/FPSGAME` 下：

- 作者：`Tools/Production/build_tool_grip_motion.py`；导入：`Tools/Production/import_tool_grip_motion.py`。
- 运行：`Source/FPSGAME/Production/ProductionToolComponent.cpp`、`ProductionToolMotion.cpp`；定义：`Content/ColdSteelData/production_tools.json`。
- 源与参数：`SourceAssets/ProductionToolGrip20260913`；UE 资产：`Content/Items/ProductionTools/GripMotion20260913`；恢复依赖与交付边界：`Docs/ProductionToolGripMotion-20260913.md`。
- 抓握母版依赖 `MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend` 及该案例的 80% 闭合拟合记录；不将此例的握点或 roll 角直接套给另一工具。

[Unity-First-Person-Melee 固定提交](https://github.com/BigAndCrispy/Unity-First-Person-Melee/tree/592b08e2e1fe81a51f712fa65d806fa3621e2032) 的作者模型、声音和动画为 CC0，本例少量采用待机轨迹与挥动声；主要工具挥击重新制作。[UnrealMeleeAnimationHelpers](https://github.com/Redesigner/UnrealMeleeAnimationHelpers) 的接触窗口、[ProcHitReact](https://github.com/Vaei/ProcHitReact) 的停留/回收及 [MotionExperiments](https://github.com/josimard/MotionExperiments) 的恢复思路仅作参考，没有安装这些插件。

代码仓库许可、声音许可和 Manny/Fab 美术许可分别记录。公开制作脚本及参数不表示可以公开派生手臂、纹理或整套 FBX；保留本机可编辑源和来源，不把仍被作者脚本使用的母版移入 trash。
