# 村防热油锅

## 动作

满锅先在胸腹前持稳。左掌托住靠低侧的木柄，右手提起对侧锅柄，双肘先收、再送。锅绕前方与侧方两个轴转动，油沿左前锅唇流出。油尽后先回正再收低。第一人称使用 V7 手型，第三人称按同一双柄接触点适配角色手掌。持锅时低头看墙下沿用端锅姿态，锅内液面按装量和倾角偏向低侧。

## 锅内油面

油体使用深琥珀色、非金属的受光表面，由光源和反射形成高光。热区缓慢移动，每次随机选取泡核位置、起泡间隔、簇大小、尺寸和寿命。泡帽长大、破裂时，在同一 UV 位置触发向外传播的涟漪。复用烹饪蒸气的稀疏发射方式。热区会更频繁地产生 2 至 5 个泡帽的小簇，间有单泡；每口锅最多使用 28 个气泡实例，保存最近四次破泡的波纹；离开观察范围停止更新装饰。

## 流到地面

油束从当前锅唇伸向第一处有效落点，接触地面后才开始计油区寿命。先在落点生成小片湿面，再分批采样附近高度、法线和相邻地面之间的连通性。以入射方向、坡度和局部阻力计算油到达每一处的时间。完整障碍阻断流动，短障碍允许绕行。接近墙脚或平台边界时细分网格到实际接触边缘。

表现层按一小锅约 2.3 升的油量分配膜厚，在邻接地块之间进行四次守恒转移。高处留下薄膜，低处积油更深。材质使用到达时间、流向、厚度和距边缘的距离表现湿润前缘、细流与反光。地表纹理透过薄膜可见，主体沿地形铺设，飞溅只在落点短暂出现。

落地飞溅使用 16 颗油滴。地火复用青铜火把的主辅火焰与颜色曲线，每片油运行一个 Niagara 系统。主层沿连通油面从上游向下游点燃，薄油处先退。厚油洼里的辅层更窄更高，先于最后一批低火退去。近景火片依据观测距离和视场收窄，间隙露出深琥珀色油面。

## 玩法与复查

投掷距离 3 米；初始蔓延半径削弱为 **2.75 米**，落地后基础持续 **10 秒**，每连续接触 0.25 秒造成 **10 点** 基础魔法伤害并施加 **1 层** 持续 5 秒的灼烧。解锁机械工坊后可通过「城防热油锅」升级卡分别强化：热油伤害（15 级，10 → 25）、蔓延范围（15 级，2.75 米 → 5 米）、持续时间（3 级，10 → 16 秒，`M_OilFilm` 由 CustomPrimitiveData 1 动态控制火光与油膜淡出）及灼烧堆叠层数（3 级，每次接触 1 → 4 层）。服务器确定地表三角形、岸线高度和到达时间，客机从已复制的湿区快照生成油面与动态范围/时长参数。晚加入和重新进入相关范围时使用最新快照。取锅时检查双手和输入是否可用。持锅阶段按当前装备栏、两只手的实际物品和已执行的手部动作判断中断。短暂锁定视角、菜单光标、相同装备的显示刷新及未执行动作的按键均可保留手锅。友军和自身可受伤，城防设施免伤。

[火把发射器与油区接入](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_torch_field.py) · [地面火根与可见距离](../Publication/VillageDefense20261126/Implementation/Source/FPSGAME/WorldGeneration/VillageOilFireFront.cpp) · [材质制作源](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_materials.py) · [地表扩散算法](../Publication/VillageDefense20261126/Implementation/Source/FPSGAME/WorldGeneration/VillageOilSpread.cpp) · [双手动作](../Publication/VillageDefense20261126/Implementation/Source/FPSGAME/WorldGeneration/VillageOilCarry.cpp) · [UE 复查记录](F:/FPSGAMEData/ArtReviews/HighVillageDefense/HotOilFlow-20261125/results.json)

## 坡面、支撑物与联机同步

2026-11-26。每个服务器世界共用一个轮询地形队列，每帧最多 384 次地形射线查询，每轮每片油最多领取 32 次。列采样、跨格连通和岸线二分都占用此预算。单位脚下的实时支撑复核单独进行。独立游戏沿用相同的分帧调度。

