# Super90 战术冲刺左臂返工：运行时混合轨道

用户在 NativeHingeR2 后仍反馈战术冲刺左手错误弯折，要求参考其他枪械排查调整。

## 确定的运行时问题

`FPSGAMECharacter.cpp::UpdateActionPose` 先调用 `UM4TacticalSprintComponent::Apply`，配置完整的进入轨道、连续进度和循环权重；随后 Super90 专属普通走跑分支无条件覆盖 `SprintClip`、`SprintTime`、`SprintAlpha`，但没有覆盖 `SprintLoopClip` 与 `SprintLoopAlpha`。

`FPSGunplayAnimInstance.cpp` 的 `SprintMotionBlend` 正好把这些通道进行局部骨骼混合：实际输入变成原生双手 run/walk 与战术单手竖枪 loop。进入/退出时无法完整播放 NativeHingeR2 收手轨迹，混合中的左肩、肘、腕来自不同动作。循环权重还受脚步落地权重影响，低权重时会再次露出旧跑步姿势。

M4、AKM、QBZ191 使用同一冲刺组件，但没有后续普通走跑覆盖。其成熟流程让 `Apply` 统一拥有进入/返回轨道与循环：进入/退出均采样同一条 Enter；中途反向只改变进度；循环于进度 0.65–1 淡入。AKM 收手参考为 `Docs/Weapons/akm-sprint-left-wrist-relax-20260917.md`（V4）。

本轮还读取了 `GripLayerMode` 与 `WeaponGripProfileNode`：Super90 的稀疏握把差量按具体动画资产匹配，旧 PKM/201 IK 层不作用于此枪。上一轮实际保存的 NativeHingeR2 三段动画与四类握把冲刺条目继续使用，不再通过更改骨架或重新导入掩盖运行时轨道错误。

## 调整

- 冲刺组件已获得姿态且进度大于零时，Super90 禁止普通走跑分支覆盖。
- 冲刺组件最后统一写入所有相关通道，使用与 M4/AKM/QBZ191 相同的时间与权重。
- 保持直到退出进度归零；松开 Shift、ADS/射击要求退出以及中途反向不立即切回旧走跑姿态。
- 进度归零后才恢复原有普通移动；未配置战术动作时仍使用原先走跑路径。
- 无新 Tick、反射字段或网络状态；不改动画资产、弹药、换弹、材质、握把配置和上一轮散弹隐藏修复。

修改前源码见 `Before/FPSGAMECharacter.cpp`。本轮只需原生模块构建，不需资产导入。实际构建状态另见 `delivery.json`。按用户规则，不主动打开编辑器、游戏、渲染或测试；用户负责实机体验。

## 构建阻塞处理

首次 Editor 构建在 `Saved/BuildEditor/build-20261007-222650.log` 被新加入的 `MantisM27Monster.h` UHT 错误阻塞：RPC `MulticastMantisAccent` 的参数 `Role` 与 `AActor` 字段重名。仅把该 RPC 的声明、实现和函数内部引用改名为 `CueRole`，不改参数类型、顺序、网络标记或音效行为。涉及 `MantisM27Monster.h`、`MantisM27Audio.cpp`；两份修改前副本也保留在本目录 `Before/`。

下一次构建 `build-20261007-222816.log` 继续在同一音效文件发现 `PlayMantisVoice` 参数和扑击音效局部变量的 `Role` 重名（C4458），同样局部改为 `CueRole`，无行为改动。该轮 Super90 角色及冲刺模块编译完成，整轮因这两处错误未链接。

最终 `Saved/BuildEditor/build-20261007-223221.log` 返回 Succeeded、进程退出码 0，完成 `UnrealEditor-FPSGAME.dll` 与 `UnrealEditor-ColdSteelNet.dll` 链接及目标元数据保存。未打开编辑器或运行游戏测试。
