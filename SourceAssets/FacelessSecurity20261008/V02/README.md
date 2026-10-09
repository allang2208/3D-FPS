# 无面安保 V02：男性动作与发力节奏

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

本版已由 [V03](../V03/README.md) 替代。用户要求继续采用僵尸动作，且反馈出生后手脚不可见；V03 使用 Idle_A／Walk_A／Attack_D，并重建靴体与完整显示副本。本目录仅保留历史。

日期：2026-10-08。按用户反馈，将 V01 的女僵尸同源待机、行走、攻击替换为项目已有男性动作来源，并调整安保的力量感。衣物和身体继续使用 V01。

## 动作来源与制作

| 动作 | 实际来源 | 本次处理 |
| --- | --- | --- |
| 待机 | `/Game/AsianMale_Jason/Demo/Animation/AS_Jason_Idle` | 男性站立待机，保留呼吸和微动，增加轻微前倾准备姿势和肩部整臂余量，闭合循环。 |
| 行走 | `/Game/AsianMale_Jason/Demo/Animation/AS_Jason_Walk_Fwd` | 保留男性步态、骨盆和摆臂关系，匹配当前移速与播放倍率，闭合循环。 |
| 攻击 | `/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D` | 保留踏步、转体、抬臂和下劈挥击的整身配合；蓄力较慢、挥击短促，随后按躯干、肩臂、手部顺序返回男性待机。 |

Jason 源网格为 `/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body`，攻击源网格为包内 `SK_Manny_Simple`。复用本机已有素材；未购买、调用生成 API 或公开分发资源。只查看了已有的 Attack_D 分帧参考，没有新渲染。

两套源动作先经 UE 原生 IK Rig / IK Retargeter 转到 `SKEL_FacelessSecurity`。四肢与手指采用对应关节旋转映射，然后离线制作整臂避让、鞋底支撑、循环端点和攻击时间曲线。保持目标原绑定骨长；米制作者计算和 FBX 厘米键值分开换算。没有重新绑骨、改变服装权重或增加运行时 IK。

## 节奏与玩法时钟

- 待机 7.5667 秒；行走源片段 2.7333 秒；攻击重编为 2.30 秒。
- 攻击命中窗口约 0.5896–0.7859 秒，对应源动作约 0.47–0.73 秒的落步挥击段。
- 1.18 秒之后开始分部位收势，手部略晚，2.30 秒回到男性待机；攻击结束后的额外冷却为 0.38 秒。
- 安保移动速度从原 52 cm/s 调为 78 cm/s。
- 当前 `ANurseZombie::Tick` 的行走播放倍率为 `速度 / 26`，上限 3.5。本轮保留共享 C++，只在新行走资产设置 `RateScale = 26 / 234.50875 ≈ 0.11087`，其中分母来自制作姿态中支撑脚的后移速度估计。在 78 cm/s 时，合成播放倍率约 0.3326。该数值是动画制作匹配参数，不是实机滑步测试结果。
- 保留生命、攻击伤害、攻击距离、现有导航胶囊、碰撞与 AI；没有新增安保技能或替换死亡体系。

## 实际保存

本轮最终导入进程正常退出，实际保存以下 4 个正式资产：

- `/Game/Monsters/FacelessSecurity/Animations/V02/A_Security_Male_V02_idle`
- `/Game/Monsters/FacelessSecurity/Animations/V02/A_Security_Male_V02_walk`
- `/Game/Monsters/FacelessSecurity/Animations/V02/A_Security_Male_V02_attack`
- 原 `/Game/Monsters/FacelessSecurity/BP_FacelessSecurity`，已切换三段动作及配套时钟。

F6 → 无面安保入口不变，重新生成角色使用新默认值。身体、服装、材质、蒙皮、物理和 V01 网格引用保持。没有修改 C++，没有触发原生构建。

作者文件为 `Motion/FacelessSecurity_MaleMotion_V02.blend`，3 个动作存于静音 NLA 轨；同目录保存三段动画 FBX。`motion_manifest.json` 是最终制作参数，`ue_delivery.json` 是正式资产保存回执。`Before/` 保留修改前蓝图副本和动作／时钟记录，V01 原动作资产仍保留。

## 执行边界

未打开 UE 图形编辑器，未运行游戏／PIE、渲染、自动测试或动作验收；力量感、服装变形和移动效果由用户体验。

原生重定向阶段已经写出 3 个 Raw 动作、FBX 和姿态缓存，随后 commandlet 在退出阶段出现动画压缩任务仍在执行的断言，进程码 1。这个阶段不记为正常退出，也未据此重放已完成写入。最终正式 FBX 动作导入是独立进程，正常完成保存并以进程码 0 退出；本轮未追加保存后读回测试。

重建脚本：`Tools/FacelessSecurity/retarget_male_v02.py` → `author_male_v02.py` → `import_male_v02.py`。中间重定向资产位于同角色 `Rig/V02` 和 `Animations/V02Raw`，正式蓝图只引用 `Animations/V02` 成品。后续仅重做节奏时可从已保存 Native 缓存继续，不必重复原生重定向。