中心向外的每个采样带完成后才用于伤害。伤害粗筛沿实际湿面三角形的三维包围盒扩展 17 厘米，脚下仍按所在三角形和连续暴露时长判定。支撑构件或实例被移除、移动、替换或关闭查询碰撞后，受影响的湿区和跨格通道由服务器撤销，仍有支撑且已经流到的区域继续燃烧。

每片油复制可独立解码的最新快照，包含湿格高度、法线、连通位、到达时间、油膜厚度和岸线截点。快照按采样提交或支撑变化更新，稳定期不重发地形。粒子由各客户端按照已有视距档位和共享发射预算生成。收锅与手部动作使用原有复制状态，角色取得本地控制权时可以直接从世界锅补建第一人称锅。

[服务端调度](../Publication/VillageDefense20261126/Implementation/Source/FPSGAME/WorldGeneration/VillageOilSurveySubsystem.cpp) · [湿区同步](../Publication/VillageDefense20261126/Implementation/Source/FPSGAME/WorldGeneration/VillageOilSurfacePacket.cpp)

## 连片地火 R2

制作日期为 2026-11-26。每个 2×2 网格块选取一个落在湿面上的位置，沿油流回溯最多两条属于湿面三角形的边。每条短带有五个取样位。低火逐带轮换，下一轮沿各带前进，并只使用在本地油龄下已经到达的位置。墙脚和断台阻断连通边，缺少完整湿面时该短带会缩为一个火点。每个 4×4 网格区域只选一个高火候选，要求该点膜厚超过湿区均值的 1.12 倍。

单片近景主辅层的发射上限分别为 145 和 36 个/秒，中、远景主层上限分别为 60 和 26 个/秒。每个客户端世界的可见油区合计预算为 300 个/秒。先按各片低火需求分配，再把余额分给可见近景厚油处的辅层。单个高火点的目标发射率最多为 0.9 个/秒，视野外停止模拟。伤害和接触时间继续使用服务端湿面。

地形扩展时重新计算流向和膜厚，沿用路径未变的短带坐标。稳态仅在油流到达新采样位、局部退火或视距档位变化时更新相应数据。贴脸宽度使用单独的摄像机参数，移动视角无需重传火根表。

[火焰资产制作源](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_torch_bands.py) · [运行时分布与并发预算](../Publication/VillageDefense20261126/Implementation/Source/FPSGAME/WorldGeneration/VillageOilFireFront.cpp) · [正式 Niagara 资产](../../Content/WorldGeneration/TemperateHills/HotOil/TorchFieldR2/NS_OilTorchBands.uasset)

## 整片燃烧升级计划

2026-11-26 制定。分布、分层与并发预算已接入 R2，以下保留升级前基线和调优依据。目标是玩家从城门上能看见一片火沿油流展开，靠近时仍能看清单条火舌、深色油面和绕开墙脚的边界。继续使用青铜火把的两层原生火焰、颜色曲线和每片油一个 Niagara 系统。

当前地表采样间距约 45.5 厘米，每个 2×2 网格块最多保留一个火根。主层与辅层都从已到达的火根中近似均匀取点，共用原火片宽 3.6 倍、高 2.4 倍的尺寸系数。油层厚度主要影响火片大小。近景单片每秒发射上限为主层 145 个、辅层 36 个。四片都达到近景上限时，合计可达 724 个/秒。这是代码中的发射预算，实际帧耗尚无采样。

