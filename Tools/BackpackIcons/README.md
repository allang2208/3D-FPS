# 背包栏统一正面图

正式出图复用运行时 `ColdSteelEquipmentIcon` 图标棚。规范：外袋／包盖所在外侧为正面，展示源正面 −Y、顶部 +Z；正交平视、图标旋转 `(0, -90, 0)`、完整轮廓约占限制轴 91%、透明背景。

## 本批制作

在工程根目录执行：

```powershell
# 当前七款；后台导出并发布正式 PNG
Tools/BackpackIcons/run.ps1

# 只重出开拓者的正式图
Tools/BackpackIcons/run.ps1 -Definitions ue_pathfinder_backpack
```

入口自动使用现有 UE 批次互斥。只启动制作所需 commandlet，不打开交互编辑器或运行游戏。PNG 写入目录 `ue_icon` 和固定回退 `Icons/<id>.png`。

本批清单位于 `SourceAssets/BackpackIcons20261025/FrontR1/plan.json`；源图、原文件备份、构建结果和发布回执也保存在该目录。`Sources` 是制作中间图，`Catalog` 是最终图。

## 新增或替换展示源

1. 在清单登记物品 ID、实际静态网格、占格、PNG 路径及正面识别点。源已满足方向规范时使用 `[0, 0, 0]`。
2. 源朝向错误时使用新的独立展示资产路径，在 `source_rotation` 填写所需刚性旋转，在 `display_asset` 填写目标对象路径。不要为了图标旋转穿戴件。`save_display.py` 只用于首次创建本批的独立资产，已有资产不得重复执行覆盖；新修订使用新清单与路径。
3. 完成 UE 保存后，通过 `publish_display.py` 的配置事务写入精确的 `inventory_static_mesh` 叶子，再执行正式出图。显示源选择为物品 `ue_equipment_icon_mesh` → `inventory_static_mesh` → `world_static_mesh`。
4. 修改显示源后同步更新清单再导出；不得把旧 Blender 斜角 `source_icon.png` 复制回正式目录。

底层命令支持 `-Definition=ID` 或带引号的 `-Definitions="ID1,ID2"`、`-OutputDirectory=路径`。批量列表保留引号，避免 UE 参数解析在逗号处截断。未指定物品的底层默认列表不代表七款全覆盖。

文件发布不主动刷新已运行编辑器的模型、实时图标或 PNG 缓存。由用户在下次重启后查看；本制作入口不包含游戏或联机测试。
