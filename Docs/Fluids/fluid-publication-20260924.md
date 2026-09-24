# 流体制作归档与源码发布（2026-09-24）

本次整理覆盖 2026-09-23～24 的原生流体基础库、枪口烟 V14 密度／V15 分层表现、火系燃烧场与命中烟、水花方块修复和全水体接入、毒液／毒池，以及两轮流体交互。流体技能标准已进入 `skills/ue5-fluid-vfx-workflow/`，个人技能目录同步维护。

## 归档与保留

68 个被替代的制作快照与 Blender 自动备份，共 25,121,140 字节，已移动到本机 `trash/fluid-publication-20260924/`，按原工程相对路径保留层级。全部移动后 SHA-256 读回一致。原路径、目标、大小、散列、原因与保留替代物见 [逐文件归档清单](fluid-publication-20260924-archive.json)。本次没有删除文件，没有移动正式运行资产。

归档仅包含各流体制作目录下已被后续成果替代的 `Before*`／`Backup` 与存在对应正式 `.blend` 的 `.blend1`。历史回执仍描述当时路径，需要恢复旧快照时通过清单定位；重新执行作者产生的新备份不属于本批归档。

保留以下有效依赖：

- 原创 Mantaflow `.blend`、OpenVDB／FLIP 缓存、Alembic、有效 EXR／PNG 导出及帧清单。
- V14 烟密度与导入入口，作为 V15、爆燃烟和冷雾的共同输入；旧名字不意味着退役。
- Foundation 素材和 UEAuthoring 工程，作为 SVT、液体网格和 Epic 模板的制作／恢复入口；未投入场景不等于废案。
- 自然水花四套缓存、图集、空帧处理及方片修复源；原作者仍读取的 Crown／Drop HLSL。
- 现用 Niagara、材质、模型、作者母版、来源记录与制作回执。仅在用户要求针对性排查时运行保留的诊断脚本。

## 公开内容与本机依赖

提交原创 C++、Python 作者脚本、HLSL、紧凑烘焙参数／轮廓、项目流体配置、文档和技能镜像。`.gitignore` 对本批 14 个 SourceAssets 目录限定源码与少量明确参数清单，防止把缓存、传输日志或素材包当作源码提交。

完整内容仍需从合法本机工程恢复。Git 不包含 UE 包、Blender／FBX／Alembic／VDB、PNG／EXR 图集、商业包原件、密集材质图导出、模拟缓存、专属 UEAuthoring 工程、构建产物及 trash。Epic 母版遵守引擎授权；Realistic Starter VFX Pack Vol 2、Military Trench 等沿用各自来源许可。未提取 COD 素材，未复制 GPL 参考实现，没有引入新的付费插件或授权声明。

恢复运行资产时保留这些目录及其既有依赖：

- `Content/Fluids/Foundation`、`RiverPilot20260923`、`RiverSplashNatural20260924`、`VenomProjectiles20260924`、`FluidInteractions20260924`、`FluidPolish20260924`。
- `Content/Weapons/GunplayFX` 的 V14 密度、V15 两套烟系统、对应材质和 `Impacts/Blood` 新材质。
- 火球当前球核、`FluidCore20260923`、`ImpactRealistic20260914`；火系 `RealisticV5`；冰锥 `FrostV2`。
- 喷泉 `M_FountainWaveWaterV3`、地牢 `M_Dungeon_ShallowPuddle`、原腐液表面与怪物毒雾材质。

来源与路径详细入口见 [流体接入地图](../../skills/ue5-fluid-vfx-workflow/references/fpsgame-map.md)。运行引用使用完整对象路径；新增贴图必须实际导入，不能仅恢复脚本。

## 重建顺序

优先恢复已保存的本机 Content。确需从源重制时，按具体对象选择作者函数，不默认执行全量：

1. 恢复合法 Epic／项目母版和本机源输入；需要 Foundation 时先完成其独立制作和清单发布。
2. 密度／燃烧场／水花图集先恢复或导出，再执行对应 UE 导入；水花保留零顶点透明帧、有效帧截断与单图 mip 驻留。
3. 运行对应枪口／火球／陨星／毒液作者入口；上游完整生成器已接回局部流体安装函数。
4. 水面轮廓有改变时再导出并生成紧凑查询数据；全水体覆盖、共享交互、第二轮接触／冷雾／血液／尾迹按所需增量安装。最后一层应保留 `DetailReduction`、`Wind`、`SmokePlane0..4` 和尾迹参数，避免旧重建器覆盖新版输入。
5. 根据依赖顺序执行必要常规 C++ 构建和指定资产编译保存；不自动打开编辑器或游戏。

## 发布范围与完成口径

共享文件中的伤害反馈、毒免疫／净化、命中音效、矿材外观、技能结算和地牢装配等其他任务修改不纳入本批。流体所需改动按块暂存，工作树中的其他内容保留。基础插件配置只加入 Niagara、Niagara Fluids、Water、GeometryCache 和编辑器 AlembicImporter，以及体积／水面碰撞相关配置。

本批执行用户授权的仓库归属、归档散列、提交内容、大小、许可、敏感信息和差异检查。没有启动 UE、游戏、PIE、截图或性能测试。此前流体资产已保存，第二轮共享工作树常规构建记录为 `Saved/BuildEditor/build-20260924-154901.log`；本次源码整理未单独重编译剥离其他并行改动后的提交，不能将历史构建说成提交独立验收。

用户已确认水花方块修复及枪口烟基本效果；第二轮五项的实际观感和性能仍由用户确认。公开源码发布不等于完整素材远程备份。
