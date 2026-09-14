# 胖子僵尸瞬移与动画断裂修复 · 2026-09-14

用户在开发面板生成胖子僵尸后发现瞬移、动作无法连贯。本次按该反馈排查并修复动画数据和状态切换；未启动游戏进行视觉或实战复测。

## 首个错误与证据

预期：F6 生成的 `AFatZombie` 由 CharacterMovement 移动，原地动作只产生体内重心变化，待机、追击、攻击和死亡连续过渡。

排查顺序为动画内部位移、状态硬切、AI 移动。最早的错误已经存在于交付 FBX 的 `Hips` 键中，无需 AI 移动即可出现。UE 导出原始动画在 Blender 世界坐标中已经以米表示，但 `fit_body_animation.py::source_pose` 又使用目标/导出参考骨架位置长度比乘了 100。错误缩放令骨盆偏离胶囊数米；死亡起始骨盆高度甚至达到约 92 米。`force_root_lock` 只锁住外层 `FatZombieRoot`，无法消除子骨 `Hips` 的位移。

初始游戏四个动画文件与制作工程对应文件的 SHA256 完全一致。使用 Blender 读取交付 FBX，并使用 UE 的 `AnimPoseExtensions` 读取 Compressed 数据；两条路径均显示同类异常。第二个问题是角色继承护士的 `PlayAnimation` 状态硬切，没有从当前姿态过渡。

## 修复

- 制作脚本删除重复的参考尺寸缩放，直接使用已转换为米的重定向世界坐标。保留原网格、蒙皮、骨架、材质以及四段动作时长，重新进行体型适配和接地烘焙。
- Idle、Walk 终端键恢复到首帧姿态，避免体型适配产生循环接缝。重新输出可编辑 Blender 文件和四段带蒙皮 FBX，导入同一个 UE Skeleton，替换游戏中的原动画路径。
- 新增 `UFatZombieAnimInstance`，以当前可见姿态快照和 Sequence Evaluator 进行约 0.2 秒混合。中途打断时捕获当前混合结果；恢复循环时保留播放进度，行走播放速度平滑跟随移动速度。
- 攻击仍使用原近战 `StateTime`，命中窗口保持 1.00–1.18 秒。动画图不产生额外命中事件或根运动。无专用受击片段时保持当前姿态；死亡从当前姿态过渡，单次播放后保持末帧。
- 修改范围仅为胖子角色、专用动画实例和四段动画及制作脚本；未改护士、手脑、毒蛆的状态切换实现，也未修改共享 AI 决策或导航规则。

## 动画数据读回结果

使用相同 UE 压缩姿态采样方法，采样间隔为 1/120 秒，坐标单位为厘米。这是动画数据排查结果，不代表游戏帧率或视觉验收。

| 项目 | 修复前 | 修复后 |
| --- | ---: | ---: |
| 待机骨盆前后摆动范围 | 173.04 cm | 1.74 cm |
| 行走骨盆左右/前后范围 | 751.53 / 950.24 cm | 7.54 / 9.54 cm |
| 行走骨盆最大单步位移 | 32.03 cm | 0.90 cm |
| 攻击骨盆最大单步位移 | 198.75 cm | 2.30 cm |
| 死亡起始骨盆高度 | 9207.13 cm | 94.33 cm |
| 行走骨盆首尾误差 | 0.59 cm | 0.031 cm |

待机首尾误差为 0；行走烘焙终端姿态相同，UE 有损压缩后骨盆误差约 0.31 mm。死亡保留正常后倒轨迹，不做循环首尾对齐。

结果文件位于 `Saved/FatZombieContinuity`：`delivered_fbx_before.json`、`ue_compressed_before.json`、`ue_compressed_after.json`、`delivered_fixed_assets.json`。四个游戏动画文件与本次读回的修复资产散列一致。

`FPSGAMEEditor Win64 Development` 和 `FPSGAME Win64 Development` 均构建成功，日志为 `Saved/Logs/FatZombie-continuity-Editor-build.log` 和 `FatZombie-continuity-Game-build.log`。没有启动游戏复测，也没有执行其它怪物或玩法的回归。

## 使用与恢复

保存并重启编辑器，重新进入游戏，通过 F6 面板清除旧实例并生成胖子僵尸。用户复测重点为持续行走、接近玩家切入攻击、受击后恢复以及死亡过渡。

源文件保持在 `SourceAssets/FatZombieMeshy20260913/FatZombie_Meshy_Animated.blend`，FBX 在同目录 `final`；错误版本原先保存在 `repair_20260914/before`，现已移入 `trash/fat-zombie-workflow-20260914/SourceAssets/FatZombieMeshy20260913/repair_20260914/before`，附原始路径和散列清单。用户提供的模型 ZIP 与原始绑定源文件未改动。2026-09-14 用户已确认整体流程成功，见 [最新整理记录](fat-zombie-workflow-publication-20260914.md)。
