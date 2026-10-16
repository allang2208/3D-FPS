# 药水工作台与炼药进入页整理发布

本轮覆盖现代离心机/魔法坩埚工作台制作、建筑“其他”栏接入、坩埚分支、台面点击与拖动、温度计、装瓶表现，以及按锻造布局制作的进入页和 V12 配方/批次状态修复。离心机注射剂小游戏尚未开发。

## 发布内容与依赖边界

- 发布 22 个炼药运行源码文件、八个配方、可分离的工作站/库存/界面接入、原创作者与导入脚本、说明及 SKILL。进入页共用 `UColdSteelForgeBoard` 与物品浮窗效果数据，已有炉次使用支付时的配方与产物快照。
- 共享文件只暂存炼药代码块；工作区中的生存、武器、箱子搜索、魔法轮盘等其他改动保留。`InventoryRevision()` 作为炼药请求使用的现有只读版本接口随同发布。
- `ColdSteelPlayerState.cpp` 的五处炼药档案赋值/比较与未公开库存宿主交织，保留为 `Integration/player-profile-alchemy.patch`。另外两份手册审计补丁只保存本轮为解除编译阻塞所做的参数改名，不包含或运行独立审计。
- `integration-manifest.json` 给出每个补丁的 LF 归一化前置/结果 SHA-256。`captured_head` 只是取证点，不能把它当作这些补丁都能直接套用的宿主。具备对应前置后再合入源码；本机已经包含结果，不能重复覆盖。
- 当前运行/界面文件保留必要的物理手册调用。后续书页、封面、阅读布局和独立审计属于并行手册维护，本批不把其整套实现提交；所需 12 个当前源码文件及散列列在 `manual-prerequisites.json`。恢复时使用当前手册实现，不退回早期 V3 代码。

因此，本提交是当前功能的源码与制作配方发布，**不是干净检出即可独立构建或运行的完整资源包**。需合入上述手册/库存宿主前置并恢复授权资源。共享本机工程仍保持完整，不因暂存子集而回写、删除或回退任何玩法文件。

## 保留的制作与恢复链

| 部分 | 保留的作者源及入口 | 恢复依赖 |
| --- | --- | --- |
| 工作台造型、桌面及离心机 | `ModelV1/Scripts`、`Authored/PotionWorkbench_Editable.blend`、`Export/PotionWorkbench_Assembly.blend` | 原枪械工作台木纹供体、原创表面图集；这是后续版本仍读取的源，不能按 V1 名称删除 |
| 建筑“其他”栏 | `IntegrationV1/Scripts/prepare_buildable.py`、导入和注册脚本 | `V1` 静态网格、简单碰撞、LOD 与已有 `DA_VoxelBuildPalette`；不覆盖其他建筑条目 |
| 坩埚、材料与音效 | `RuntimeV2/Scripts/author_runtime.py`、`author_audio.py` 及对应导入/安装入口 | `RuntimeV2` 包、物品目录中的六类炼药材料与八种成品；当前配方以 `Content/ColdSteelData/alchemy-recipes.json` 为准 |
| 原魔法书供体 | `ManualV3/AlchemyManual.blend`、作者脚本与 `ATTRIBUTION.md` | 后续 `AlchemyManualReader` 与 `AlchemyManualFinePress` 仍读取该 Blend；保留 evildeer 的 CC BY 4.0 出处及改作说明 |
| 勺架与沙漏布局 | `RefinementV4/author_layout.py`、`import_rests.py` | `SM_AlchemyToolRests` 与生成的 `AlchemyWorkbenchLayout.h` |
| 可点击器具、金色描边 | `InteractionV7/author_assets.py`、`hover_outline.hlsl`、导入脚本 | 添加剂容器、火力旋钮及实际命中区域；素材安装与运行高亮是不同环节 |
| 温度计 | `ThermometerV9/author_thermometer.py`、导入/安装入口 | `ModelV1` 可编辑源、V9 主体及 `AlchemyThermometerLayout.h`；读数来自实时温度 |
| 装瓶液体 | `InteractionV10/author_materials.py`、`install_assets.py` | `M_AlchemyBottlingFlow`、`M_AlchemyVesselLiquid`、实际瓶口与舀勺运动接口 |
| 水面与手臂 | 既有铁匠台水体、BarePalmV7/M4 | 复用本机共享材质/模型，不复制或公开未核准原始资源 |

以上相对作者路径位于 `SourceAssets/PotionWorkbenchDesign20261015`。独立 `UEImportHost` 仍被作者/安装脚本及并行物理手册使用，保留在本机；只在用户授权的制作阶段运行导入命令。本次整理未运行它们。

二进制模型、FBX/Blend、贴图/图标、声音、字体、UE 包、宿主内容、日志及回执按仓库规则留本机。本提交不授予外部资源新的再分发许可，也不把脚本公开等同于资产已恢复。静态注册回执和各版实际保存回执均保留。

## 退役与技能沉淀

`trash/alchemy-workbench-retired-20261016` 收纳 151 个文件，共 2,183,980 字节。包括修改前源码/目录/资产快照、已被最终源码取代的一次性改码/旧配方生成脚本，以及已完成阶段的旧构建/回执驱动。逐文件原路径、目标、字节数、SHA-256、原因和替代物见 `archive-manifest.json`；移动后已读回核对散列。仅移动本轮制作目录中的明确废案，没有移动正式 Content 包。

历史文档中的 `Before/`、旧迁移脚本和旧构建驱动路径改由归档清单定位；历史构建/保存日志和 JSON 回执仍在原处，不能为了重做旧回执而恢复过时改码脚本。

个人技能及工程对应部分已同步：

- [成品预览与异步准备](../../../skills/ue5-ui-umg-slate/references/product-preview-readiness.md)：共同数据源、缓存失效、批次绑定的准备意图、作废确认和按钮语义变化。
- [已支付工件与退款](../../../skills/ue5-cpp-gameplay/references/paid-workpiece-quality.md)：Resume 不扣料、按实际 Escrow 合并退半、原子结算、旧进度与回执排序。
- [炼药台交互](../../../skills/ue5-world-interaction/references/alchemy-tabletop-interaction.md)：手册/观察反馈、器具身份、捕获搅拌、旋钮、温度仪表及装瓶时序。

## 构建与验收状态

最近一轮 V12 在完整本机工作区完成 Game（328.57 秒）与 Editor（207.78 秒）后台构建，均为 `Result: Succeeded`；记录在 `SourceAssets/PotionWorkbenchDesign20261015/EntryV12/delivery.json`。这不是本次公开暂存子集的独立构建或联机证明。

V12 核对了八个配方的成品、恢复效果、材料需求、继续、领取、作废、满背包及重复请求的源码路径。本次整理只进行归档散列和 Git 发布检查，没有打开 UE、游戏、PIE、commandlet 审计或自动化测试；视觉、液体、鼠标交互和实际主客机体验仍待用户验收。
