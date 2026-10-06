# RSH-12 改造发布与本机资源恢复

本次整理范围为 RSH 对话自 10 月 3 日上一批发布后的握姿、双持换弹、瞄具、枪口、握把、材质、战术设备与原厂扳机图标。当前采用双动五发设计、715 共用动作和 RSH 私有姿态层；用户已认可基础双手握姿与 ADS 同步。后续修订的资产保存和原生构建记录不等于全部动作或配件已获游戏验收。

## 当前内容与数值

| 内容 | 当前接入 |
| --- | --- |
| 基础参数 | 后坐力由 180 调到 225；稳定性按此前用户要求减少 25 点；基础腰射扩散倍率 4 |
| 方形瞄准镜 | RSH 专属，开镜耗时 −5%；从本枪旧 holographic ID 迁移 |
| 战术方形瞄准镜 | RSH 专属，固定 1.5 倍、开镜耗时 −5%；从本枪旧 EOTH ID 迁移 |
| PSO / 其他通用瞄具 | PSO 原侧挂架适配；全景、棱镜、LPVO 沿用本枪私有导轨座 |
| 大口径消音器 | 当前为加长方盒；后坐力 −30%、稳定性 +30%、弹速 −20%、开镜耗时 +10% |
| 大口径枪口制退器 | 后坐力 −30%、稳定性 +20%、开镜耗时 +10%；保持非消音 |
| 加重握把本体 | 稳定性 +15%、后坐力 −10%、开镜耗时 +5% |
| 轻型快拔握把本体 | 拔出速度 +100%（动作时长减半）、开镜耗时 −20%、后坐力 +5% |
| 防滑纹 | 原厂、加重、快拔本体各自适配三种通用防滑表面 |
| 通用前握把 | 五种已有改造；单持使用支撑手，双持保持单手握姿，只保留该前握把减益 |
| 战术挂件 | 通用 laser / flashlight 二选一；前段下导轨夹座向持枪者右侧偏置，与前握把独立 |
| 原厂扳机图标 | 从实际 `17_l` 机构件制作，灰阶金属框，专属键 `ue_rsh12_trigger_false` |

数值以公开 `Content/ColdSteelData/gunsmith.json` 的 `ue_rsh12` 对象为准。稳定性是现有后坐/回稳公式中的属性，目录内保存的是计算得到的倍率，并非简单写入 `0.75`。本批目录提交只替换 RSH 对象，不带入其他枪或并行中的通用改造。

## 动作与抓握

- [双手握姿与 ADS](rsh12-unified-grip-20261004.md)：idle/aim 共用序列、采样时钟和握姿层，整组视模对齐瞄线；检视食指不再叠加伸直端点的扣扳机修正。
- [五发装填器](rsh12-speedloader-five-20261003.md)：保留逐发装填及可选快速装填器；原生绑定、机械和接触资料沿用本机输入。
- [双持换弹循环修复](rsh12-dual-reload-fix-20261004.md)：退壳事务识别 RSH，避免动作失败后不断自动重启。
- [开仓收手与脱壳](rsh12-dual-reload-drop-20261004.md)：开仓阶段整组渐降，精确释放姿态承接静态壳体，使用既有有界 FX 池模拟重力及落地。
- [前握把](rsh12-foregrips-20261004.md)：基于已接受的成组手型适配本枪；共振握把腕臂后续由 `RSH12ResonanceWrist20261005` 调整，检视连续性由 `RSH12InspectArmRepair20261005` 修复。

用户否定的 `RSH12InspectGrip20261004` 与旧单动资料保留为拟合工具、绑定基准和关键失败记录，不能作为当前握姿入口。当前 profile 路径以 `RSH12WeaponAssets.h`、`RSH12ForegripAssets.cpp` 为准。

## 本机恢复顺序

公开作者脚本含本机绝对路径；在其他主机先修改工程、Blender、UE 和合法素材位置。不要批量运行全部历史导入器覆盖现用资产。

