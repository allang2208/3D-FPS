# V3 作物种植玩法接入（2026-10-22）

状态：实现已落盘，最终 `FPSGAMEEditor` 和 `FPSGAME` 后台构建成功；文件与接入合同静态检查 15 项通过，隔离自动化 40 项、0 失败。实际界面和游戏体验未测试。未打开 UE 图形界面、PIE 或游戏，未提交或推送 Git。

## 入口与闭环

沿用 B → 其他 → 种植地（2 米 × 2 米），放置后在 2.5 米内目视按 E，打开原背包和工作台栏。种植地沿用 `/Game/Building/PlantingBed20261017/SM_PlantingBed_2m_V2`，没有新增种植地资产。

可选番茄、土豆、胡萝卜、小麦；选择地块后显示种植材料、库存、成熟时间与产出。空地播种、占用拒绝重复种植，成熟后收获。大株占 2×2 个种植锚点，点击副占用格会定位到所属植株。种植锚点间隔 42cm，与建筑的 20cm 体素无关。

未找到独立种子目录。本轮每株消耗现有同名作物 1 个作为种植材料，可在配置中将 `input_item` 改成以后新增的种子定义。材料来源复用普通制作：背包、夹层、无容器标识的主仓库，不读取其他箱子。收获尝试先在库存快照中完整放入产出，放不下则保留原库存和成熟植株。

扣料与新增植株、收获入包与清除植株分别使用原 `UColdSteelStatusModel::CommitState` 一次提交。后端校验操作时的植株 GUID，拒绝过期或重复意图；前端另有 0.35 秒提交冷却。库存、占格、重复意图与存档事务已经通过隔离自动化，前端冷却和实际游戏操作尚未验收。

## 公共 UI 对齐依据

直接复用 `UColdSteelWorkbenchWidget` 的外壳、`ColdSteelWorkbenchHUD` 的挂载及开合、原交互入口，仅在种植模式替换主体内容。普通制作仍走原分支。

- 制作栏与背包等宽并排，外边距 12px，开合速度 4.0/s；沿用原右抽屉宽度规则（视口 48%，720–1040px）及双栏可用空间夹取。
- 使用公共 `ColdSteelUIStyle`、原 Text/Button/Card/UpdateScale；黑灰玻璃，模糊参数 9/21、1px 边框、10/8/6px 圆角、36px 操作高度。
- 字号沿用 20/16/14/12；中文 Noto Sans SC，纯数字 JetBrains Mono。短标签和按钮横排，主体滚动，标题和提交固定。
- 作物选择复用配方下拉及 `UColdSteelGunRecipeOptionWidget` 行，包括已有选中、悬停和禁用样式。地块通常四列，窄于 480px 时改两列。
- Esc、关闭按钮、输入焦点、动画期间提交门控和其他工作台互斥走原 HUD。目标移除、被替换或距离超过 3.5 米后关闭。

规则来源：`UI-WORKFLOW.md`、`Docs/UI/ui-cold-steel-design-system.md`、原 `ColdSteelWorkbenchWidget.cpp` 与 `ColdSteelWorkbenchHUD.cpp`。本轮未截图或渲染；尺寸和状态的代码复用不代表已完成人眼视觉验收。详细布局规划见 `Docs/UI/planting-workbench-plan-20261022.md`。

## 数据、模型与存档

使用 `Content/ColdSteelData/crop_models_v3.json` 中已导入的 4 作物 × 3 变种 × 3 阶段，共 36 个阶段网格；每个网格保留原先接入的 3 个 LOD。资产路径 `/Game/Props/Crops/V3`。本轮未重新导入或改写作物二进制资产。

植株首次播种时确定变种 A/B/C、朝向、尺寸和根位置，随后保存并跨阶段复用，仅切换同变种阶段网格。根位置依据种植地作者 manifest 的 16 个锚点，米转厘米、按既有导入镜像 Y；大株取所占锚点平均值。原 manifest SHA256 记录在规则文件中。

新增植株数组进入原 `FColdSteelProfile`，与库存共用校验保存；记录 WorldKey、种植地 InstanceId/格子、占格、作物、变种、根位、朝向/尺寸、播种 UTC、时长和产出快照。旧档缺少字段时为空，不改 VBX 字节格式。拆除地块后清除对应植株，不返还材料；同位置重建因 InstanceId 不同不会恢复旧株。

使用现实 UTC 秒，离线继续生长；0–50% 幼苗，50–100% 生长，达到时长后成熟并保留至收获。天气时间跳转不改变成熟时间。资产异步缓存上限 36 个网格，世界每秒更新，阶段或数据变化才重建 ISM 分组，无逐株 Tick；作物不参与碰撞和导航。

支持范围为单人角色档案。本轮未实现多人地块所有权、RPC 或共享种植，多人模式显示不可用并禁止提交，未引入外部联网服务。

## 可配置开发默认值

以下数值为本轮开发默认，**并非用户指定**；集中在 `Content/ColdSteelData/planting_rules.json`。

