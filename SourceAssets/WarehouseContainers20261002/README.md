# 仓库可搜寻容器

四类容器：加固运输木箱、带盖塑料周转箱、金属运输箱、维护工具柜。工具柜下门和上层抽屉分别搜寻，合计十个静态网格及五套活动部件配置。

正式接入地图 `/Game/GameMaps/L_Dungeon_Randomized` 的 `AbandonedCargoWarehouse` 模块；车站整条线路样板沿用 `/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`。

每间仓库按局种子和房间节点选择 12–17 个搜寻入口：货物区 4–5 箱、货架下层 3–4 箱、空墙维护区 1–2 组工具柜（每组柜门及抽屉各一个入口），以及 2026-10-03 增补的墙边和装卸台备用箱 3–4 个。货物区和货架点位替换原来的货物 Actor，其他布景保留。原样板采用固定布局种子 `20261002`，新增点位采用 `20261003` 批次种子，当前仓库共 12 个搜寻入口。

沿用生活主题的容器交互、聚焦时绿色/黄色轮廓和宝箱面板；打开后保持开启。奖励配置留待后续。

## 制作与接入

- `Scripts/author_containers.py`：Blender 几何、分离活动部件、轴心、碰撞与 FBX 导出。
- `Scripts/prepare_slots.py`：点位、变体和原比例标签图集。
- `Scripts/extend_catalog.py`：目录扩展及样板布局生成。
- `Scripts/build_native.ps1`：后台构建 Editor 和 Game 原生目标。
- `Scripts/import_assets.py`：实际导入、材质与 Nanite 构建并保存。
- `Scripts/install_scenes.py`：保存生产生成器目录和现有车站样板。
- `Scripts/install_background.ps1`：互斥批次执行导入及地图保存；保留运行中的编辑器。

真实制作状态以 `Receipts/native-build.json`、`assets.json`、`install.json` 为准。源 Blender、FBX、纹理、UE 包及备份保留本机。

第一间货运中转房的容器及仓库增补点位，见 [容器增补制作源](../SceneLootExpansion20261003/README.md)，实际两图保存回执在该目录的 `Receipts/install.json`。生产目录扩展、点位作者和重新安装入口均保留增补规则。

未运行游戏、PIE、测试、截图或渲染；由用户试玩。详细记录见 [仓库容器](../../Docs/Gameplay/dungeon-warehouse-containers-20261003.md)。
