# 裸皮感染犬：Godot 原 Gallop 直接适配 V2

2026-09-24，用户要求排查受击血液方块，以及 Godot 正常而 UE 跑姿别扭的问题。本目录记录替代 FoxRunV1 的首个 Godot 直接适配版本。没有重新启用被否决的 WolfV3 重定向结果。

用户随后反馈有所改善，要求继续自然化；当前奔跑入口已升级为 [GodotRunNaturalV3](../GodotRunNaturalV3/README.md)，本版本作为改善基线和回退版本保留。下文接入与核对结果为本版本安装时的记录；全量重装后的最终奔跑入口应使用 `Tools/InfectedDog/install_godot_run_natural.py`。

## 来源和改动

取回旧 Godot 实际使用的 Quaternius `wolf_quaternius.gltf:Gallop`，51 骨、17/30 秒完整循环；播放脚本为 `wolf_anim.gd`。来源是工程归档提交 `49cec1dd11d65295f43c737bac327de829cfd7b1`，原作者 Quaternius，CC0，<https://quaternius.com/packs/ultimateanimatedanimals.html>。有效原始输入独立保存在 `Source/`，不依赖旧 WolfV3 的失败重定向或预览。

当前裸皮犬有自己的 41 骨绑定，不能直接复用源骨骼的局部旋转。此次从原始世界空间采样直接适配目标：

- 脊柱、头颈及脚掌按实际骨段方向拟合，保留目标绑定的骨长和滚转基准。
- 前肢双段求解限定肘部向后弯曲，后肢限定膝部向前弯曲。跗关节优先沿源方向；腿长不同时在足端固定的条件下拟合跗关节位置，避免无约束三段链翻折。
- 目标静立绑定接近伸直，奔跑姿态增加 7.5 cm 的屈腿余量；前后足端行程按 0.9、横向按 0.35 适配更窄的裸皮犬。保留原动作的支撑顺序、起伏和腾空。
- 60 Hz 烘焙、35 个样本，末帧与首帧相同。四足不可达残差最大约 0.222 mm；这是离线求解误差，不等于实机接地/穿模验收。
- 动画步幅参考为 271.8687 cm/s，仍由现有移动速度驱动相位。角色追击速度保持 400 cm/s，所以实机并非固定 1 倍速；旧 Godot 脚本是固定 1 倍速。
- 模型、材质、骨架参考姿态、权重、物理资产和战斗数值均不改。

## 已保存的入口

`/Game/Monsters/InfectedDog/MeshyV2/GodotRunFitV2/A_InfectedDogMeshy_GodotRunFitV2`

正式 `DA_InfectedDogMeshy_AnimationSet` 中 Run、RunTurnLeft、RunTurnRight 共用此循环，转向由角色驱动。其他动作包括奔跑咬击、扑咬、受击和死亡的引用、播放字段、命中窗口不改。

`InfectedDog_GodotRunFitV2.blend`、同名动作 FBX、`authoring.json` 为制作源；`installation.json` 为实际保存回执。替换前 Fox 引用和数据资产备份保存在 `binding_before.json`、`DA_InfectedDogMeshy_AnimationSet.before.uasset`。

生产入口：`Tools/InfectedDog/author_godot_run_fit.py`、`install_godot_run_fit.py`。后者复用 `install_canine_run.main` 的动画单独导入、根单位修正和有限槽位更新，不导入网格或修改其他角色。重新执行 CompletionV2 全量安装后，应最后执行 GodotRunNaturalV3 安装入口；FoxRunV1 已移入 trash，不是重建依赖。

## 本轮针对性核对

用户授权排查，因此执行了离线姿态/权重分区检查及独立 UE 进程的保存后回读。35 个姿态 × 41 骨，源数据与 Blender 骨点最大误差 0.000081 cm，压缩数据最大误差 0.283 cm；非奔跑动作合同保持，读取无失败。记录见 `../RunBloodDiagnosis/saved_readback.json`。

离线侧面诊断图位于 `../RunBloodDiagnosis/godot_fit_*.png`，是 Blender 灰模灯光下的姿态对照，不是 UE 游戏截图。未启动游戏或 PIE；没有宣称完成动态穿模、地形接触、攻击切换或整体观感验收。
