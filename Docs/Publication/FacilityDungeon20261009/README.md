# 设施地牢源码整理与恢复（2026-10-09）

本次整理覆盖生态/发电区、接待大厅、分流大厅、六主题双配对生成、入口与夜景、光照/异步加载，以及最后的静态设施和门框收口。公开原创源码、作者配方、稀疏布局、恢复说明和技能；不上传完整 UE Content、第三方资源、Blend/FBX、生成贴图、几何采样、缓存或 trash。

## 当前保留内容

| 范围 | 当前入口及边界 |
|---|---|
| 正式生成 | `Source/FPSGAME/Dungeons/AuthoredDungeon*`；原通道工作台/破洞神像 → 侧破洞接待厅 → 分流厅 → 三条双主题路线 → 汇聚/档案区 → Boss。六个主题不重复，主题内三房顺序固定。 |
| 空间求解 | JointRouting 与 LayoutBank；按同一抽签组合回退，120 套有序配对布局保留原生合同/占用检查。作者入口 `DungeonFacilityFlow20261007/extend_catalog.py`。 |
| 生态、发电 | `DungeonEcology20261004/Scripts`、`Production20261005/Scripts`；`DungeonPowerTheme20261004RefineV2` 的文字卡片、二层玻璃总控室及服务器抽拉容器。 |
| 大厅 | `DungeonReceptionHall20261006` 与 `DungeonFacilityTransit20261007`，含精修、二层道具、六套门厅、植物展柜；`HallLighting20261007` 保存最终亮度与故障灯配方。 |
| 第三房宝箱 | `ThemeThirdRoomTreasure20261007/treasure.py` 与 `Config/saved-placements.json`。 |
| 性能 | `AuthoredDungeonGenerator.*`、`AuthoredDungeonLighting.*`；选中路线异步准备、共享实例房间可见性、失败/取消保留旧场景。迁移脚本 `DungeonPerformance20261008/install.py`。无同条件 FPS 对比数据。 |
| 夜景 | `NightStreetCube20261009`，保留近景实体门廊/道路与六面离线 Cubemap。前序 NightStreet/EdgeFix 配方仍在重放链中，不能整体删除。 |
| 门框 | `EntryFrameFit20261009` 完整替换门框组合件，西侧后沿延至 -2479 cm；源母版 `FrontEntry20261008/Authored/FrontEntry.blend` 继续保留。 |
| 关闭设施 | 27 个模板中的 87 处门/井盖/风口是静态布景。用户已撤回本次怪物出入口扩展；不重新引入专用刷怪 Actor、动画或波次，原普通/Boss 遭遇保留。 |

## 本机恢复依赖与顺序

这些相对路径均以项目 `D:/FPS3D/FPSGAME` 为根。

1. 先恢复合法完整 `Content`（含地图的 `__ExternalActors__`/`__ExternalObjects__`）及既有主题材质、房壳、交互、角色、植物和声音。来源边界见 [本次资源说明](../../../ThirdPartyNotices/FACILITY_DUNGEON_20261009.md)。Git 克隆不能替代本机完整资产备份。
2. 恢复本机作者输入：生态 `Revisions/v2..v6` 的配置/manifest/可编辑源，发电 `References` 的合法复用包，各任务 `Sources`、`Authored`、纹理和导出清单。生态 V2 `prepare.py` 仍由当前入口读取；这些母版没有按旧日期判废。
3. `DungeonFacilityFlow20261007/Config/catalog.json`、`Sources/production-catalog.json` 和已保存修订回执留本机。公开 `Config/layout-bank-v1.json` 仅为稀疏摆放数据；只有对应完整目录合同才可使用。不要制造 `map_saved` 回执激活尚未导入的资产。
4. 完整恢复优先使用当前正式地图。需要重建时先恢复各主题作者输入并执行对应准备/建模入口，然后生成大厅/分流、基础设施配方、原入口恢复及后续修订。不要按目录编号盲跑所有历史安装器。旧样板 README 描述当时阶段，正式接入以 `facility-dungeon-flow-20261007.md` 及当前保存目录为准。
5. `SpawnEntries20261009/author.py → recipe.py → install.py` 只维护静态设施。`floor-assets.json` 保存撤回旧切孔引用所需的稀疏映射，`legacy-spawn-pools.json` 只保留本次曾改过的原护士编成类型，已不依赖整份旧采样目录。
6. 最后按需执行 `EntryFrameFit20261009/author.py` 和 `install_background.ps1 -ScriptName 'EntryFrameFit20261009/install.py'`。后台包装器沿用批次互斥；已有编辑器时走现有桥，拒绝 PIE/未保存地图覆盖，不另开编辑器界面。

当前完整目录快照未作为新公共数据提交，旧版其他任务的已跟踪目录镜像也未整份覆盖；恢复时通过作者入口合并本机当前配方。公共源码切片没有在无资产的全新克隆中构建过。

## 归档与保留

本次 1307 份退役几何/通行采样、出怪切孔阶段工具、临时待保存快照及 Blender 自动备份移入 `trash/facility-dungeon-retired-20261009/`，约 959.42 MiB。移动前后逐文件 SHA-256 一致。公开 [归档元数据](archive-manifest.json)，实际内容只留本机。

前次撤回的 `DungeonSpawnEntry` 源码和修改前恢复文件继续保留在 `trash/dungeon-emergence-withdrawn-20261009/`；本次补齐路径/大小等元数据，见 [前次归档索引](withdrawal-archive-manifest.json)。其中 backup 项为恢复备份，不能误报成此次删除的代码。

旧动画与切孔地板共 41 个 UE 包已不被当前正式生成目录引用，但整理时发现带窗口的 FPSGAME 编辑器正在运行，未搬动这些可能已加载的资产。清单见 [保留资产](retained-legacy-packages.json)，状态为待关闭宿主后按资产引用关系另行归档；不声称已全部清走。当前 11 个静态设施网格、活动输入、历史恢复地图和已保存回执保留。

## 技能与发布检查范围

- `ue5-pcg-building`：按真实断面修复门框收口、文字比例/共面问题、静态设施与出怪行为分离、同组合布局回退、实体近景加 Cubemap。
- `ue5-performance-packaging`：异步准备/隐藏/卸载的区别、旧场景资源生命周期、共享 ISM 可见性并集与单视角范围。
- 本次新增内容同步个人技能与工程镜像，保留其他技能并行修改。

按 WORKFLOW 第 8 节检查发布目标、提交范围、暂存差异、大小、敏感内容和来源；只普通推送 `HEAD:main`。未包含货币、武器、角色、联机及其他并行开发改动。发布文件表见 [published-files.json](published-files.json)。

本轮没有启动 UE、运行游戏、渲染或重跑布局测试。之前的门框/静态设施保存、原生编译及布局回归记录分别见对应开发文档，不能算作本次新验收。视觉、通行和运行表现继续由用户测试。