1. **先接通火根。** 沿现有地表连通关系和流向，把相邻湿点连成短带。主层轮流覆盖各带，按油实际到达的先后点火。优先补齐带上的空档，再向厚油处分配第二条火舌。沿已有湿面三角形裁剪短带，遇到墙脚、断台或干地即截断。点位随本次泼洒的种子固定。
2. **再调火焰层次和收尾。** 主层的低火沿带相接，前缘零星先亮，随后与后方火面连上。辅层只在积油较厚的少数位置升高。两层分别设置宽高，先收窄贴脸的大火片，把省下的发射量分给相邻位置。薄油先衰减，厚油留少量低火到十秒危险期结束。暗部继续露出深琥珀色油面。
3. **控制单片和并发开销。** 第一版沿用每秒近景 181、中景 60、远景 26 的单片发射上限。优先保证各可见油区的低火轮廓，再将辅层预算分给近处。多片同屏初始可试每个客户端合计 300 个/秒，作为待调上限。贴近镜头时同时限制火片投影宽度和同一位置的辅层叠加。远处只留主层，视野外沿用现有停用逻辑。伤害继续按服务端湿面结算。
4. **按变化更新。** 地表采样范围扩展时更新受影响的短带，包括因新增绕行路径而改变到达时间的旧点。地形稳定后，沿排序的到达时间推进游标。只有根表、点燃数量、视距档位或衰减值改变时，才更新相应 Niagara 参数。

首轮先改火根分布和两层分工，便于用同一火焰资产比较变化。后续性能对照固定分辨率、曝光和机位，分别看城楼俯视、贴地近景及坡面墙角。对比单片与四片同屏的透明渲染 GPU 耗时、Niagara 模拟耗时和帧时间 P95，同时观察远处油区轮廓、熄灭顺序及墙角是否串火。

## 全流程优化与火海 V3（2026-11-26）

2026-11-26 对热油系统完成四轮联动修复与表现/性能升级（尚待实机 PIE 与 GPU 帧耗验证，待备份）：

1. **取锅遮蔽与防误取消**：`UVillageOilCarry::IsStowingEquipment` 同步隐藏枪械镭射/光点/战术手电（`TacticalDeviceComponent`、`FPSPlayerBodyLaser`）、法杖晶体点光（`StaffIllumination`）、木火把点光与火焰（`WoodenTorchComponent`）、弓箭瞄具及武器准星并切为单点居中准星（`ColdSteelCrosshair`）。`IsBlockingWeaponActions` 屏蔽持锅期间的开火/瞄准/换弹/检视/近战/滑铲/冲刺撞门，禁止隐藏剑锤自动触发步行检视，并取消本地对延后 `UFPSPlayerBodyComponent` 动作态的误取消；`bTakePending` 增设 1.5s 超时防卡死，切换副手、生产工具或按 E/鼠标交互不再误落锅。
2. **非线性动作与人体工学**：重写 `VillageOilMotion.h`（蓄力回拉、爆发推举、快速倾角到位、尾段轻颤回弹与平稳归位）与 `VillageOilArmSolver.h`（双锁骨协同驱动、`lowerarm` 保持单自由度肘铰链，腕部旋前/旋后按节段距离渐变分配至前臂 twist 骨骼，兼容 1P/3P 骨架）；端锅状态叠加呼吸、步态同步起伏（`GetStridePhaseRadians`）、视角惯性阻尼弹簧、落地沉陷及碗内 2D 热油晃荡。
3. **地面火海 V3 与分级预算**：重制 [材质制作源](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_materials.py)（为 `M_OilFilm` 增加随前缘/油深/流纹脉动的火海自发光并在 8.6–10.45s 平滑熄灭，`M_OilStream` 增微弱高温余辉）并发布至 `FlowR2`；新增 [火海资产脚本](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_sea_of_fire.py) 构建 `/Game/WorldGeneration/TemperateHills/HotOil/SeaOfFireV3/NS_OilSeaOfFire`（将 `NE_Flame_01`/`NE_Flame_02` 的 `Uniform Curve Scale` 从继承火把的 0.30 恢复至 `0.88`/`1.05`，加入 `NE_Sparkles` 火星层与本地随机散射、风场漂移）。C++ 侧改为 3 槽短带复用与零拷贝 `ScratchFireRoots`，`UFluidPresentationSubsystem` 按 `EffectsQuality` 分级限流（低/中/高总发射预算 `135/195/260`/s，全场景最多 `0/1/2` 盏无阴影火海点光与 `1/2/2` 路空间循环火声，异步预载音效/资产），油区延后 0.65s 销毁实现无突跳熄灭。
4. **全链路与城防补齐**：倾倒落点支持从 18.2m 高塔俯视（最远 3200cm 射线及逐档缩进回退），本地通过 `GetLineBatcher` 绘制地面琥珀落点预警环；`Pulse`/`WetAt` 放宽大体型怪物与斜坡脚下判定至 22cm；`AVillageOilKettle` 增配低消耗炉膛无阴影点光；交互准星提示与底部持锅操作提示接入现行提示框（无运行期 PIE 实机验证）。

