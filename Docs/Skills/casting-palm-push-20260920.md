# 共用左手施法：向外推掌与停顿（2026-09-20）

**2026-09-21 当前 V9：总长 1 秒，增强回震。** 用户要求缩短总长并反馈未见回震；V9 保留 V8 的快速切换/推出与 V6 的 recover，将终点停留缩至约 0.227 秒，独立发射为 0.16 + 0.113333 + 0.226667 + 0.50 = 1.00 秒。回震位移系数约放大 2.5 倍，12 Hz、0.18 秒衰减。当前源及构建结果见 [ImpactV9](../../SourceAssets/CastingPalmPush20260921/ImpactV9/README.md)。本轮未运行游戏测试或渲染。下述 V8 编译受阻是历史记录，不代表 V9 状态。

**2026-09-21：V8 已完成代码与源动画制作，编译接入受阻。** 用户要求再加快从持握到推掌并增加冲击抖动；当前源为预备 0.16 秒、推掌约 0.113 秒、到位停留约 0.627 秒、recover 0.50 秒，总长仍为 1.40 秒，接触后叠加 0.16 秒衰减整臂回震。制作及编译阻塞见 [ImpactV8](../../SourceAssets/CastingPalmPush20260921/ImpactV8/README.md)。未测试；下述 V7 是上一轮已完成构建的版本，V8 尚未在游戏中生效。

**V7 推掌重定时（已构建，待用户实机确认）。** 保留 V6 小臂与收手修订，按用户要求将推出速度加倍：默认预备 0.26 秒、推掌 0.17 秒、停顿 0.47 秒、recover 0.50 秒，总长仍为 1.40 秒。施法加速时也保留原总时长，发射接触同步提前。历史源文件及时钟见 [PushTimingV7](../../SourceAssets/CastingPalmPush20260920/PushTimingV7/README.md)；此前源模型检查见 [RecoveryV6](../../SourceAssets/CastingPalmPush20260920/RecoveryV6/README.md)。该轮未追加测试或渲染。下文 V4 制作记录按历史保留；不得作为当前已认可基线。

用户以左手照片指定“向外推掌，停顿 0.3 秒再 recover”。本轮适用于共用释放手势的火球、冰锥、闪电和圣光。照片定义终点手型；起手到推掌的运动路径属于基于原动作的三维适配。未进行游戏测试、截图或渲染，待用户确认。

## 参考与动作

- 已读取原 `FireballCast20260914/reference-release.jpg`、当前运行姿态参数和阶段时钟。原释放为手掌向下、四指朝前；当前照片要求手背朝向玩家、掌心向外、四指向上、拇指自然张开。
- 继续使用 Manny 手模与 `FPSCastingMeshComponent` 的完整肩／上臂／前臂／辅助骨求解。目标掌向采用相机空间语义，不改骨长、缩放或右手武器动作。
- `fireball_hand_pose.json` 升为 V4：掌心法向约 +X，手指方向约 +Z；腕部终点 `(50,-22,-18)` cm，保留肩与肘协同支撑。四指保持轻微且不相同的弯曲，拇指放松外展。

## 时序与接触

默认独立释放：预备 0.26 秒 → 推掌 0.34 秒 → 定姿 0.30 秒 → recover 0.44 秒，总长 1.34 秒。法术接触仍在推掌开始后 0.20 秒，即整段的 0.46 秒，停顿期间不重复释放。

推掌曲线在完整前伸的末端归零速度；保持阶段固定采样终点。复用 `Releasing` 阶段，结束阈值加入 `ReleaseHoldSeconds * GestureSpeed`；由于阶段时钟也乘施法速度，实际停顿保持 0.30 秒。其余阶段继续使用已有施法加速，收手由真实退出姿态衔接。凝聚、脱手悬浮与资源／冷却规则沿用原实现。

## 可编辑源

- 作者入口：`SourceAssets/FireballCast20260914/author_cast.py`，读取运行 JSON、C++ 时长和曲线。
- 当前输出：`SourceAssets/CastingPalmPush20260920/Casting_PalmPush_Editable.blend` 与 `Export/`。保留原 V3 Blend／FBX；当前照片仅作本机私人作者参考。
- 除原分段动作外，增加 `A_Fireball_PushHold`（0.30 秒）与 `A_Fireball_CastDetached`（1.34 秒连续完整动作），300 Hz 烘焙，后者包含预备、推掌、停顿和 recover。`A_Fireball_Hold` 仍仅为旧凝聚终点参考，不能当作新推掌停顿。
- 游戏继续使用共用程序化施法层；FBX 是可编辑交付，不替换现用武器动画引用。

## 制作与构建记录

- `author.log` 记录 Blend 保存和九段 FBX 导出完成；`authoring.json` 为作者输出清单。
- `live-coding-result.txt` 记录当前编辑器补丁编译成功。随后编辑器返回无未保存包、无运行游戏，正常退出以完成常规构建；未强制结束进程。
- `FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 常规构建均已完成，记录为作者输出目录下的 `build-editor.log` 和 `build-game.log`；本次实现已写入基础 DLL／游戏程序。
- 本轮未运行 PIE、测试、截图或验收渲染。
