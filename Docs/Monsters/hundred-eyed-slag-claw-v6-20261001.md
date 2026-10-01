# 百目炉渣 ClawV6：普通攻击与大右臂蒙皮

2026-10-01。按用户认可的建议，用本机已有 `Mutant3_ClawC` 动作作为肩、肘运动供体，适配百目炉渣普通攻击的大右前肢。完成背景制作、FBX 导出、常规原生编译及背景资产导入保存；具体完成状态以 `ClawV6/installation_complete.json` 为准。未启动游戏、PIE、预览渲染或验收工具，由用户试玩。

## 普通攻击

- 原普通攻击以目标掌位驱动整条臂链；本次改用供体的肩至肘、肘至腕方向，按原绑定臂长重建姿态，肘部折角限制为 105 度。没有拉长骨骼或用掌位反向拉扯关节。
- 动作顺序为抬起大右手、向前斜向挥爪、收回原支撑垫。供体接触平面按怪物面向重新定向，使挥爪的主要接触落在正前方。腕部单独采用有限屈伸，爪指配合收拢。
- 骨盆、腰、胸与肩部配合移重，另外三肢使用原接触垫支撑。动作长度仍为 1.4 秒、30 fps，伤害窗口仍为 0.54–0.73 秒，半径仍为 48 cm 的实际掌部扫掠。
- 本次只导入替换 `AttackSweep_R`。抬手重击、奔跑、回程、特殊攻击、受击、硬直、眩晕和死亡的关键帧沿用当前版本。

## 右臂蒙皮

局部重新分配 12,121 个顶点；原几何、法线、UV、绑定姿态、骨骼父子关系保持，仍为 43 根作者骨、39 根变形骨、每顶点最多四个影响。没有新增骨骼。

局部权重从原 RuntimeV3 的解剖区域重新开始，将旧版本过高的辅助扭转比例降低：上臂扭转骨最高分走原上臂权重的 20%，前臂分段扭转按轴向连续分配，肘和腕辅助骨仅在关节附近参与，肩盖部分随肩臂运动。爪指原有独立权重保留；目标区域以外恢复原 V4 权重。Blender 使用线性蒙皮，避免双四元数预览掩盖 UE 的线性蒙皮变形。

## 跑近与站稳后攻击

`HundredEyedSlagMonster.cpp` 的原近战会在抬手前摇期间继续移动胶囊，动画支撑肢却保持接地。本次将这一段拆为奔跑接近：仍从 300 cm 范围接敌，按追击 340 cm/s 跑到约 130 cm，然后停止角色移动并从零开始播放攻击。

近战接近沿用 `Run` 循环；接近阶段不采样挥爪动画、不执行掌部伤害。到位后重置攻击计时和上一帧掌位，保持原伤害窗口；整个过程仍由同一忙碌攻击状态持有。撞墙、离地、目标高度差过大或接近超过 1.1 秒时结束这次接近。实际抬手与挥击阶段停步，保留前摇有限转向；特殊冲撞仍使用原角色移动和时段。

原 AggressionV5 的攻击冷却 1.25 秒、恢复 0.12 秒、远程和冲撞逻辑保持。死亡 0.42 秒转布娃娃和拟合物理资产保持。

## 资产与复现

制作目录：`SourceAssets/HundredEyedSlagMeshy20260930/ClawV6`。

- `extract_donors.py`：从本机已修正单位的 `Mutant3_OpenClaw_Animated.blend` 提取现有 ClawA / ClawC，实际使用 ClawC。
- `author_claw.py`、`HundredEyedSlag_ClawV6.blend`、`skin_weights.npz`：可编辑动作和蒙皮母版。
- `Delivery/SK_HundredEyedSlag_ClawV6.fbx`、`Delivery/Animations/A_HundredEyedSlag_AttackSweep_R_V6.fbx`：实际导出。
- `Rebuild.ps1 -Stage Authoring`：仅重制和导出；`-Stage Install`：编译并后台安装已有导出；默认两者。
- `native_build.json`、`mesh_installation.json`、`animation_installation.json`、`installation_complete.json`：构建和保存记录；`Before` 保存目标源码与旧资产。

保存到现有正式路径，两份网格镜像使用同一份新蒙皮：

- `/Game/Monsters/HundredEyedSlag/PolishV2/SK_HundredEyedSlag_V2`
- `/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1`
- `/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSweep_R`
- `/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1_Skeleton`

保留原皮肤材质、2K 纹理和高模烘焙法线、十万三角形 LOD0，从新蒙皮生成三档 LOD。原物理资产只复用，不重新拟合。F6 目录和原生类引用保持。

本轮未调用 Meshy。供体为本机既有 Epic Khaimera 派生资产；保留其既有许可和本机来源，不将源动作作为无版权或独立可再分发素材。
