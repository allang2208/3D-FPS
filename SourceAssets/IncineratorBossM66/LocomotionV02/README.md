# M66 焚骸：待机、移动与导航 V02

当前后续阶段已扩展至 [ReactionsV03](../ReactionsV03/README.md)，开启受伤并加入硬直、眩晕、击飞/落地/起身、死亡。下文保留 V02 当时的阶段范围。

2026-10-14 已完成制作、常规 DLL 构建和实际后台导入保存。`Saved/BuildEditor/build-20261014-180743.log` 返回 `Result: Succeeded`，`Records/install-20261014-181300/engine.log` 对应 commandlet 退出码 0。四段动画已保存至 `/Game/Monsters/IncineratorBossM66/LocomotionV02/`；原蓝图已保存为 `M66IncineratorMonster` 的子类，使用 `M66MovementComponent` 与 `M66AnimInstance`。完整交付回执为 `Records/completion.json`。未启动游戏或进行联机/视觉测试。

输入沿用 `../MeshyRigV01/Authoring/M66_back_completed_v01.blend` 的 88 根骨骼、用户原网格、UV 和材质。此阶段制作待机、行走、原地左右转身，并将原 F6 模型入口升级为有导航行为的角色；不新增攻击、死亡、奖励或焚化区遭遇。

## 动作制作

`author_locomotion.py` 制作 M66 体型专用循环，采用原骨架实测的髋/膝/踝位置进行双段腿部求解。没有套用其他怪物的攻击动作，也没有重新生成模型。

| 片段 | 长度 | 制作基准 |
| --- | --- | --- |
| Idle | 4.8 秒 | 双脚承重，骨盆和脊柱轻微移重；四块背囊错相呼吸，排热骨链迟滞微动；巨臂和小臂保持各自姿态 |
| Move | 2.4 秒 | 原地步态，每循环对应 144 cm 前进；62% 单脚支撑区间、平滑抬脚/回落，最高抬脚 13 cm；巨臂从肩到腕错峰摆动 |
| TurnLeft | 2.4 秒 | 每循环对应左转 60 度，两脚轮流支撑，支撑脚位置与朝向补偿身体转动 |
| TurnRight | 2.4 秒 | 右转 60 度，沿用同一相位与左右承重关系 |

动作以 60 FPS 烘焙，循环末帧回到首帧姿态。根骨保持原地；行走支撑段的脚相对身体匀速后移用于抵消真实前进，摆动、抬脚、身体移重和附属组织采用非线性曲线。源速度 60 cm/s 是步幅基准，运行速度改变时不修改该基准。

输出：`Authoring/M66_locomotion_v02.blend`、`Export/A_M66_*_V02.fbx`，制作清单为 `Records/animation_manifest.json`。

## 运行接入

- `AM66IncineratorMonster` 使用现有 `AMonsterAIController` / 行为树，支持等待、巡游、视线发现玩家后的跟随、近距离停止、失去目标及超距返回。当前阶段关闭受伤和攻击，没有占位伤害/死亡行为。
- 继续使用 `/Game/Monsters/IncineratorBossM66/BP_M66RigPreview` 原蓝图路径和 `IncineratorBossM66Rig` 稳定 F6 ID，重设父类及动画/控制器。显示名变为“焚骸 M-66（待机·移动）”。
- 导航复用工程已有 `M10Mawcrawler` 大体型规格：半径 225 cm、高度 450 cm、台阶 40 cm；角色实体胶囊半径 100 cm、半高 190 cm。没有追加 SupportedAgents 或改动已有导航 Bounds Mask 索引；仅在具有对应导航覆盖且实际净空足够的位置生成。
- 胶囊位于实际双脚支撑中心，Mesh 根据原骨架踝部中心对齐，避免不对称巨臂导致包围盒中心偏移。
- `UM66MovementComponent` 负责唯一转向：大角度先减速/原地换步，方向接近后再前进；继承已有怪物胶囊跨阶与 Mesh 高度平滑。
- `UM66AnimInstance` 按呈现网格的实际支撑中心位移和角度推进同一循环相位。模型原点绕支撑中心旋转不被错误计为前进；自然吸收联机 Mesh 平滑，堵住时不按期望速度继续踏步。待机/移动/转向连续混合，不在状态切换时从第零帧重启步态。
- `FMonsterSurfaceGroundingNode` 接入实测双足链：`Bone_012 → Bone_011 → Bone_010` 和 `Bone_017 → Bone_016 → Bone_015`。共用已有地面采样、脚底法线适配和骨盆/双腿调整，不增加逐足独立 Actor Tick。
- 服务端负责目标与导航、角色位置/朝向复制；客户端仅根据已复制运动播放本地动画，不重复寻路。

## 导入与保存顺序

1. 运行 `author_locomotion.py` 导出四段动作。
2. 必要的普通 `FPSGAMEEditor` DLL 构建。新增原生类型不得只依赖 Live Coding 就保存为蓝图父类。
3. `import_motion.py` 将四段 FBX 导入原 Skeleton，保持与网格相同的 ForceFrontXAxis 约定，等待动画编译完成，再按原骨架修正 FBX 根单位、保存。
4. `install_character.py` 将原蓝图重新继承到 M66 原生角色并保存网格、动画类、移动、导航、控制器与阶段属性。编辑器关闭后可用 `install_headless.py` 进行实际后台导入与保存。

实际导入/保存回执为 `Records/motion_import.json`、`Records/character_install.json`。导入过程中修正了 FBX 动画长度参数的 Python 写入方式；最终导入正常结束，四段动画的根骨单位与原骨架一致，无需额外缩放。未启动游戏、联机测试、自动化测试或验收渲染，用户测试后再确定动作观感和具体区域通行效果。
