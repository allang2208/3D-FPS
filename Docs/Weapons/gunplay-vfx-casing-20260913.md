# Gunplay 特效升级建议与步枪抛壳修改

> 后续用户已确认一起接入曳光与烟雾，当前实现和构建状态见 [Gunplay V6 交付记录](gunplay-vfx-v6-20260913.md)。下文保留初始盘点、建议和首轮构建中断记录。

日期：2026-09-13。第 1 项交付资源盘点和升级建议；第 2 项修改运行源码。没有启动游戏、截图、渲染或运行测试，效果由用户自行测试。

## 当前资源和实现

以下来自本机 `Content`、当前源码与资产生成脚本的读取，未打开特效编辑器判断实际画面。

| 用途 | 已在库里的资源 | 当前接入情况 |
| --- | --- | --- |
| 曳光 | `NiagaraExamples/FX_Weapons/Trails/NS_BulletTracer`；`Materials/MI_Tracer`、`MI_TracerRibbon` 及对应主材质 | 当前仍使用引擎 Cylinder 和 `Weapons/GunplayFX/M_BallisticTracer`。每帧只画真实扫掠段末端，最长 45 cm、宽 0.35 cm；没有柔边与沿长度的明暗渐变。 |
| 枪口烟火 | `Weapons/GunplayFX/NS_FPS_MuzzleEpicV5`、`NS_FPS_BarrelSmokeEpicV5`；原包 `NS_MuzzleFlash` 和 `MI_Flipbook_Smoke_Muzzle` | 已正式引用 V5；烟色绑定、世界空间、停火热烟和火光 alpha 淡出已有实现。 |
| 细烟和烟团 | Epic `T_Smoke_Wispy`、`MI_SmokeWispy_8x8_Emissive`、`MI_SmokePuffLight_8x8`；Realistic Starter VFX Vol2 的 `T_Smoke_Wisp`、`M_Smoke_Wisp` | 可作为候选贴图/材质来源；尚未作为本轮升级资产接入。场景烟柱、地面烟和爆炸烟不直接套给步枪。 |
| 弹壳 | `NiagaraExamples/FX_Weapons/MuzzleFlashes/Meshes/SM_BulletShell`、`MI_BulletShell_FX`、颜色和法线贴图 | 本轮将已有模型/材质接入步枪抛壳。原先是尺寸 0.8 × 0.8 × 2.6 cm 的基础圆柱。 |

Epic 原包沿用项目 `Docs/AssetSetup.md` 已记录的授权与本机恢复规则。本轮不下载、复制 GitHub 代码或公开发布第三方二进制资源。

## 建议：先改善画面，再考虑批量渲染

### 曳光：真实弹道驱动的短亮芯与柔边尾迹

保留 `FPSBallisticsComponent` 的飞行位置、扫掠碰撞、命中截断与伤害结算。它负责告诉视觉层本发子弹从哪里飞到哪里，视觉层不重新模拟第二条弹道。

优先复制本机 `NS_BulletTracer` 为独立项目候选，复用 `MI_Tracer` / `MI_TracerRibbon` 的表达方式。实现时需读取原发射器的参数绑定和空间设置，不能仅根据资源名称假定其可直接接收当前弹道数据。

建议调校起点：暖白亮芯、较弱的暖黄外缘，头部紧凑，尾部透明渐隐；视觉段长从 45–100 cm、宽度 0.15–0.30 cm 起调，长度与实际移动距离、速度关联，并截在实际命中点以内。每发沿用同一弹道身份，只展示当前位置附近的短段，避免把历史位置积成连续光管。保持深度遮挡，不为增强可见性穿墙显示。以上是美术候选参数，尚无本轮运行效果结论。

第一阶段继续用现有数量受限的池即可；大量角色同时射击时，再把上一帧/当前帧端点按视觉类型批量送入少量 Niagara 系统。单玩家的小规模特效不必先引入 ECS、GAS 或新的网络弹道框架。

### 枪口烟雾：保留 V5 烟量，分离每发喷烟与热烟

现有 V5 已有两种触发：每发烟为 0.50–0.80 秒，ADS alpha 0.40、腰射 0.55；最后一发超过 0.14 秒且热量超过 0.35 才补热烟，后者寿命 0.60–0.90 秒。当前 Niagara 池上限 24，热烟调度周期 0.11 秒。升级应从这些现有值出发。

建议每发烟继续使用枪口 flipbook，呈现短促、沿枪管喷出再展开的烟；停火后换用 wispy 细烟，随热量渐弱、上浮并带轻微扰动。不要把每发烟和热烟都做成相同的大烟团。烟出生后保持世界空间，火光继续跟随当前枪口出口。

