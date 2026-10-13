# 搜索收集物与两厅投放：整理发布

2026-10-13。当前本机工程已保存17件收集物模型、图标和材质，以及31个容器的搜索投放/联机实现。公开发布原创制作配方、物品目录、概率配置、独立库存改动、技能参考和联机接入补丁；模型、贴图、参考照片、UE包、日志、导入宿主和构建产物留本机。

## 当前规则

- 4件文件、5件检修材料、8件机房硬件；另复用4件日常补给，搜索池共21件。纪念腕表尚未制作，不投放。
- 接待大厅15个、分流大厅14个、已列出的服务器柜2个。首次生成必出1～3件，概率70%/25%/5%；按物品权重不放回抽取，同一品类每箱最多一次。
- 图标按形状居中：条状物水平或垂直，宽幅物品沿用立体展示视角。显卡占2×1，原有旋转实例迁移后1×2；物品身份、数量和能保留的格位不变。
- 原创CS标识；网卡、阵列卡、CPU采用白/银/黑配色。GPU/内存/SSD沿用原创标识版，GPU最终UE网格CSR3C使用CSR3B导出几何。

完整目录与概率见 [物品设计](../../Gameplay/search-item-catalog-v2-20261012.md)、[投放表](../../Gameplay/facility-search-loot-20261013.md)、[图标布局](../../Art/collection-icon-layout-r2-20261013.md)。制作台配方设计不等于已实现扣料，本批不把售卖/制作系统作为新增完成功能。

## Git 与本机实现的边界

目标仓库为 `https://github.com/allang2208/3D-FPS.git`，根目录直接提交至main，正常非强制推送。

共享库存/网络请求的底层仍有未提交的并行开发，且角色与库存文件混有其他任务变更。为保留这些改动而不夹带，本次：

1. 直接提交17件收集物定义、两件食物稀有度、浅色背包底色、收集物地面模型加载、GPU占格及三件硬件旧实例外观迁移、对应打包路径。
2. 直接提交新概率配置、制作配方脚本、说明和SKILL。
3. 将本轮搜索/联机接入的8个原生文件差异发布为 [scene-search-integration.patch](scene-search-integration.patch)，同时记录 [依赖基线哈希](integration-baseline.json)。完整本机工程已应用这些改动；公开分支并未因此获得完整共享库存框架。不要在当前本机再次应用补丁。

补丁包含首次搜索生成、运行隔离、共享结算标记、库存版本校验、失败回包访问检查和两项代码测试。它依赖现有 `ColdSteelInventoryRequestTypes`、`ColdSteelSharedInventorySubsystem`、角色RPC/网络视图/交易日志等未发布底层。待该底层正式进入仓库后，以基线逐项接入，不能把此补丁独立称为可构建的联机模块。

本次未暂存其他任务的货币替换、背包容量重排、魔法书、木工、技能、枪械和全局联机框架。原宝箱表的损坏引号已在本机修复；相对于当前Git基线剩余差异属于其他任务，未夹带发布。

## 资产恢复链

完整本机根为 `D:/FPS3D/FPSGAME`。保留合法参考/资产后，通过各批次 `Scripts` 恢复纹理、模型导出、隔离导入与正式安装；按制作阶段执行，不能运行所有目录脚本覆盖已采用版本。

| 内容 | 保留的制作源 |
| --- | --- |
| 文件4件 | `SourceAssets/SearchDocuments20261012` |
| 检修5件 | `SourceAssets/SearchMaintenance20261012` |
| 硬盘、计算模块及旧路径几何兼容 | `SourceAssets/SearchServerEquipment20261013` |
| GPU、内存、SSD | `SourceAssets/ServerOriginalMarks20261013` |
| 网卡、阵列卡、CPU中性色 | `SourceAssets/ServerNeutralPCB20261013` |
| 当前17件图标 | `SourceAssets/CollectionIconLayoutR2_20261013` 与 `Tools/AssetPipeline/collection_icon_orientation.py` |
| 当前搜索概率 | `Content/ColdSteelData/scene_search_loot.json` 与 `SourceAssets/FacilitySearchLoot20261013/Scripts/author_pools.py` |

制作顺序：物品身份/占格 → `prepare_textures.py` → `author_models.py` → 隔离宿主导入/安装 → 目录接入 → 当前R2图标批次。原创GPU另执行切线修订流程；中性色版保留 `apply_legacy_appearance.py` 和对应纹理别名，以兼容旧物品引用。保存/安装回执以及当前model/texture清单在本机保留，不作为公开媒体上传。

参考照片仅保留于 `ServerReferenceRemodel20261013/Reference`；旧品牌模型已退役。旧网卡/阵列卡/CPU的正式UE资源仍服务旧存档，保留原位。未核准再分发的二进制内容不因此次推送授权而自动公开。

## 归档

确认废案移至 `trash/search-collectibles-20261013`，逐文件原路径、目标、大小、SHA-256、原因和替代物见 [archive-manifest.json](archive-manifest.json)。本批归档224份、257,557,653字节（约245.63MiB），移动后散列已读回一致。

范围包括V1填充物设计、统一斜向旧图标、旧品牌制作输出及导入宿主、旧CSR3导出、最初GPU/内存/SSD几何、被替换的绿色表面备份和Before快照。仍参与当前恢复的51条模型源/导出引用、原始参考图、当前母版和历史构建记录保留。历史文档/回执里的原路径可通过本清单定位，不改写当时的证据。

## 构建与验证

- 本机0～2件阶段执行过数据检查、50万次抽取、两项内存自动化，结果通过。
- 最终1～3件版本完成Editor/Game构建，未重新执行抽样或游戏测试。此前测试不能算作最终概率版的测试结果。
- 本次只做用户要求的整理、提交范围/差异/依赖/敏感内容检查与补丁应用检查，未启动UE、游戏、联机实测或重新构建。
- 双客户端同时搜索、争抢、掉线重连、主机重启恢复均未实机验收。
- 单人旧档转联机时，若容器还有房主私有内容/领取记录，需房主先打开一次完成原子迁移。已搜索、旧空箱和已取空状态不随概率调整补刷。

技能沉淀：世界交互的 [搜索容器合同](../../../skills/ue5-world-interaction/references/facility-search-containers.md) 与物品资产的 [搜索收集物资产](../../../skills/ue5-item-asset-workflow/references/search-collectible-assets.md)，同步个人维护源；个人存档联机技能也增加对应入口。
