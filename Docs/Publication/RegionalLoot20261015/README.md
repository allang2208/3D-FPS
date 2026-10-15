# 货运、发电与医疗／生态收集物：整理发布

2026-10-15。完整本机工程为 `D:/FPS3D/FPSGAME`；发布目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。本轮只做已完成工作的整理、技能沉淀和发布检查，不开始新区域或药水调配系统。

## 已完成的本机内容

- 搬运工 M-10、技术员 M-11 使用安保员骨架、蒙皮和成熟动作，独立衣物与头盔；沉匣当前显示 M-20，内部 `M10Mawcrawler` 身份与路径保留。
- 货运区前两房各 6～8 名工人，第二房另有 3 只伏窥者；第三房二楼 4 只鼓囊，一楼沉匣及 4 只伏窥者。宝箱移至一楼隧道口附近站台，保留领取身份。两组维修双开门战斗后每 20 秒各补 1 名工人，最多存活 8 名门增援；沉匣死亡后停止。指定通风口与舱盖移除。
- 发电区第一房 6～8 名研究员/技术员，第二房同类工人加 4 只悬钟，第三房 2 只悬钟与 1 只涡电匣；首领目标、区域门及共享进度已接入本机。悬钟远端表现时钟改用服务器时间。
- 三件货运工具、三件电气收集物、六件调配材料已完成模型、材质、透明背包图标、目录及拾取接入。万用表和稳定剂默认 1×2。工具是可回收战利品，未增加持用维修功能；药水调配仍未实现。
- 货运 68 个候选容器 ID；发电补齐 10 个既有容器、增加 2 个检修工具箱；医疗 28 个、生态 32 个固定/候选入口及动态床边箱族。候选数不是每局同时出现数。旧两厅 31 个入口保留，整张表为 172 条绑定、26 个池、36 种物品。
- 稳定剂迁移覆盖共享地面物品、单个/范围拾取、共享箱子、主机保存的客机档案及重连合并。保留数量/身份及仓库容量；旧共享容器改键后须提交才返回成功，保留领取状态且不补刷。

## Git 发布范围与共用前置

直接发布本轮可分离的目录、掉落表、维护材料配方投入、回收价格、拾取模型映射、占格迁移、动态床边箱身份、悬钟时钟修订及原创制作脚本。共用文件从 Git 基线构造精确内容，通过独立 blob 暂存；工作区其他任务修改不回退，也不整文件夹带。

当前公开分支仍缺少完整的区域遭遇/共享进度/客机档案缓存前置。为保留本轮成果而不替其他任务发布整套框架：

- [regional-implementations.patch](regional-implementations.patch) 保存货运/发电的五个独立实现文件及悬钟时钟测试。需要同版本 `FacilityHallEncounter`、`DungeonRunSubsystem`、`DungeonSharedProgress`、区域门和调度声明/分派。
- [guest-profile-migration.patch](guest-profile-migration.patch) 保存本轮客机最终合并修复。公开旧版 `ApplyGuestProfile` 是 `void`，本机为带磁盘/缓存恢复的 `bool` 接口，因此不能直接应用到旧函数。
- [integration-baseline.json](integration-baseline.json) 记录 Git 基线、补丁前置与完整本机共用文件散列。完整本机已经应用这些修改，不要再次执行补丁。补丁不是已公开完整框架或干净检出可构建的承诺。
- 共用区域框架的既有交接见 [根冠与生态区域](../RootCrownEcology20261014/README.md)、[联机框架](../Multiplayer20261014/README.md)。按同一源状态整合分派、成员、复制和实现，不只复制新 `.cpp` 文件。

原生产地图与多批次目录 JSON 混有其他场景修改，保留本机。货运变更用 `Tools/FreightEncounter/catalog_patch.py`、`service_doors.py` 重放；发电新增工具箱用 `SourceAssets/PowerCollectibles20261014/Scripts/power_containers.py` 重放，并已接入该区域 `prepare_modules.py`。这些脚本只在明确恢复资产时运行，本次发布没有运行它们。

## 制作源与恢复顺序

| 内容 | 活动输入及入口 |
|---|---|
| 两种岗位衣物 | `Tools/CargoStationStaff`、`SourceAssets/CargoStationStaff20261014/V01`；依赖本机安保员 V13 供体及合法原输入 |
| 货运遭遇、维修门、宝箱位置 | `Tools/FreightEncounter`，`SourceAssets/FreightDoorReinforcements20261014` |
| 三件工具 | `SourceAssets/FreightTools20261014`；UE 使用 `VisualRefine`，预览使用 `Previews/ReviewV2` |
| 工具目录与制作投入 | `SourceAssets/FreightIntegration20261014/integrate_data.py`；Saved 内容器清单是本机恢复输入 |
| 三件电气收集物 | `SourceAssets/PowerCollectibles20261014`；UE 使用 V1 |
| 六件材料 | `SourceAssets/AlchemyMaterials20261015`；基液、赤脉根、银叶花保留根目录源；其余三件使用 `VisualRefineV4` |

材料恢复顺序：根目录纹理与模型作者 → 根目录后台导入及安装 → 目录/掉落接入 → V4 三件精修作者与导入 → `install_icons_and_receipts.py` 合并生产清单及发布图标。V4 保留稳定 V3 网格路径，材质使用 V4；必须恢复两套依赖。根目录 `setup.py` 是启动模板，不要在最终配方之后盲目重跑覆盖作者脚本。

制作脚本公开不等于媒体已经进入 Git。模型、纹理、PNG、原始供体、UE 包、导入宿主、运行日志、历史回执与构建产物按仓库规则保留本机。`Tools/CargoStationStaff/author_variants.py` 仍被园艺师作者读取，已保留。

## 废案归档

本次将 164 份确认退役文件、431,336,748 字节（约 411.35 MiB）移入 `trash/regional-loot-retired-20261015`，没有永久删除。每项原路径、目标、SHA-256、原因和替代物见 [archive-manifest.json](archive-manifest.json)，移动后散列一致。

包括本轮 Before/Backups 快照、Blender 自动备份、被 V4 替换的三件旧模型/导出、货运旧预览和已结束的一次性操作脚本。当前母版、正式 UE 资源、当前图标、活动导入宿主和制作依赖保留；历史记录中的原路径通过归档清单追溯。

## 构建、检查与待测边界

- 修复前的材料专项检查：349 项保存地图/资产检查与 35 项图标/数据检查无失败；共享保存/版本测试通过，掉落池测试因三项旧数量预期失败。
- 本轮已修正这三个预期，并修复三条兼容问题；2026-10-15 Editor 与 Game 构建成功，原始证据位于本机 `Saved/AlchemyFixes20261015`。修复后没有重跑自动化，也没有真实双端测试。
- 发电区历史专项检查与构建见该批 README/本机回执。历史通过项不等于最终全项目或当前 Git 切片已验收。
- 本次仅执行用户授权的归档/发布检查，不启动 UE、游戏、渲染或重新构建。仍待用户体验旧存档迁移、重连、同时搜索/拾取、增援出门与区域闸门等实际联机行为。

技能更新同步个人维护源与工程对应章节：搜索物资产、搜索容器、岗位服装与占格迁移。方法记录不把本次构建写成真实联机验收。
