# 大旋风动画错位排查（2026-09-20）

本轮用户要求排查“手和武器是否有两套动画错位播放”。仅读取代码、现有资产作者源和当前 PIE 的组件状态；未修改运行代码、材质或动画，未改变玩家装备、触发技能、启动/停止 PIE。

后续用户已明确要求修复；上面的只读范围指排查阶段。修复记录见文末。

## 结论与证据

当前实现没有为手臂和剑身各启动一套独立动画时钟。发现更明确的相机时序问题：大旋风在本帧 PlayerCameraManager 已缓存 POV 后才旋转相机和附属前景网格，渲染仍取缓存 POV。由此产生相机组件/手臂/武器与渲染视角之间的一帧相位差。代码路径可确认，尚未在真实大旋风施放帧采集 POV 差值或截图，不能据此断言所有重影均由这一处导致。

### 一条动画、一个握持骨架

- `Source/FPSGAME/Weapons/RuneSwordComponent.cpp:78`：RuneSwordViewmodel 禁止自动 Tick。
- `:176`：SetClip 只设置一个 CurrentAnimation，播放速率设为0；`:184` 的 SamplePose 以显式时间执行 SetPosition、TickAnimation(0)、RefreshBoneTransforms。
- `:154`：模块化剑刃为 StaticMeshComponent，挂到同一手臂骨架的 WPN_root，没有自己的动画播放器。
- `:840`：大旋风 Tick 后立即 return，不再走后面的格挡、普通攻击、待机或走路分支。
- `:506`：大旋风期间普通近战 GetCameraMotion 直接返回零，未叠加另一套剑技镜头曲线。
- `WindupV3/author_whirlwind.py`：手部抓握矩阵与 WPN_root 矩阵在同一帧循环内烘焙到同一个 action。`whirlwind_motion.py` 的 grip/blade 通道共用时间，只分离握柄与刃面朝向；720度转身由运行时单独控制。
- `Source/FPSGAME/Skills/FPSCastingMeshComponent.cpp:36` 确有施法左臂覆盖层，但大旋风入口拒绝左手施法占用，施法入口也通过 IsLeftHandBusyForCast 拒绝正在大旋风的近战 IsBusy。源码未发现允许这两个动作并行覆盖的入口。

### 首个明确的时序分歧

本机 UE5.8 源码 `Engine/Source/Runtime/Engine/Private/LevelTick.cpp`：

1. 第1778行：执行 TG_PostPhysics。
2. 第1847行：UpdateCameraManager，缓存本帧 POV 与后处理设置。
3. 第1877行：执行 TG_PostUpdateWork。
4. 随后 LocalPlayer 使用 PlayerCameraManager 的缓存视角构造渲染视图（LocalPlayer.cpp:714、PlayerController.cpp:1007）。

但 `RuneSwordComponent.cpp:37` 将整个近战组件放在 TG_PostUpdateWork。`RuneSwordWhirlwind.cpp` 在此阶段写 SetControlRotation、调用 RefreshQuickCombatCamera，再提交手臂姿态。`FPSGAMECharacter.cpp:1338` 的 RefreshQuickCombatCamera 仅调用 UpdateCamera(0)，后者更新 CameraComponent 的位置/旋转，没有刷新 PlayerCameraManager 缓存。项目源码未发现大旋风之后的 FillCameraCache 或 UpdateCameraManager 补偿调用。

因此旋转帧的实际顺序是：缓存旧视角 → 转动相机组件及手臂/剑身 → 用旧缓存视角绘制已经转过的前景。手和武器自身仍在同一动作帧，但会一起相对屏幕错位；这种运动也会增加时域历史重投影的困难。技能后处理参数同样在相机缓存之后改变，存在一帧生效延迟。

按720度/0.8秒与当前 smoothstep 推算，峰值角速度为1350度/秒，60 FPS 时一帧相位差可接近22.5度，120 FPS 时约11.25度。这是公式估算，不是实测帧率或捕获结果。

骨骼刷新本身会通过 UE `FinalizeAnimationUpdate()` 同步更新挂点子组件（PhysAnim.cpp:473–483），源码不支持“骨架刷新后忘记更新剑身挂点”这一猜测。

## 运行读取的范围

`runtime_snapshot.json` 来自当前 `/Game/GameMaps/UEDPIE_0_L_TemperateHills_Initial`。当时玩家持 M16：只有 AKMViewmodel 的 M16手臂可见；RuneSwordViewmodel、生产工具、攀爬手臂、备用施法手均未显示，施法左手占用为false。该快照证明了读取到的真实上下文，不能当作大旋风中的重复模型排除证据。

本轮尝试读取普通柄/加长柄 V3 的源姿态与压缩姿态差异，连接未发现可用编辑器节点，脚本没有执行，未生成 `asset_pose_snapshot.json`。因此不报告压缩误差数值，不宣称完成动作帧或视觉验收。

最近可读的完整构建日志 `Saved/BuildEditor/build-20260920-134446.log` 为 Succeeded，基础 DLL 时间13:44:57；编辑器也已重开。此前13:16的编译阻塞属于旧状态，本次诊断未重编译。

## 假设排序与下一步

1. **镜头缓存与前景更新错一帧：代码证据明确，优先处理。** 将大旋风的转向、动作和技能后处理更新提前到角色更新之后、PlayerCameraManager 缓存之前，保留同一时钟及一次最终姿态提交；可使用 TG_PostPhysics 阶段或角色相机更新前的专用技能推进入口。避免再次更新整套 CameraManager 导致镜头混合/震动重复计时。
2. **时域重投影/运动矢量残影：仍可能同时存在。** 先消除上面的屏幕相位差，再在同一场景对比前景残影。
3. **两套动画或两套模型同时显示：源码没有对应路径，旋转中的运行快照尚缺。** 后续直接采集实际技能帧的可见网格、动画资源名、组件相机角度与缓存POV角度即可区分，无需更换贴图或重做握持。

针对修复的最小复现范围：一把普通柄剑原地施放一次、一次确认命中的停帧、一次按 ALT 展示鼠标；记录同帧相机组件/缓存POV、WPN_root/剑身与双手位置。加长柄仅需确认同一更新顺序及握点。以上为后续建议，本轮没有执行。

## 经用户授权的修复

`RuneSwordWhirlwind.cpp` 在 BeginWhirlwind 成功提交技能后，将现有近战组件切到 `TG_PostPhysics`；FinishWhirlwind（正常结束及取消的共用出口）恢复 `TG_PostUpdateWork`。已有的角色 Tick 前置依赖保留，因此技能更新在角色之后、PlayerCameraManager 的本帧缓存之前完成。

只改变大旋风持续期间的调度阶段，不额外调用 CameraManager，不增加第二条动画时钟。现有120Hz命中子步、每帧一次最终骨骼提交、0.5秒蓄势、反向720度、停帧、背景模糊和 ALT 逻辑均沿用。

UE 的 SetTickGroup 更新下一次调度所用阶段；若技能输入发生时本帧 Tick 已排队，起始帧仍可能在旧阶段完成第一小段蓄势。镜头旋转在0.5秒蓄势后才开始，届时已进入镜头缓存前的阶段，不保留旋转期间的一帧视角差。

执行必要的完整 Editor 构建。没有启动应用、运行游戏、截图或追加回归测试；视觉效果由用户测试。构建结果记录在主迁移文档及 `camera-order-build-output.txt`。

构建结果：Succeeded，`Saved/BuildEditor/build-20260920-140939.log`，基础 Editor DLL 已更新。
