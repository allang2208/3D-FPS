# 犬类 Gallop V3：找回 Godot 动作并实际替换

> 2026-09-25 整理：下文保留当时制作/诊断记录，旧路径不再表示现役入口。当前模型、动作、归档映射和恢复顺序见 [感染犬发布记录](InfectedDogPublication20260925.md)。

**当前状态：V3 已被用户否决并撤回（2026-09-24）。** 用户指出对照图右侧新动作存在错位、穿模，左侧旧动作更正常。已通过后台 commandlet 恢复野狼、僵尸犬、感染犬和母版的原 Run、RunTurnLeft、RunTurnRight，并恢复替换前的 RunSpeed 与走跑混合参数，四个数据集均已保存。恢复记录为 `SourceAssets/CanineGallop20260924/restoration.json`，工具为 `Tools/WolfMonster/restore_previous_canine_run.py`。V3 源文件仅保留供追溯，不作为成功重定向案例；原安装脚本已阻止重新启用该失败版本。本次恢复没有重新运行游戏或渲染。

下面保留的是制作及数据检查历史。关键帧、压缩误差、接缝与保存检查通过，并未覆盖蒙皮错位和肢体穿插问题，不能作为动作视觉合格的依据。

日期：2026-09-24。用户反馈当前犬类奔跑僵硬，要求查找旧 Godot 调整记录、检查并升级替换。

## 旧记录与原因

旧 Godot 工作目录已经不在历史文档指向的位置，但 Git 标签 `archive/godot-before-ue5-20260910`（提交 `49cec1dd11d65295f43c737bac327de829cfd7b1`）保留了完整资料。本次按单文件读取归档，没有切换工作区分支或覆盖当前工程。

- `assets/models/wolf_quaternius.gltf`：51 骨、12 动作，含完整 Gallop，17/30 秒。
- `scripts/wolf_anim.gd`：旧运行脚本实际播放完整 Gallop，没有使用备用的对角正弦程序步态。
- `tools/ai-gen/black-wolf-fur-v01-20260906/Gallop-frames-*.jpg` 和 README：旧连续姿态与制作记录。
- 2026-09-15 的 [Locomotion V2](QuadrupedLocomotionV2.md) 已落盘的是走跑混合区间、步频和转向参数；当时没有把 Godot Gallop 迁移为 UE 新片段，所以正式奔跑仍引用旧 Run。不是旧记录完全丢失。

找回素材的原作者为 Quaternius，官方 [Ultimate Animated Animal Pack](https://quaternius.com/packs/ultimateanimatedanimals.html) 标明 CC0，可用于个人和商业项目。本次恢复本地历史文件，无需下载替代包。目标模型仍沿用现有狼资产的原始来源和许可，CC0 不改变目标模型的许可。

## 新动作

保存目录：`/Game/Monsters/QuadrupedTemplates/WolfV3/Animations`。

| 动作槽 | 新资源 |
|---|---|
| Run | A_QP_Wolf_Gallop_Run |
| RunTurnLeft | A_QP_Wolf_Gallop_RunTurnLeft |
| RunTurnRight | A_QP_Wolf_Gallop_RunTurnRight |

将源 Gallop 的脊背、肩颈、前后肢和尾部运动转移到现有 34 骨骨架。目标骨长、网格和蒙皮保持；前肢使用两段 IK，后肢保留 HorseLink 三段链。按源足端轨迹处理支撑和收腿；源运动超出目标腿长时限制到可达范围，不拉长骨骼。头部没有对应源骨的附件保留现有 Run 的局部运动。

左右转向由同一新 Gallop 派生，增加向弯内的身体倾斜和头颈朝向，并约束足端保持同一相位，不再混入旧 RunTurn。根容器保持原地，关闭 Root Motion，角色移动仍由现有 AI 和 CharacterMovement 驱动。

周期 0.566667 秒，编辑源与平台采样均为 60 Hz、35 个采样点。新步幅参考由适配后支撑足后移速度的中位数计算：约 164.78 cm/周期，对应参考速度约 290.79 cm/s；写入数据集 RunSpeed 以驱动动画相位。这不是角色追击速度，角色移动数值未改。走跑切换比率继续使用 0.35/0.65。

实际更新四个数据集：

- `/Game/Monsters/QuadrupedTemplates/WolfV1/DA_QP_Wolf_AnimationSet`
- `/Game/Monsters/Wolf/DA_Wolf_AnimationSet`
- `/Game/Monsters/ZombieDog/RefinedWoundsV5/DA_ZombieDog_RefinedWounds`（从现役 BP_ZombieDog 的 CDO 读取）
- `/Game/Monsters/InfectedDog/DA_InfectedDog_AnimationSet`

保留 18 个其他动作槽及攻击接触窗口，保留三个角色的现役网格与材质；六维属性、感染、AI、受击、死亡和战斗时钟未改。

## 制作资料和检查范围

`SourceAssets/CanineGallop20260924` 保存恢复的 glTF、原预览、源采样、重定向关键帧、3 个 FBX、可编辑 Blender 预览、安装记录、原数据集备份和检查结果。不是仅保存脚本。

工具位于 `Tools/WolfMonster`：

1. `read_gallop_upgrade.py`：读取当前 BP 引用、原动作和绑定姿态。
2. `sample_recovered_gallop.py`：以 30 fps 导入历史 glTF，按 60 Hz 提取源动作。
3. `retarget_recovered_gallop.py`：语义骨链适配、足端约束、左右转向与新步幅测量。
4. `preview_gallop_upgrade.py`：当前感染犬模型的同视角旧/新动作及转向预览。
5. `install_recovered_gallop.py`：保存 UE 片段，备份并更新现役数据集。
6. `save_gallop_sampling.py`：统一平台压缩采样并重新保存导出。
7. `check_saved_gallop.py`：按用户本次要求检查骨架、源关键帧、循环接缝、绑定和其他动作槽。

背景制作过程中已有其他来源启动的 UE 编辑器，后续资源接入沿用项目 MCP 桥互斥执行；本任务没有启动或关闭交互编辑器，没有启动或停止游戏。最后采样设置保存曾被 PIE 阻止；用户结束试玩后已经继续保存。

本次做了离线模型连续帧对照与 UE 动画数据回读。预览 GIF 按归一化周期慢放，使用 Blender 评审灯光，不是 UE 游戏画面或战斗验收。足端约束是离线平地适配，未宣称实现运行时地形 IK。实际追击、坡地、攻击切换手感仍由用户在游戏中确认。

最终记录：三个片段与四个数据集均保存为 uasset；`sampling-live-04.txt` 记录三个片段各 35 个平台采样点，`check-live-04.txt` / `saved_asset_check.json` 记录检查通过。最终检查在非试玩状态重新加载了三个已保存动画包，包含压缩后姿态对照和未保存修改状态。压缩后最大局部位移误差小于 0.008 cm、旋转误差小于 0.152°，循环端点匹配；没有中断试玩。
