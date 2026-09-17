# Voxel Plugin 安装器登记与地貌改造接入评估（2026-09-16）

用户从 Fab 下载 `Voxel Plugin Installer`（`d3f93b8f-1718-406a-96ac-f96755678f1e`）。本文记录来源、许可、本机真实安装与启用状态，以及把它接到当前 FPSGAME 地貌／建造／导航／存档上的可行范围与前置条件。

**本次交付边界**：只做了只读排查、`FPSGAME.uproject` 的一行插件注册和本文档。没有安装 Voxel Plugin 本体、没有编译、没有启动编辑器或 PIE、没有截图或帧率测试。所有"能做到什么"均来自官方文档与随包源码，不是本工程的运行结果。

## 1. 来源与许可

| 项 | 内容 |
| --- | --- |
| Fab 条目 | <https://www.fab.com/listings/d3f93b8f-1718-406a-96ac-f96755678f1e> — `Voxel Plugin Installer`，CreatedBy `Voxel Plugin` |
| 作者 / 官网 | Voxel Plugin SAS，<https://voxelplugin.com>；文档 <https://docs.voxelplugin.com>；支持走 Discord |
| 描述符 | `.uplugin`：`Version 160`、`VersionName 0ea55d4b2`、`EngineVersion 5.8.0`、`Category Editor`；单模块 `VoxelPluginInstaller`（Type=Editor，LoadingPhase=PostDefault，Win64+Mac） |
| 安装位置 | `E:\Program Files (x86)\UE_5.8\Engine\Plugins\Marketplace\VoxelPlucfe420af57efV8\`（引擎级 Marketplace，仓库之外，不进版本管理） |
| Fab 库条目 | `D:\FPS3D\VaultCache\FabLibrary\Voxel_Plugin_Installer-d3f93b8f\`（只有 manifest，没有独立 data 目录） |
| 随包二进制 | `Binaries\Win64\UnrealEditor-VoxelPluginInstaller.dll`（916 KB）、同名 `.pdb`（约 68 MB）、`UnrealEditor.modules`；另有 Mac dylib 2.6 MB |
| 许可 | 闭源商业授权。官方许可页写明 Voxel Plugin 2 改为官网直销（约 349 USD、永久授权、含 1 年功能更新与 3 年修 bug／引擎升级），**不再通过 Marketplace 出售**；官方安装文档写明安装 2.0 预览需要先在 Marketplace/Fab 拥有 `Voxel Plugin Pro Legacy`。插件与源码都不可再分发。 |

## 1.1 收费情况（2026-09-16 在线核查）

| 项目 | 结论 | 证据 |
| --- | --- | --- |
| Fab 上的 `Voxel Plugin Installer` | **免费（0 元）** | Fab 商品接口 `https://www.fab.com/i/listings/d3f93b8f-…`：`title=Voxel Plugin Installer`、`sellerName=Voxel Plugin`；两个授权档 `Personal` / `Professional` 的 `priceTier.price` 均为 `0.0`（CNY）。注意同一响应里 `isFree` 是 `false`，所以只看这个布尔字段会误判。 |
| 它安装的 Voxel Plugin 2（真正做地形/挖洞的那套） | **收费** | 官网首页套餐与 Paddle 报价接口：产品 `53348` = `Voxel Plugin Pro - 1 year of feature updates`，`gross=349.0`、`net=349.0`、`currency=USD`；套餐名写明 `Voxel Plugin Pro (for budgets <$200k)`，套餐权益含 Voxel Graphs、Discord 支持、团队共享、VP2 预览版；预算超过 20 万美元要走 `Custom License`。官方许可页说明这是**永久授权、非订阅**（1 年功能更新、3 年 bug 修复与引擎升级）。 |
| 免费替代：`Voxel Plugin Free Legacy` | **免费源码 + 免费 5.8 预编译二进制** | GitHub `VoxelPlugin/VoxelPluginFreeLegacy`（`free.voxelplugin.com` 跳到这里）：README 写明 "This code should compile on 5.6, 5.7 and 5.8"，并给出 `VoxelFree-434-…-5.8-Binaries.zip` 的下载地址；`VoxelFree.uplugin` 的 Description 就是 "Create fully volumetric, entirely destructible & infinite worlds"，含 `Voxel` / `VoxelGraph` 运行时模块。**但仓库里没有任何 LICENSE／EULA 文件**，条款要按其官网/EULA 确认；Fab 安装器说明里也写明它**不能**用来安装 Legacy（Free 或 Pro）。 |
| 老客户 | 可能免费 | 官方许可页写明：原有 Unreal Marketplace 与 Gumroad 客户在 VP2 发布时会获赠 VP2 授权（含 1 年更新）。 |