| 作物 | 种植消耗 | 成熟时间（现实秒） | 产出 | 占格 |
|---|---:|---:|---:|---:|
| 番茄 | 番茄 ×1 | 1800 | 番茄 ×3 | 2×2 |
| 土豆 | 土豆 ×1 | 1200 | 土豆 ×3 | 2×2 |
| 胡萝卜 | 胡萝卜 ×1 | 900 | 胡萝卜 ×3 | 1×1 |
| 小麦 | 麦穗 ×1 | 1200 | 麦穗 ×4 | 2×2 |

同一小麦物品 ID 为 `wheat`，库存显示名沿用现有“麦穗”。尺寸范围 0.9–1.0，朝向 0–360°，无位置抖动；植株总上限 1024。时长、产出、占格在播种时保存快照，后续调整配置不追改旧株。

## 修改文件与交付记录

新增实现：

- `Source/FPSGAME/Building/ColdSteelPlantingTypes.h`、`ColdSteelPlantingSystem.h/.cpp`：档案数据、规则读取、库存事务、阶段和显示。
- `Source/FPSGAME/UI/ColdSteelPlantingWorkbench.cpp`：原工作台种植模式主体。
- `Source/FPSGAME/Building/ColdSteelPlantingAuditCommandlet.h/.cpp`：隔离事务检查入口，已编译和运行。
- `Content/ColdSteelData/planting_rules.json`：四作物规则与作者锚点。
- `Tools/Crops/run_planting_build.ps1`、`run_planting_audit.ps1`、`check_planting_static.py`：后台构建、隔离测试入口和静态合同检查。

共享文件仅追加所需接点，保留已有工作区改动：`ColdSteelInventoryTypes.h`、`ColdSteelStatusModel.h`、`VoxelBuildWorld.h/.cpp`、`ColdSteelWorkbenchWidget.h/.cpp`、`ColdSteelWorkbenchHUD.cpp`、`ColdSteelWorldInteraction.cpp`；`Config/DefaultGame.ini` 增加 V3 Cook 目录；`crop_models_v3.json` 更新玩法消费者元数据。未调整已有作物物品效果或其他工作台配方。

本轮备份与回执位于 `SourceAssets/PlantingGameplay20261022/`：`Baseline/`、`baseline.json`、`implementation-manifest.json`、`delivery-status.json`、`static-validation.json`、两个构建日志及状态、`audit-blocker.json`。清单散列是交付时快照，后续其他任务修改公共文件不会同步更新它。早前 V3 资产导入记录保留在 `SourceAssets/CropsV3_20261022/Receipts/`。

## 已执行与尚未执行

- **最终后台编译实际成功**：`FPSGAMEEditor`，exit 0，2026-10-22 14:59:33 UTC，日志 `build-editor-20261022-225859.log`；`FPSGAME`，exit 0，日志 `build-game-20261022-230011.log`。两者均 `Result: Succeeded`。没有仍在等待的本次构建或测试命令，未终止其他任务进程。
- **静态检查实际执行**：15 项通过、0 失败，检查四作物定义、36 个 V3 磁盘资产路径、16 个锚点及源散列、共享 UI 复用、原制作分支、事务提交接点、有界异步缓存、随机字段生成位置、重复意图保护和 Cook 路径。这不是玩法执行测试。
- **最终隔离自动化实际成功**：用户明确授权后运行 `Tools/Crops/run_planting_audit.ps1`。最终报告 `AuditRun-20261022-225955/planting-audit.json` 为 **40 项、0 失败、进程 exit 0**，2026-10-22 15:01:00 UTC 完成。实际检查材料不足、背包满、重复提交、占格冲突、扣料与收获、注入保存失败回滚、内存序列化及临时磁盘存读档、稳定变种字段、四种作物播种、同位置替换地块和孤株清除。三个阶段均核对实际 ISM 分组、仅一株可见实例及不变的朝向/尺寸/根位置，未进行 GPU 渲染。36 个 V3 阶段网格均从实际项目包加载成功。
- **已修复的测试夹具问题**：第一轮因空世界未登记测试控制器，交互检查拒绝播种并提前退出。已显式登记控制器，增加夹具断言、失败原因和退出清理，随后 33 项全通过。第一轮日志保留在 `AuditRun-20261022-225112`，未将其失败前的断言作为完成验收。最初的审批拒绝已被用户明确授权解除，不再是当前阻碍；历史记录保留在 `audit-blocker.json` 和 `audit-attempts.json`。
- 最终引擎日志汇总为 0 错误、7 警告，来自旧 Paragon 示例地图 Lighting_Background 数据与建模插件的 Python 重名暴露；未改写这些无关资源。最终轮未出现首轮退出清理的 WorldSubsystem ensure。
- 尚未实际运行：其他工作台运行回归、UI 画面/焦点/鼠标交互、Cook/打包和多人。全部测试只使用本轮目录下的临时 User/Saved 和唯一 PlantingAudit 角色槽，不使用正式存档。

