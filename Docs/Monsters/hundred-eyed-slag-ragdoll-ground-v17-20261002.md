# 百目死亡下陷修正 V17 与 GitHub 布娃娃方案

2026-10-02。用户反馈 V16 后百目死亡仍陷入地下，本次排查静态骨架、已保存 PA 和死亡交接源码；默认不运行游戏、PIE、截图、渲染或物理测试。

## 实际错误

后台只读数据见 `SourceAssets/HundredEyedSlagMeshy20260930/RagdollGroundV17/death_physics_inputs.json`。

1. 当前 V12 网格的顶层骨骼为 `RIG_HundredEyedSlag_V1`，本地缩放为 100；下游还有 `root`、`death_pivot`、`pelvis`。V16 新增的刚体和骨盆约束却使用不存在的 `Armature`，交接代码也按这个错误名称寻找刚体。它没有修正真实顶层骨骼的物理混合。V16 文档和技能中的顶层名称来自假设，需要更正。
2. 重新加载的 V16 PA 所有 16 个关节的角度模式均为 `Free`，包括拟锁定的容器关节。原作者修改 `DefaultInstance` 后未同步 `UPhysicsConstraintTemplate::DefaultProfile`；UE 5.8 `PhysicsConstraintTemplate.cpp::Serialize` 保存时用默认配置替换实例配置，因此预期的活动范围没有持久化。仅调用 `PhysicsAssetToolset.SetConstraintLimits` 也没有同步这个默认配置。

死亡动画采样为本轮读取资产输入的一部分，并没有运行死亡或复现接地。以上是实际资产/源码错误，不将它们表述为游戏内完整根因已验证。

## 制作与接入

- 新 PA 路径为 `/Game/Monsters/HundredEyedSlag/RagdollGroundV17/PA_HundredEyedSlag_Ground_V17`，从 V16 复制，保留 16 个贴合解剖的碰撞体、质量与自碰撞禁用表。源网格、蒙皮、材质及全部动作包不修改。
- `RepairCorpsePhysicsAsset` 在制作阶段读取网格实际根骨，修正容器刚体及 pelvis–容器约束；容器仍为 2 cm 无碰撞辅助球，随身体参与物理混合。
- 躯干限制 18/18/12 度，肢体近端段 65/50/35 度，中段 55/18/15 度，掌部 30/25/20 度，恢复原作者设定。线性全部锁定，容器角度锁定，并通过 `SetDefaultProfile` 实际持久化。
- `BuildFittedPhysicsAsset` 同步补上默认配置保存，避免以后重新制作再次丢失限制。
- `AlignVisual` 引用 V17；死亡交接从网格参考骨架读取根骨名称，在当前死亡姿态建立容器关节，不再硬编码 `Armature`。保留立即同步姿态、脱离胶囊、地面阻挡、CCD、重力与一致的速度交接。

实际资产保存以 `physics_installation.json` 为准，必要构建以该目录构建回执/日志为准；仅存在制作脚本不代表资产已保存。未进行运行验收，由用户测试。

本次落盘：后台保存日志明确记录 `root=RIG_HundredEyedSlag_V1 bodies=17 joints=16` 及 V17 包保存完成。复用当前共享工作树中已完成的常规 Editor 构建：百目角色对象文件 12:19:59、物理作者对象文件 12:20:03，基础 `UnrealEditor-FPSGAME.dll` 12:25:09 落盘；新的原生资产作者方法随后在保存 commandlet 中实际执行。不是隔离本次源码的独立构建。另排的重复构建到达时编辑器已再次运行，触发占用保护、没有执行；本次未启动该交互编辑器，没有重启或关闭其他进程。复用产物与保存状态分别写入 `build_installation.json`、`physics_installation.json`。

## GitHub 方案评估

本轮搜索并读取项目自己的 README、许可证信息与相关源码。以下属于结合 FPSGAME 的适配判断。

| 项目 | 当前公开信息 | 对本工程的判断 |
| --- | --- | --- |
| [Sixze/ALS-Refactored](https://github.com/Sixze/ALS-Refactored) | MIT；公开兼容表最新版 4.17 对应 UE 5.7。重写的 C++ ALS 系统，支持网络/Iris。 | 最适合借鉴死亡交接、起始速度限制、骨盆刚体数据和网络同步方法。它是完整人形移动系统，不能直接套在百目四肢专用骨架上；本机 UE 5.8.2 适配没有本轮编译证据。 |
| [tigershan1130/UE5-active-ragdoll-with-floating-capsule](https://github.com/tigershan1130/UE5-active-ragdoll-with-floating-capsule) | 作者明确称为 Active Ragdoll 与浮动胶囊的概念验证；GitHub API 最后推送 2023-03-24，许可证字段为空。 | 适合研究受击后主动平衡与物理跟随，当前死亡尸体问题不需要替换整个角色控制器。没有明确再使用许可，不复制其代码进正式工程。 |
| [PanicPetal/ALS-Community](https://github.com/PanicPetal/ALS-Community) | README 标为 UE 5.4；MIT 源码；作者说明后续仅做引擎兼容修复，布娃娃复制仍属实验阶段。 | 可作旧实现参照，优先级低于 ALS-Refactored，不作为 UE 5.8 新死亡系统的首选。 |

ALS 的布娃娃实现可直接查 [AlsCharacter_Actions.cpp](https://github.com/Sixze/ALS-Refactored/blob/main/Source/ALS/Private/AlsCharacter_Actions.cpp)。它在进入物理时脱离网格、禁用胶囊并限制初始速度；运行时读取刚体骨盆而非依赖动画插槽位置，再同步角色位置和处理接地。其接地射线主要服务角色胶囊/相机，不能当成已经修复尸体网格穿地的依据。

建议后续保留 Chaos 与每类怪物专属 PA，提炼一个共用死亡交接组件：真实根骨和骨盆配置、动画姿态与速度交接、有限初始速度、关节阻尼、接地后休眠/预算及网络权威同步。本轮只修百目并给出方案评估，没有安装第三方插件、替换全体怪物或声称通用系统升级完成。
