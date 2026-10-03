# 左手抬起瞬间握拳 V1

2026-09-23。先按用户指定制作独立动作；随后用户指定将其用于圣光自疗，接入说明见 `../../Docs/Skills/holy-light-self-fist-20260923.md`。保留当前 Manny 手臂与手套，独立源资产仍可继续复用。

## 参考与复用

- 主要手型来自 `SourceAssets/RuneSword20260913/FistBraceGuardV21/AzureRunesword_Manny_Editable.blend` 的 `A_RuneSword_Guard` 末帧。原动作 480 Hz、0–96 帧、0.20 秒，非循环；左拳抵剑、右手持剑。制作前读取了原动作实际姿态，并查看已有 `Review_FistBraceGuardV21/hold_firstperson.png` 源模型画面。它的空手拳形比握着圆柱握把的姿态更适合本次需求。
- 原参考四指收拢、拇指在外侧扣合。按源和目标的手掌解剖坐标转换指骨旋转，保留目标骨长、指骨位置、缩放；不复制剑、抵剑接触或右手动作。冻结输入见 `References/guard_fist_source.json`。
- 整臂借鉴 V21 已接受的腕肘衔接：以前臂变换沿最短转向建立上臂方向，锁骨支撑随之调整，蒙皮辅助骨跟随所属完整骨段，避免把旋转集中在腕或肘。
- 查阅了 `MannyGraspDonor20260912` 的 VRE GrabAnimation 来源、静态抓握数据及 `Delivery/Original_Donor.png`。该动作可供抓握参考，但原始是单帧抓握、UE 长度 1 秒，不包含抬手。Epic XR Grasp 的食指和拇指开放，未用作本次握拳目标。
- 查阅并沿用 `FireballCast20260914/author_cast.py` 的左臂独立制作、局部变换重建及连续曲线路线；查看其既有抬掌参考。没有修改现有火球动作。
- 手模及静止入场姿态来自 `GASPTraversal20260910/Native/TraversalArms_Editable.blend` 的 `M4_idle` 第 0 帧。以上均为项目已有素材，没有下载新素材。

## 动作节奏

| 时间 | 动作 |
| --- | --- |
| 0–0.045 秒 | 小幅下沉准备，松开原持握 |
| 0.045–0.225 秒 | 沿左侧短弧快速抬手并转向拳形展示方向 |
| 0.125–0.225 秒 | 四指迅速收拢；小指、无名指略早，拇指最后从外侧扣住 |
| 0.225–0.30 秒 | 握紧到位，整臂一次短促制动，位移小于 1.2 cm；不扭腕、不叠加镜头抖动 |
| 0.30–0.52 秒 | 稳定持拳，突出发力结束的停顿 |
| 0.52–1.00 秒 | 肩肘腕沿弧线收回，随后松指，回到入场姿态 |

配置使用相机空间厘米。抬手目标腕点为 `(34,-24,-12)`；掌向参考原 V21 的朝向，让拳面偏向玩家。`FistLocked` 是动作制作提示点，不是命中或技能成功事件。时钟参数可在 `motion_config.json` 编辑。

## 交付

- `LeftHand_PowerFist_Editable.blend`：当前 Manny 手模、四条动作、时间标记和源视角相机。原有参考资产没有改写。
- `Export/A_LeftHand_PowerFist.fbx`：完整动作，1.00 秒。
- `Export/A_LeftHand_PowerFist_Raise.fbx`：抬手、握紧与制动，0.30 秒。
- `Export/A_LeftHand_PowerFist_Hold.fbx`：0.50 秒稳定持拳，可由后续动作系统循环。
- `Export/A_LeftHand_PowerFist_Recover.fbx`：收手，0.48 秒。
- FBX 均以 300 Hz 烘焙、局部四元数连续插值，输出原骨架的动画轨道；右臂和武器轨道维持入场姿态。可编辑 Blend 保留现有手模网格。
- UE 已保存目录：`/Game/Animations/LeftHandPowerFist20260923`，四条动画均完成后台导入、压缩与保存，骨架为 `/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton`。本次 commandlet 退出码 0，`import_receipt.json` 状态为 `complete`，逐项记录保存结果；日志为 `import.log`。

接入应仅混合 `clavicle_l` 及其子骨骼，右手/枪械继续播放原动作；不要将完整双臂轨道直接全身覆盖到其他武器。圣光自疗现在由共用施法层按同源参数驱动，适配当前武器的骨架和进出握姿；对外圣光继续推掌。没有新增按键，也没有改动动作优先级。初次独立资产导入回执中的 `gameplay_hook_added: false` 是当时状态，后续接入以专项记录为准。

## 制作命令

在 Blender 5.1 后台执行 `author_power_fist.py` 生成源文件和 FBX，再用 UE 5.8 的 `-run=pythonscript -script=<import_power_fist.py 的绝对路径>` 无界面导入保存。导入脚本只创建本目录的新资产，使用现有视模压缩配置并等待压缩完成后保存；不会覆盖已有同名序列。

未打开交互编辑器、启动游戏、生成新预览或进行视觉/玩法测试。制作和保存完成不代表视觉验收通过，由用户测试。