[火海资产脚本](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_sea_of_fire.py) · [材质制作源](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_materials.py) · [火海与预算](../../Source/FPSGAME/WorldGeneration/VillageOilFireFront.cpp) · [双臂人体工学解算](../../Source/FPSGAME/WorldGeneration/VillageOilArmSolver.h) · [火海回执](F:/FPSGAMEData/ArtProduction/HighVillageDefense/HotOilUpgrade-20261126/delivery.json) · [材质发布回执](F:/FPSGAMEData/ArtProduction/HighVillageDefense/HotOilUpgrade-20261126/Surfaces/published.json) · [编辑器编译日志](F:/FPSGAMEData/ArtProduction/HighVillageDefense/HotOilUpgrade-20261126/EditorFinal.log)

## 第一人称腕关节去扭曲与模块化穿衣适配（2026-11-26）

2026-11-26 修复端油锅手臂腕部扭曲与缺少角色服装/手套的问题（待备份 · 未跑实机 PIE/多人联机）：

1. **模块化服装与手套挂载**：原 `UForgeArmsMeshComponent` 继承自 `UPoseableMeshComponent`，被 `UFPSModularOutfitComponent::DiscoverSources()`（仅扫描 `USkeletalMeshComponent`）完全忽略。新增继承自 `USkeletalMeshComponent` 的 [第一人称油锅手臂组件](../../Source/FPSGAME/WorldGeneration/VillageOilArmsMeshComponent.h)（在 `FinalizeBoneTransform()` 注入解算姿态并维护扩编包围盒），并在 [UFPSModularOutfitComponent](../../Source/FPSGAME/Characters/FPSModularOutfitComponent.cpp) 新增 `RefreshSources(bool bDiscoverNow)`；`PrepareVisual()` 创建后立即触发发现，`UpdateVisual()` 显示/隐藏或取消时同步调用 `RefreshVisibilityForSource()` 保证零延迟显隐。
2. **零扭曲腕关节与肘位重建**：重写 [VillageOilArmSolver.h](../../Source/FPSGAME/WorldGeneration/VillageOilArmSolver.h)，改由原骨架 `BindPose` 与实测手掌朝向协同求解 `LowerDeform` / `UpperDeform`（参考 `Super90SupportArmNode`），去除 `±68°` 截断及 `RestPose` 双重旋拧叠加；`lowerarm_aux`、前臂中段 `twist_02` 与腕端 `twist_01` 全部从原生 `BindPose` 重建，对称修正 `Grip()` 与 1P/3P 持锅下垂肘位，倾倒时右肘随推动平稳抬升。
3. **离线复查结果**：通过 `FPSGAMEEditor Win64 Development` 编译与 `VillageOilMotionReview`（`-OilCarryOnly` 及 Jason / Kaitlin `-OilScreens -AllowCommandletRendering -RenderOffScreen -d3d12`）全部检查：1P/3P 四臂 `twist=0.00°`、`seam=0.00°`，`view_cm=0.0000`、`body_cm=0.0000`、`lip_cm=0.0000`，实穿 `ue_chainmail_shirt` + `ue_modern_tactical_gloves` 挂载 `visible_parts=3` 且取消即隐藏 `hidden_on_cancel=1`。[复查输出与对比截图](F:/FPSGAMEData/ArtReviews/HighVillageDefense/HotOilArmsOutfit-20261126) · [验证命令列](../../Source/FPSGAME/Development/VillageOilMotionReviewCommandlet.cpp)

## 油锅与手锅模型材质升级及高帧率法术复用落点环（2026-11-26）

