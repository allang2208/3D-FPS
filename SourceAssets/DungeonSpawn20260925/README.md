# DungeonSpawn20260925 — 地牢战斗房刷怪配置批次

把冻结的每房 `spawn` 段（主题 / 数量区间 / 锚点角色 / 加权怪物池）注入
`module_catalog_json` 中 9 个战斗房模块（Distribution、Drainage、Drainage_NearBridge、
Drainage_FarBridge、ShoredBreach、VentilationLoop、VentilationLoop_WestCore、
VentilationLoop_EastCore、FreightTransfer）。怪物 class 路径逐一核对过
`Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp:22-30` 的注册表。

## 文件

- `Config/spawn-groups.json` — 唯一数据源。每个键对应一个战斗房模块 id，值为逐字注入的
  `spawn` 段（含 `"source": "DungeonSpawn20260925"` 幂等标记）。
- `Scripts/extend_catalog.py` — 纯离线函数模块（FinalReward 模式）：
  - `extend(catalog)`：deepcopy 后按 `catalog['room_ids']` **整段替换**各模块的 `spawn`
    字段；`room_ids` 出现没有对应 spawn 组的 id（或模块缺失）时抛错；spawn 组多于
    `room_ids` 时也抛错。重复执行幂等。
  - `asset_paths(catalog)`：生成器，按模块稳定顺序去重 yield 所有 pool 条目的 class 路径。
  - `__main__`：离线候选生成（见下）。
- `Scripts/install.py` — headless UE Python 安装器（镜像 DungeonRoomVariants20260924 骨架）。
- `Sources/catalog-before.json` — 安装时生成的 Actor 原 catalog 备份（首次安装才写）。
- `Receipts/catalog-extended-candidate.json` — 离线候选（只写本批次目录）。
- `Receipts/install.json` — 安装回执。

## 运行顺序

1. 正常路径：随 DungeonRouteRepairs20260922 主脚本的钩子链执行。其
   `Scripts/extend_catalog.py` 末尾已追加本批次的 receipt 门控 runpy 钩子（位于
   DungeonRoomVariants20260924 钩子之后，保证注入发生在变体房 anchors 重建之后）：
   仅当本批次 `Receipts/install.json` 存在且 `stage == 'map_saved'` 时激活。
   RouteRepairs 的 `install.py` 也已把模块 `spawn.pool[*].class` 并入 module_assets
   收集（与 boss_encounter 同款的 catalog 驱动模式）。
2. 首次安装 / 单独执行：在编辑器条件下 headless 运行本批次 `Scripts/install.py`
   （UE Python：`UnrealEditor-Cmd.exe <project> -run=pythonscript
   -script=".../DungeonSpawn20260925/Scripts/install.py"`，或由主会话在合并点执行）。
   安装器：校验项目与目标地图 → 拒绝 PIE / 脏包 → 读 `l_dungeon_randomized` 中唯一
   `AAuthoredDungeonGenerator` 的**实时** `module_catalog_json` → 备份 →
   runpy `extend` → 写回 `module_catalog_json` 与
   `module_assets = 现有实时列表 ∪ asset_paths()`（去重；`*_C` 蓝图类走
   `load_class`，`/Script/FPSGAME.FatZombie` 等 native 类同样走
   `load_class`（2026-09-26 主会话加固；其余资产走 `load_asset`）→ 仅保存名字含 `l_dungeon_randomized` 的脏包（OFPA 外部 Actor 包），
   不调用 `save_current_level` → 把最终 catalog 镜像回磁盘
   `SourceAssets/DungeonRoutes20260922/Config/catalog.json` → 写回执。

## 离线候选生成（无 UE、无构建）

```
python SourceAssets/DungeonSpawn20260925/Scripts/extend_catalog.py
```

读取 `../../DungeonRoutes20260922/Config/catalog.json`（相对脚本自身定位），extend 后把
候选写到**本批次**的 `Receipts/catalog-extended-candidate.json` 并打印统计
（注入模块数 / asset_paths 数 / room_ids 数）。绝不写 DungeonRoutes 的 catalog.json
或其他批次文件。

## Receipt 契约

`Receipts/install.json`：

```json
{
  "stage": "map_saved",
  "map": "/Game/GameMaps/L_Dungeon_Randomized",
  "room_ids": [...],
  "spawn_modules": 9,
  "spawn_assets": 6,
  "saved_actor_packages": [...],
  "root_map_modified": false,
  "tests_run": false
}
```

RouteRepairs 钩子只认 `stage == 'map_saved'`。未安装（无回执）时钩子静默跳过，
主链行为不变。

## 注入的 spawn 段 schema（冻结）

```json
"spawn": {
  "source": "DungeonSpawn20260925",
  "theme": "<wet|industrial>",
  "count": [最小, 最大],
  "anchor_roles": ["encounter"],
  "pool": [ {"id": "...", "class": "...", "weight": 整数} ]
}
```

`anchor_roles` 的 `"encounter"` 按**前缀**匹配锚点 role：磁盘 catalog 中 9 房全部存在
`encounter` 前缀锚点（Distribution/Drainage/ShoredBreach/两个 Drainage 变体为精确
`encounter`；VentilationLoop 及其两个变体为 `encounter_west`/`encounter_east`；
FreightTransfer 为 `encounter_lower`/`encounter_dock`）。RoomVariants 重建变体房
anchors 时沿用 `main-rooms.json` 的同名 role，前缀匹配不受影响。
