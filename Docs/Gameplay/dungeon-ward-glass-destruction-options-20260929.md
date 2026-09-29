# 病区射击玻璃破碎：现状与可复用方案

日期：2026-09-29。用户要求查询现有资产是否可实现，并参考 GitHub 案例；随后指定 Niagara Destruction Driver 做源码复用评估。已下载固定提交的源码候选并阅读运行时实现；没有启用第三方插件或运行游戏、效果预览、兼容性测试。

本文保留 V3/V4 的前期调查记录。后续病区专用的玻璃破碎实现、碰撞切换和素材复用范围见 [V5 制作记录](dungeon-ward-breakable-glass-20260929.md)，实际接入状态以该批交付回执为准。原 NDD 插件仍未启用。

## Niagara Destruction Driver 源码复用结论

**可以复用碎片表现与离线数据制作，但活动玻璃门不能直接使用原插件。** 本轮完成源码候选保存和适配方案，尚未接入开枪打碎玻璃。

- 上游：[eanticev/niagara-destruction-driver](https://github.com/eanticev/niagara-destruction-driver)。固定提交 `881c350b0670a3a99dfe240ffdf284e1df6d9a86`，MIT 许可。完整许可证与源码保存在 `SourceAssets/NiagaraDestructionDriver20260929/Upstream/`，下载记录为同目录 `provenance.json`。未写入 `Plugins/`，未修改 `.uproject`。
- 可复用部分：作者阶段将 Geometry Collection 转成带碎片索引 UV 的网格及初始骨点纹理；运行时用 Niagara 模拟碎片，将位置和旋转写入两张 RGBA16f Render Target，材质通过 WPO 驱动碎片网格。预制破碎数据能避免运行时切割模型。
- 原 `InitiateDestructionForce` 隐藏完整模型，但其关闭完整模型碰撞的代码被注释。直接照搬会留下看不见的玻璃阻挡；病区必须由自己的玻璃组件同步撤销显示和碰撞，金属门框继续保留。
- `BeginPlay` 只设置一次 `ActorRotationQuat`、包围盒和模拟初始位置；作者也将移动支持列在路线图中。建议玻璃完整时跟随各自门扇，受击时取得门扇当时的世界变换，再创建固定世界坐标的碎片代理。碎片不继续跟随开关门旋转。
- Helper 的 `InitiateDestructionForce(..., Force)` 没有把 `Force` 传给 Actor；Actor 的第三个参数实际是持续时间。枪械适配必须明确区分受击方向、强度、半径和持续时间，不能把现有参数名当成已实现的力传递。
- Helper 只通过 `ECC_WorldDynamic` 重叠寻找该插件 Actor，并未接入本项目武器命中。病区应使用已有实际命中组件作为入口，不让打中把手或金属框触发玻璃消失。
- 原 Actor 为每个实例在 BeginPlay 分配两张 RT、动态材质并同步加载 Niagara。病区接入应推迟到命中时创建短寿命表现代理，并限制同时活跃的碎片组；不能把整间所有完整玻璃变成常驻模拟。
- 数据资产缺失时原代码的 `ensure` 后仍有解引用；正式接入需要完成资源装配和相应失败退出。材质需适配项目现有 Substrate 玻璃链路。上游记录的测试版本为 UE 5.5.4，本地 5.8.2 的编译与显示兼容性尚未执行。

下一阶段实际接入顺序：先分离门叶玻璃/金属和各观察窗，独立配置可关闭的玻璃碰撞；再添加受击状态切换、命中时变换快照和有界碎片代理；最后制作对应玻璃的破碎数据、适配材质并保存关卡。十二扇门继续各自交互。GPU 碎片只承担视觉，不能让它们承担人物阻挡、子弹命中或拾取查询。

源码依据：[Actor 实现](https://github.com/eanticev/niagara-destruction-driver/blob/881c350b0670a3a99dfe240ffdf284e1df6d9a86/Source/NiagaraDestructionDriver/Private/NiagaraDestructionDriverActor.cpp)、[Helper 实现](https://github.com/eanticev/niagara-destruction-driver/blob/881c350b0670a3a99dfe240ffdf284e1df6d9a86/Source/NiagaraDestructionDriver/Private/NiagaraDestructionDriverHelper.cpp)。以上结论来自源码阅读，不是运行验收结论。

## 当前项目

病区目前没有“整块玻璃被射击打碎”的接入。门是带碰撞的静态玻璃/金属组合网格；观察窗也是静态网格，没有破碎状态逻辑。

可复用的本地资源已经存在：

| 用途 | 本地资源/代码 |
| --- | --- |
| 玻璃命中粒子 | `/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass` |
| 三种玻璃碎片网格 | `/Game/NiagaraExamples/StaticMesh/SM_GlassShard_01`、`02`、`03` |
| 碎片材质 | `/Game/NiagaraExamples/Materials/MI_GlassShard`、`MI_SimpleGlassShards` |
| 玻璃弹孔 | `/Game/NiagaraExamples/Materials/MI_BulletHole_Glass`、`/Game/Weapons/GunplayFX/Impacts/MI_ImpactMark_Glass` |
| 三个玻璃命中声音 | `/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0`、`1`、`2` |
| 现有命中分流 | `Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp` 的 `OnImpact` 调用 `FPSImpactFXSubsystem::SpawnImpact`；子系统已有 `Glass` 表面分支与有界碎屑池 |

这些资源能支撑实现，不需要先购买新的素材。但“有粒子”和“玻璃障碍真的破坏”是不同阶段：仍需按受击部位触发破裂，保留金属框，移除破损玻璃的碰撞，并使后续射线穿过空洞。现有玻璃声音属于命中库，整窗碎落声的适用性尚未试听。

## 推荐的病区接入方式

1. 将五处观察窗拆为单窗组件，将十二扇门叶的玻璃与金属框分离；原模型/尺寸、门的独立开关行为保持。
2. 每片玻璃具有完整、裂纹、破碎状态。金属框命中走金属反馈；玻璃命中由玻璃组件响应，避免打中把手也把整门删除。
3. 作者阶段制作有限数量的放射裂纹与残留边片。破碎瞬间替换玻璃显示及碰撞，复用现有碎片/声音/弹孔；较细碎片只作短时视觉表现，使用有限并发和寿命。
4. 门移动时玻璃与裂纹跟随对应门叶；玻璃破后门框仍可独立推开。局部裂口需要匹配裂口的碰撞；整片破碎则撤掉对应玻璃碰撞，不能仅隐藏透明材质。

本条为待开发方案，本次血迹/门交互调整没有接入射击破坏。

## GitHub 参考

- [Niagara Destruction Driver](https://github.com/eanticev/niagara-destruction-driver)：UE 项目，MIT 许可。将预制 Chaos Geometry Collection 转成 Niagara 驱动的 GPU 碎片；README 记录测试版本为 UE 5.5.4。其碎片属于装饰表现，不能对碎片做碰撞射线查询，移动支持仍列在路线图中。因此适合借鉴碎片渲染和触发方式，不能直接代替门窗碰撞/活动门破坏系统，也未证明与本工程 UE 5.8.2 兼容。
- [WindowFracture](https://github.com/florian-noirbent/WindowFracture)：Unity 实现，附演示场景，使用二维裂纹图案投影裁切、生成碎片多边形，并按与边框的连接关系保留边片或掉落。适合借鉴平面玻璃算法；不是 UE 插件，未下载、移植或复制其代码。

Niagara Destruction Driver 已进一步完成上方的源码阅读，WindowFracture 仍仅作公开方案参考。不把作者演示称为本工程已验证成功；本地已有的玻璃命中声、粒子和碎片仍可复用。