2026-11-26 升级大小油锅几何与专用 PBR 材质，并将泼油地面落点预警环迁移至法术复用高帧率贴花方案（待备份 · 未跑实机 PIE/多人联机）：

1. **模型精细度与顺滑法线重建**：重写 [author_oil.py](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil.py)，为 `SM_OilHearth`（7,472 面）与 `SM_OilHandPot`（5,688 面，均低于 8,000 面 Nanite 阈值以规避粗粒度回退网格）提供真实逐顶点顺滑法线与无缝柱面 UV；小手锅新增对齐 `VillageOilMotion::Lip` 的浇注嘴、黄铜底部导热底环、双腰箍、铆接鞍座、圆顶黄铜铆钉及对称炭栎木手柄（保持 `(0, ±18.9, 5.6)` 与 `r = 3.065 cm` 握点）；大油锅石砌火塘新增发红炭堆与交叉炭木，平衡炉膛点光至 `420 lm`、`EmberIntensity = 2.8`。
2. **专用 1024×1024 PBR 与热油抛光**：通过 [author_oil_prop_textures.py](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_prop_textures.py) 生成 `OilCastIron`、`OilAgedBrass`、`OilCharredOak`、`OilHearthEmbers` 四组 1024×1024 PBR 贴图并通过 [import_oil.py](../../SourceAssets/HillsVillageHighWall20261120/HotOil/import_oil.py) 发布至 `/Game/WorldGeneration/TemperateHills/HotOil/PropsR2/`（`M_OilCastIron`、`MI_OilCastIron_Kettle`、`MI_OilCastIron_HandPot`、`M_OilAgedBrass`、`M_OilCharredOak`、`M_OilHearthEmbers`）；同步微调 `FlowR2/M_OilBody` 与 `M_OilBubble` 的高光与深琥珀对流自发光（[author_oil_materials.py](../../SourceAssets/HillsVillageHighWall20261120/HotOil/author_oil_materials.py)）。
3. **法术参数复用与高帧率预览环**：在 [VillageOilCarry.cpp](../../Source/FPSGAME/WorldGeneration/VillageOilCarry.cpp) 移除每帧 CPU 划线（`ULineBatchComponent`）及无条件 `TActorIterator`，改为懒创建并持续复用单个 `UDecalComponent` + `UMaterialInstanceDynamic`（`Arms` / `ViewPot` / `WorldPot` / `ViewOil` / `WorldOil` 关闭 `bReceivesDecals`），直接复用流星预览材质 `MeteorSpellAssets::Preview`（`/Game/Skills/FireMagic20260921/PreviewSurface20261022/M_MeteorAimPreview`）与 `FPSMagicPreview::LineColor()`（`Tint`、`Center`、`SurfaceNormal`、`ImpactRadius` 随工坊热油范围动态绑定 `275–500 cm`、`FieldRadius = min(92, OilRadius*0.36)`）；采用 `0.5 cm / 0.08°` 镜头增量脏检查与 `ATemperateHillsWorld` 弱引用缓存，静置帧零拷贝且无每帧分配。
4. **离线复查结果**：通过 `FPSGAMEEditor Win64 Development` 编译与 `VillageOilMotionReview` 三轮审查（`-OilCarryOnly` 及 Jason / Kaitlin D3D12 离屏渲染均退出 `0`）：`OIL_PREVIEW init=1 tint=1 min_tracked=30 hide=1`（30/60/144 Hz 每档 30/30 帧同实例指针零重建跟踪通过）、`preview_ok=1`、`contact=1`、`twist=0.00°`、`seam=0.00°`、`visible_parts=3`、`hidden_on_cancel=1`。截图目视确认大锅光滑石砌与炭火、小手锅黄铜底环与双环地面贴花均正常渲染。[最终网格回执](F:/FPSGAMEData/ArtProduction/HighVillageDefense/HotOilPropsPreview-20261126/MeshesFinal/published.json) · [油面材质回执](F:/FPSGAMEData/ArtProduction/HighVillageDefense/HotOilPropsPreview-20261126/Surfaces/published.json) · [复查截图与日志](F:/FPSGAMEData/ArtReviews/HighVillageDefense/HotOilPropsPreview-20261126)