保持现有 `User.Smoke Color` 绑定以及 V5 用户已经要求提高的烟量。优先调整形态和展开方式，不同时压低透明度、尺寸与寿命。普通枪口、消音器、腰射、普通 ADS、LPVO 各自配置可读性：LPVO 保留火光与烟，必要时只对靠近视点的烟做柔和淡出。消音器的闪光与烟量应有独立参数，避免一个全局缩放同时把两者缩没。

每发喷烟可继续池化。若停火余烟实例重叠明显，可改成每把枪一个可复用热烟组件，由热量控制发射率，并让已出生粒子自然消散。原始包保留，候选分别命名后再接入。

## GitHub 与官方参考

- [EmpiresCommunity/ECSProjectiles](https://github.com/EmpiresCommunity/ECSProjectiles#ecsprojectilemodule_niagara)：作者用前后两帧位置数组把同类子弹交给少量 Niagara 系统渲染。可借鉴视觉数据批处理和弹道/渲染分工；仓库是实验性 UE4 插件，README 明确网络部分未完成，不作为 UE 5.8 即插即用依赖。
- [Voidware-Prohibited/Ricochet](https://github.com/Voidware-Prohibited/Ricochet)：GAS 弹道框架涉及物理材质、穿透/跳弹、Niagara、Metasound 等。可作为以后扩大弹道功能时的结构参考；作者仍标注开发中，其依赖与改造范围超过本次视觉升级需要。
- [Epic：Niagara 扩展性与最佳实践](https://dev.epicgames.com/documentation/unreal-engine/scalability-and-best-practices-for-niagara)：池化减少组件分配，但多系统实例仍有成本；向已有系统追加粒子是进一步减少实例数的方向。这支持“先复用本库资源和池，必要时再批处理”的升级顺序，不构成本工程帧率提升的测量结果。

## 已修改：步枪抛壳和 LPVO

修改文件：`Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`。

- 步枪复用 Epic 弹壳模型与表面材质，根据模型实际包围盒等比缩放并补偿模型枢轴，避免套用引擎 100 cm 圆柱的尺度。M4、AKM、QBZ191 的表现长度起点分别为 4.5、3.9、4.2 cm；这是共享特效网格的尺寸适配，不宣称三种口径已各自制作独立精确弹壳模型。
- 出生位置读取当前枪身 `WPN_SOCKET_Eject` 的世界位置。朝向在初始化时从枪械参考骨架的前后瞄点、枪身上方向解算，再转换到 `WPN_root` 局部坐标；开火时随当前枪身姿态旋转。方向不再跟随摄像机的右/上向量，也不受运行时折叠瞄具影响。
- 抛出速度为枪身局部向右 185–260 cm/s、向上 70–125 cm/s、向后 35–70 cm/s，并一次性继承角色移动速度。加入随机翻滚，使用世界重力；脱离枪体后沿世界轨迹飞行。继续沿用现有有限粒子池、扫掠碰撞、碰撞反弹和回收流程。
- 装备 `lpvo_1_6x` 并进入瞄准时停止生成弹壳，瞄准中把之前腰射产生的在飞弹壳回收；退出镜内画面的渐隐阶段仍保持隐藏，随后新开火恢复抛壳。这个规则涵盖 LPVO 的 1x 到 6x，不能写成单纯“倍率大于 1”。只装备镜子但腰射时仍有抛壳；普通机瞄/红点照常。
- LPVO 分支只处理弹壳，保留现有枪口火光、烟雾、曳光和命中反馈。手枪继续原有抛壳表现。

## 交付状态

曳光/烟雾部分为升级建议，未更换其运行资产。抛壳部分已修改源码并引用本机已有资源。没有执行运行检查、视觉预览或测试；本轮外观、抛壳贴合与镜内表现由用户测试。

本机 FPSGAME 编辑器当前打开，普通 Editor 构建入口要求先保存并关闭。没有关闭用户进程或用带后缀的热重载 DLL 替代正常 Editor 构建。

本轮尝试了独立 Game 目标的必要构建，记录为 `Saved/Logs/GunplayCasing-GameBuild-20260913.log`。构建遇到本次未修改文件的错误，包括 `ColdSteelInventoryTheme.cpp` 的 `UColdSteelSkillPage` 未定义类型、`ColdSteelSkillPage.cpp` 的声明不匹配，以及生产/地形相关头文件和字段错误；发现这些跨模块阻塞后停止本轮构建，退出码为 1。没有改动这些其他源码，也未完成链接，不能宣称枪械代码已编译通过。

当前正在运行的编辑器仍使用旧模块。完整工程编译问题处理后，先保存并关闭编辑器，再执行 `Tools/Build/Build-Editor.ps1`，重新打开工程使用新模块；不自动启动测试。
