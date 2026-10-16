# 枪械配件整理与发布 · 2026-10-16

本轮范围为伸缩后托/均衡与幻影后握把表面、幻影接颈、A762 ADS 材质、M16/ASH 瞄具底座、改造面板类别记忆，以及 SUPER90 收束器、鸟笼消焰器、消音器、加长管式弹仓和封闭侧壁鸭舌。M870、步枪消音声音、战锤、怪物、工作台等并行任务不属于本次发布。

## 当前制作源与恢复顺序

| 功能 | 本机活动作者源/入口 | 必须保留的前置 |
| --- | --- | --- |
| M16 伸缩后托 | `SourceAssets/M16StockMaterialDiagnosis20261015` | 原始低模及匹配法线；`M16StockDonor20261015/Final` 的原厂接口；HardSurface 的历史保存回执 |
| 其余九枪伸缩后托 | `SourceAssets/TelescopicAllGunsRepair20261015` | `TelescopicStockSurface20261014/Inputs` 的原始逐枪装配；原 StockRefresh 高低模/烘焙 |
| M16 均衡握把 | `SourceAssets/M16AttachmentSurface20261014` 中握把独立修复 | 主体/接颈/接口分区映射及对应角点 UV；不要重用该目录已否决的后托 R2 法线 |
| 幻影握把 | `PhantomGripSurface20261015` → `PhantomGripJunction20261015` | `Phantom_Canonical.blend`、`M4_HighNormalProbe.blend`/`source_probe.py` 和各枪当前 Exports；LMG201 保留独立分支 |
| A762 ADS | `SourceAssets/A762ADSSurface20261015` | 实际中性法线及既有微法线、干湿材质配方；Engine DefaultNormal 不能按名称当平坦图 |
| M16 / ASH 瞄具 | `M16OpticSeat20261015`、`ASH12OpticSeat20261015` | 当前宿主与镜体导出；同步瞄准插座，不整体替换原枪 |
| 三款基础枪口 | `Super90Choke20261015`、`Super90Birdcage20261015`、`Super90Suppressor20261015` | 原创作者模型、WS1、原生枪体；消音音频依赖原授权声音 |
| 加长管式弹仓 | `Super90ExtendedTube20261015` | 原厂端帽/材质分区；`CompatibleMuzzles` 中收束器和消音器兼容外壳 |
| 鸭舌 | `Super90DuckbillV2_20261016` → `Super90DuckbillClosedSides20261016` | V2 可编辑源及逐级 LOD；V1 保留的导入/打包模板仅作为 V2 脚本输入，V1 外观已退役 |
| 正式图标 | `ShotgunIconsFramed20261015/Final`，弹仓与封闭侧壁鸭舌各自最终 PNG | 认可金属框母版及实际模型参考，生成提示词随源发布 |

本机完整工程已经应用上述代码与资产。公开的是原创 C++、作者/导入脚本、稀疏参数与文档；Blend/FBX/GLB、PNG/WAV、NPZ/密集 profiles、UE 包、授权母版、Python 第三方库、回执和日志留在本机。不能仅凭本次源码提交恢复完整可运行游戏，也不对依赖素材另行授予再分发许可。

## 源码发布边界

- 独立资产定义、弹仓显示、散布数学函数、属性读取、分类、瞄具路径、改造面板类别记忆及可分离的目录/预加载/材质区段修改发布到原路径。
- 角色开火、枪口与火光、权威退弹、装填时钟、准星和审计夹具共 18 个目标以 `Integration/*.patch` 保存。它们与尚未公开的 M870 谓词、档案协议等前置交织。补丁只包含本轮修改；`integration-manifest.json` 为每个目标记录完整宿主前置与结果的 SHA-256，捕获 Git HEAD 只是追溯点，**不是所有补丁可以直接套用的基线**。
- 恢复时先具备相应宿主前置，再按目标路径应用补丁并合入正常源码。不要覆盖本机工作区——本机已经是结果版本。审计类只在用户明确要求对应测试时使用。
- 未把其他任务的 M870 玩法、步枪声音、战锤或公共库存改造顺带提交。索引候选与发布清单按精确路径构造，未覆盖共享工作区。

本轮确认的两处修复：实际弹道只读取已安装配方，预览不再提前生效；服务器按真实弹量处理弹仓缩容和实体溢出退弹，并以库存版本拦截旧档案重复退弹、终止旧装填方案。

## 退役与保留

`trash/weapon-attachments-retired-20261016` 收纳 237 份已确认废案/旧备份/一次性编辑器操作，共 711,093,381 字节。包括被否决的硬表面替代后托、R1 平滑输出、第一版鸭舌模型、旧程序图标场景和不再参与重建的表面实验。逐文件原路径、目标、大小、SHA-256、原因与替代物见 `retired-files.json`；移动后已经重新读取散列核对。

临时隔离测试工程另归档为同目录 `IsolatedAuditHost`：8,003 个普通文件、6,144,629,263 字节，移动后散列一致。其 2 个 Content 目录联接未遍历，联接指向的正式资源不属于废案；详细本机清单为 `isolated-host-manifest.json`。原 `D:/FPS3D/ShotgunAttachmentAudit20261016` 不再保留常驻副本。

旧目录中仍被最终作者读取的低模、接口、模板、法线对照图和回执保留；未因版本号或目录日期较旧而整包删除。正式 Content 包没有离线移动，避免绕开 UE 引用关系和已加载资产。

## 已有证据及本次未执行项

此前两处修复已完成本机 Editor/Game 构建；权威及组合检查曾完成 78 项、0 失败。这不是本次发布子集的独立构建结果。

真实双进程检查尚未取得整轮通过：记录中远端模型/表现弹道通过，但首组射击拒绝及方向比较存在失败；审计夹具已修正冻结坐标、弹道回收和量化向量比较，最后复跑按用户要求中止，不能当作联机完成证明。源码覆盖记录在 `SourceAssets/Super90AttachmentAudit20261016/coverage.md`。

本次只进行归档散列、依赖范围和 Git 发布检查；按用户要求不再启动 UE、运行游戏或重新构建验收。装配、首入房射击、存档、延迟/丢包/重连和完整联机效果由用户测试。

## 技能沉淀

个人 `ue5-weapon-workflow` 与工程对应章节同步补入 [表面与霰弹枪组合](../../../skills/ue5-weapon-workflow/references/attachment-surface-and-shotgun-combinations.md) 及 [弹药权威/缩容](../../../skills/ue5-weapon-workflow/references/shotgun-authority-and-presentation.md)。保留用户“不主动测试、不跨任务协调、后台制作”的执行边界。