结论：**下载安装器不要钱，真正的地貌功能要么买 VP2（349 USD 永久授权），要么改用 GitHub 上的免费 Legacy 版**。建议先用免费 Legacy 在测试地图验证"能不能挖、能不能炸、和建造/PCG 能不能接上"，确认有价值再决定是否购买 VP2。价格随官方调整，采购前请以官网结账页实际报价为准；本机 CN 地区的正式 Paddle 端点当前没有返回该商品（站点代码里查的是 sandbox 端点），实际可购买性也需要在结账页确认。

## 2. 本机现状（证据）

1. **只装了安装器，没有装插件本体。** `Binaries\Win64` 下只有 `VoxelPluginInstaller` 模块，没有 `VoxelPlugin` / `VoxelCore` 这类运行时模块；工程 `Plugins\` 下只有 `AutoFootstep`。
2. **安装器本身不含任何地貌功能。** 随包源码 `Source\VoxelPluginInstaller\Private\` 只有：Slate 面板（`SVoxelPluginWidget` / `SVoxelPluginSectionWidget`）、HTTP 客户端（`api.voxelplugin.com`）、OAuth 跳转（`https://new.voxelplugin.com/oauth`）、下载与解压（`VoxelPluginDownload` / `VoxelInstallerUtilities`）。`VoxelPluginApi.h` 的 `bHasValidLicense` / `HasCompatibleLicense` 决定账号能下哪些版本（无授权账号只能拿 `no source` 版本）。
3. **还没有登录过。** `%LOCALAPPDATA%\UnrealEngine\VoxelPlugin\`（`Token.txt` 所在目录）不存在；今天 21:52 装完插件之后编辑器没有再启动过，`Saved\Logs\FPSGAME.log` 里没有任何 Voxel 记录。
4. **安装位置可选。** `UDeveloperSettings → Plugins > Voxel Installer`：`bInstallInEngine`（默认 **false**，即装进当前工程）、`bShowDevVersions`、`bShowUnstableVersions`、`CacheSizeInMB`（默认 1024）。
5. **已注册到工程。** 按 `Docs/Vibe3D-plugin-20260915.md` 的先例，`FPSGAME.uproject` 的 `Plugins` 数组加入：

```json
{ "Name": "VoxelPluginInstaller", "Enabled": true, "MarketplaceURL": "com.epicgames.launcher://ue/marketplace/product/dcb8f76613ce49cda4e70fb602513ce4" }
```

改的是 `.uproject`，**需要重启编辑器**才会加载；重启后工具栏出现 Voxel Plugin 图标（5.6+ 在左侧模式选择旁边）。

## 3. 它提供什么（官方文档口径）

| 能力 | 说明 |
| --- | --- |
| 体素世界 | `Voxel World` 只是管理者，负责统一的渲染与碰撞设置，本身不生成地形；地形由 `Voxel Stamp`（height / volume，数据可来自 heightmap、体素化网格或 graph）决定。没有 stamp 的地方就没有地形。 |
| 程序化地形 | `Voxel Height Graph`（`Output Height` + 噪声等节点、参数可暴露到 Actor 细节面板）生成程序高度，stamp 的半径与高度直接由 Actor 变换控制。 |
| 运行时改地貌 | 两种：spawn **stamp**（便宜，但随玩家移动会重复生成）与 `Height/Volume Sculpt Actor` 上的 **sculpt 函数**（贵、只算一次，适合 Minecraft/Astroneer 这类大量小编辑）。文档明确标为 **experimental**，并且**没有 gameplay 反馈框架**——无法直接知道一次 `Remove Sphere` 实际挖掉了多少地形；也**不做物理模拟**，不会自动让悬空块掉落。 |
| 存档 | `Get Save` / `Load from Save`，数据可直接接进常规存档流程；运行时编辑**不自动复制**（多人要自己写 RPC，中途加入的玩家没有现成同步方案）。 |
| 碰撞与导航 | 地形默认生成 visibility collision；可用 collision / navmesh invoker 在角色附近按需生成，官方建议 navmesh 设为 `Dynamic`，并常给体素 invoker 比原生导航 invoker 稍大的半径。 |
| 材质与生态 | Surface types + metadata、平坦法线／方块化渲染、平滑与 alpha 混合；官方有 PCG 集成路径（`Configuring PCG`、`Using PCG on Voxel Terrains`、`Voxel PCG Graphs`）。 |

## 4. 与我们现有地貌的关系

现状（源码即真源）：`Source/FPSGAME/WorldGeneration/TemperateHillsWorld.*` 与 `TemperateHillsStreaming.cpp` 用 C++ 运行时高度场生成 64 m 分块 `UDynamicMeshComponent`，近处 2 m／远处 8 m 顶点间距、异步碰撞、按距离流送；样地 `L_TemperateHills_Initial` 为 1.024 km，植被由项目 PCG 节点 `TemperateHillsPoints` 驱动。设计文档已经写清这套后端的边界：**高度场无法表达"一个 XY 下多层地面"，首期不含洞穴挖掘与体素破坏**（`Docs/WorldGeneration/pcg-world-design-20260912.md`）。

Voxel Plugin 补的正好是这块缺口：把"能看不能改"的地貌换成可挖、可炸、可加的体素地貌。两边真正相接的面只有四个——**高度采样（建造贴地、PCG 布点）、碰撞、导航、存档**。

| 我们的系统 | 位置 | 与插件的关系 |
| --- | --- | --- |
| 运行时高度场地形 | `WorldGeneration/TemperateHills*` | 可被 Voxel World + height graph 替代；我们现有的种子／世界 ID／`Hfinal` 噪声语义要整体搬进 graph 参数，否则每局世界和植被分布会变。 |
| 20 cm 体素建造 | `Source/FPSGAME/Building/`、`Docs/Building/voxel-build-workflow.md` | 贴地靠射线打真实地形碰撞（每格 5 个地面样本）。体素地形换上来后要保证 invoker 覆盖范围内碰撞已就绪，否则"地基探测不到 → 红格拒放"。承重／倒塌／拆解语义不受插件影响。 |
| 建造放置交互 | `skills/ue5-world-interaction/references/fpsgame-voxel-placement.md` | 吸附、幽灵预览、角色占用判定都不依赖地形后端；只有"地面采样"这一条要重新对着体素地形验一遍。 |
| 导航 | `Config/DefaultEngine.ini`：`RuntimeGeneration=Dynamic` | 已满足插件要求；还要给玩家与三种怪物代理加体素 nav invoker（半径略大于现有 invoker），并保证挖掘后局部导航会重烘焙。 |
| 世界存档 | `FColdSteelProfile`（含 `Generation`）、丘陵独立世界槽 | 运行时编辑的 `Get Save` 数据要进独立世界槽，按 `WorldId` + `Generation` 隔离，不能混进角色档案。 |
| 天气／地表 | `FPSWeatherManager`、`Docs/Weather/*` | 天气只读地表湿度参数；改成体素地形后要重新接 surface type 与湿度参数。 |

## 5. 接入建议（分阶段，先不碰现有地图）

**Stage 0（必须先由用户完成，无法由我代办）**

1. 打开工程 → 工具栏 Voxel Plugin 图标 → `Login`（浏览器 OAuth 登录／注册 → 绑定 Epic 账号 → `Verify`，直到 `Purchase verified` 为绿色）。
2. 图标菜单里下载并安装 Voxel Plugin 2 到**工程**（保持 `bInstallInEngine=false`）。
3. 重启编辑器。如果该账号没有 Pro Legacy / VP2 授权，这一步只会拿到 `no source` 版本或直接没有可下载项——那就需要先在官网购买授权，再继续。
4. 装好后把 `Plugins/` 下新出现的内容、`VoxelPlugin*.uplugin` 版本号和是否要求编译报给我，我再接下一步。

**Stage 1：新测试地图**（不动 `DayNight_Lighting`、`L_TemperateHills_Initial`）

- 新建 `/Game/GameMaps/L_VoxelTerrain_Test`，放 `Voxel World`（变换归零）+ 一个高度 graph stamp，先用最小噪声验证"能看到、能走、有碰撞"。
- 再把我们 `TemperateHillsWorld` 的 `Hfinal`（山脊／丘陵／细节＋道路地基印章）搬进 graph，同一种子下和现有丘陵地图做并排视觉对照。

**Stage 2：玩法接线（这才是"地貌改变"的正题）**

- 爆炸／火球／手雷命中点 spawn 一个 `Remove Sphere` stamp 或调用 sculpt actor 的 remove 函数，做弹坑；近战工具（镐／铲）做挖掘。
- 挖掘产出接现有物品通道（与拆除回收 `GrantDismantledBlocks` 同一条路），并把"挖出多少"由插件看不到量的问题在游戏侧自己记账（按操作体积算，不依赖插件返回值）。

**Stage 3：建造与导航**

- 建造贴地、角色占用、自由放置的采样改成对体素地形碰撞；给玩家与怪物挂 collision / nav invoker，确认挖洞后导航重烘焙。
- 承重求解、20 cm 最小单元、2 m 净跨契约一条都不改。

**Stage 4：存档与生态**

- 运行时编辑数据进独立世界槽（`WorldId` + `Generation`），退出重进复原。
- 植被改由体素表面查询供点（或走插件自带的 Voxel PCG 路径）；地形被挖掉后树木／岩石的悬空规则要重新定。

**Stage 5：才考虑替换温带丘陵后端**，并单独评估渲染质量（Nanite／Lumen／LOD／顶点密度）与流送性能。

## 6. 风险与限制

- **和现有体素建造是两个系统，不能混用语义。** 我们的是 20 cm 建筑体素（承重、倒塌、残骸、经济），插件的是地形体素（stamp／sculpt）。谁负责"挖出来的洞"、谁负责"放上去的墙"，必须在 Stage 1 就定死；同一位置两套体素网格互相穿插会同时产生渲染与碰撞问题。
- 运行时 sculpt 属 experimental；没有"挖掉多少"的反馈 API；不模拟悬空块掉落（我们自己的残骸／倒塌表现要单独做）。
- 运行时编辑不自动复制（单人无所谓，多人要自己写）。
- 引擎版本要对：随包安装器是 `UE_5.8` 槽位，而官方文档当前正文写 2.0p8 面向 UE 5.6/5.7。装完必须核对实际拿到的版本是否声明 5.8；不匹配时要走源码编译（需要仓库编译环境）。
- 插件装进工程会产生 C++ 依赖，需要本地编译；联网账号状态、授权、引擎小版本升级都会影响可用性。
- 许可：商业闭源、禁止再分发。插件本体与源码**不进公开 Git**（`WORKFLOW.md` 第 5 节）。

## 7. 未完成 / 未验证

- 未登录、未下载插件本体、未安装到工程。
- 未编译、未启动编辑器或 PIE、未截图、未做任何性能或画面验收。
- `.uproject` 的注册行只是让安装器在重启后可见，**不代表地貌功能已可用**。
- 上表所有"能做到"来自官方文档，未在本工程验证；不要当成已实现能力。

## 8. 相关技能与文档

- 插件登记先例：[Vibe3D 插件登记](Vibe3D-plugin-20260915.md)（引擎级 Marketplace 插件的来源／许可／兼容／启用写法）。
- 仓库与许可边界：[WORKFLOW.md](../WORKFLOW.md) 第 5 节、[资源恢复](AssetSetup.md)。
- 会被这次改动触碰的技能／文档：体素建造工作流 [`Docs/Building/voxel-build-workflow.md`](Building/voxel-build-workflow.md)、放置交互 [`skills/ue5-world-interaction/references/fpsgame-voxel-placement.md`](../skills/ue5-world-interaction/references/fpsgame-voxel-placement.md)、贴地规则 [`terrain-grounding-20260913.md`](Building/terrain-grounding-20260913.md)、世界生成 [`Docs/WorldGeneration/pcg-world-design-20260912.md`](WorldGeneration/pcg-world-design-20260912.md)。
- 现有 UE5 技能里**没有**引擎插件安装／登记的专门章节；个人技能里只有 Godot 侧先例（`godot-3d-dev` 的 Terrain3D 插件条目）。如果后面确定长期使用这个插件，再考虑补一节。
