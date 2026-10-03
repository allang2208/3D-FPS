# 百目炉渣死亡下沉修复 V16

> 2026-10-02 更正：用户反馈 V16 后仍然下陷；实际顶层骨骼是 `RIG_HundredEyedSlag_V1`，不是本文假定的 `Armature`。V16 容器刚体绑定错误，而且关节限制没有同步保存用的 DefaultProfile。本文保留历史制作记录，当前修正见 [V17 排查与制作](hundred-eyed-slag-ragdoll-ground-v17-20261002.md)，不再将 V16 视为有效修复。

用户要求排查并修复死亡后陷入地底。仅处理物理根节点和死亡动画向布娃娃的交接；保留 V12 网格、蒙皮、材质、三档 LOD、横扫 V8、下劈 V9、三攻击组合及 V15 持续激光伤害。

## 原因与证据

`RagdollGroundV16/ragdoll_sources.json` 来自现有 UE 会话的只读资产读取。正式网格的顶层 `Armature` 和组件空间骨骼均保留 FBX 导入的 100 倍单位缩放；原 PA 只有 16 个解剖刚体，首个物理骨为 pelvis，Armature/root 均没有刚体。死亡动画 0.42 秒时顶层位移仍为零，骨盆高度约 50.94 cm，并非死亡动画将根骨移到地下。

UE 5.8 `PhysicsEngine/PhysAnim.cpp::PerformBlendPhysicsBones` 在非顶层物理骨使用 RootBoneScale 的倒数，同时通过 `UpdateWorldBoneTM` 取得无刚体父链的带缩放变换。此骨架缺少顶层刚体时，第一物理骨相对带 100 倍缩放父链计算位置后，又乘单位缩放倒数，导致显示位置被再次缩小。后续骨骼跟随下移，即使原刚体正确挡住地面，也会出现模型陷入地面的表现。

原 16 个刚体的 Ragdoll 配置、CCD 和地面阻挡已存在。它们约 0.1–1.06 的本地碰撞盒尺寸由引擎 InitBody/UpdateBodyScale 应用骨骼 100 倍缩放，不能直接把几何再放大 100 倍。没有调整网格、绑定或导入单位。

原死亡交接还没有立即刷新 kinematic target，且各部位以独立动画采样速度开始模拟。延迟姿势和相互不一致的速度会增加交接拉扯，因此一并修正。

本次读取时场景没有百目炉渣实例，未复现或宣称游戏内结果通过。

## 已制作和保存

- 独立保存 `/Game/Monsters/HundredEyedSlag/RagdollGroundV16/PA_HundredEyedSlag_Ground_V16`。复制原 PA 的 16 个解剖刚体和 15 条约束，追加 Armature 容器刚体和 pelvis–Armature 约束，总计 17 刚体、16 约束。旧 PA 和正式网格包均未覆盖。
- 容器球本地半径 0.02，应用骨骼缩放后为 2 cm，质量 2 kg；不参与地面碰撞。它仅保证顶层物理变换、骨盆和渲染骨架处于同一空间。
- `AlignVisual` 使用组件物理资产覆盖引用新 PA。正式网格及原动作引用保持原路径。
- `EnterCorpse` 在模拟前立即把采样姿势写入物理，禁止延迟；随后将动画骨骼更新设为 SkipAllBones，停止动画驱动物理关节。
- 容器约束在交接时使用实际刚体世界变换，去掉缩放后按厘米重新设置两个参考框架，并锁定线性和角度。不能直接将带单位缩放的参考骨架框架再次写入已初始化的 Chaos 约束。当前保存 PA 的容器参考框架由这段运行逻辑赋值，因此不要脱离角色交接逻辑评价其独立 PA 模拟。
- 明确恢复 QueryAndPhysics、WorldStatic/WorldDynamic 阻挡、重力及所有刚体 CCD。角色胶囊继续关闭，尸体网格保持当前世界变换后脱离胶囊。
- 基于骨盆传递一致的刚体线速度和角速度，在每个质心添加旋转速度项；避免独立四肢速度强行拉扯锁定关节。保留冲击方向和有限的下落速度。
- `BuildFittedPhysicsAsset` 同步补充容器刚体和约束，避免后续从源重新制作时遗漏。

资产实际保存记录：`SourceAssets/HundredEyedSlagMeshy20260930/RagdollGroundV16/physics_installation.json`。编辑器常规构建结果另记 `build_installation.json`；在该记录生成前，源码和资产完成不等于基础 DLL 已更新。

未主动运行 PIE、测试、截图或渲染；实际死亡表现交由用户测试。后台构建不主动打开或关闭 UE。