1. 恢复 `SourceAssets/RSH12Integration20261003/Original` 中 Medji 原包、canonical_parts，以及合法 715/V7 手臂供体、原生采样、绑定与皮肤权重。保留 `RSH12Grip20261003/BeforeAuthored/Integration`，它仍是绝对拟合的输入。原作者署名见 [Medji / CC BY 4.0](../ThirdParty/RSH12-Medji-CCBY4.md)。
2. 恢复 Native715、ContactRepair、Speedloader 的最终网格和 profile；叠加 UnifiedGrip 单持基础层、DualReloadDrop 两侧私有层。脱离弹壳/完整弹共有 20 个静态网格，位于 `/Game/Weapons/RSH12/DualReloadDrop20261004`。
3. 恢复 Optics、PSO、OpticsRefit、CompactOptics 的最终网格、镜片和瞄线 socket。当前入口为 `RSH12OpticAssets.h`；旧 ID 的转换仅作用于 RSH。
4. 恢复 GripSurfaces、HeavyGrip/Integration20261005、QuickDrawGrip/Integration20261005 和 Foregrips；按 ResonanceWrist、InspectArmRepair 的最终作者输出恢复 profile。GripSurfaces 的本机 `.deps` 是制作依赖，继续保留；公开仓库不复制 vendored Python 库，使用脚本所需 NumPy / Shapely 环境。
5. 恢复 CubeSuppressor 的最终加长版本，再恢复 MaterialFinish 表面修订。旧 HeavySuppressor 目录仍提供规范接口和材料制作输入，不能整目录清空。新制退器恢复 `MuzzleBrake20261005` 的 11,138 三角形 LOD0、5,706 三角形 LOD1、Shell/Trim/Recess 材质和图标。模型仅为游戏外观。
6. 恢复 `Tactical20261005/Meshes/SM_RSH12_{laser,flashlight}`、私有聚合物干/湿材质和安装座金属。其制作源依赖本机 M1911CompactFit 两款已接受主体、715 聚合物材料及 RSH RailInsert；保留 UV0、法线与光学遮罩。共享战术图标继续使用已存在的 `tactical_laser` / `tactical_flashlight`。
7. 合并恢复 `/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials`，保留新枪口、握把、前握把、装填器及战术挂件映射。恢复专属 PNG 与 `FramedFirearms` 对应 Texture，尤其最新 `ue_rsh12_trigger_false`；不能只恢复根目录旧副本。

完整最终 `.blend`、FBX/GLB、PBR、概念图、预览、PNG、UE 包、密集蒙皮/姿态、供体素材和本地回执均保留在本机。合法使用这些素材不自动授予整个源包再分发权；公共 Git 是源码和制作配方，不是完整可运行 Content 或二进制备份。

## 既有落盘记录

以下是制作期间已存在的回执，本次整理没有重跑导入或编译：

- QuickDrawGrip/Integration20261005：模型、材质、图标与目录已保存，原生构建成功（基础 DLL 记录 UTC 2026-10-05 13:40:39）。
- MuzzleBrake20261005：13 个资源已保存、目录接入、构建成功（UTC 2026-10-05 14:58:02）。
- Tactical20261005：8 个资源已保存，原生目标成功/已最新；复用基础 DLL UTC 2026-10-05 15:55:00，不宣称此次重新编译全部文件。
- FactoryTriggerIcon20261006：PNG 及 UE Texture 均已保存；无 C++ 改动，无需 DLL 构建。

## 整理与发布边界

11 个 `.blend1` 自动备份已移到本机 `trash/rsh12-publication-20261006`，共 125,143,634 字节；每个都有保留的正式 `.blend`，没有活动源码引用。原路径、目标路径、大小、SHA-256、理由和替代物记录在 [归档清单](../AssetArchives/rsh12-publication-20261006.json)，移动后已读回核对散列。保留活动依赖、正式可编辑源、导入回执和失败证据，没有按日期清空旧目录。

个人技能维护源和仓库镜像已同步：共同握点及 ADS 时钟、短枪腕臂与检视连续性、五发换弹事务、握把本体/防滑纹分槽、拔出倍率、右偏战术安装架、真实原厂件图标和实际图标加载目录。

本批使用独立 Git 索引和精确源码片段；共享文件里的消耗品、第三人称、传说改造分级、其他武器、怪物与场景改动仍留在原工作区。RSH 专属卡片在公开候选中沿用已发布的卡片逻辑，未带入并行的新分级实现。发布检查仅覆盖本批差异、脚本语法、文件边界、链接与敏感信息；没有启动 UE、游戏、渲染或玩法回归。最终游戏效果由用户测试。
