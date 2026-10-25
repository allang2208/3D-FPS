# 七款背包栏正面图落盘记录

2026-10-25，按用户要求，将现有七款背包的库存图统一为外侧正面、正交平视、顶部朝上。沿用统一图标棚照明、透明背景和原始模型比例。

2026-10-24 的朝向标准当时只完成规范和差异记录，没有批量重出旧款图像。旧 PNG 来自不同 Blender 机位；此次还从 UE 实际展示源发现行军背包上下颠倒、登山包显示贴背面。

| 物品 | 本次处理 | 正式 PNG 尺寸 |
|---|---|---|
| 行军背包 `ue_portable_backpack` | 独立展示件 Pitch 180°，恢复主袋在上、外袋在下 | 320×320 |
| 登山包 `ue_mountain_backpack` | 独立展示件 Yaw 180°，展示包盖、扣带和外袋面 | 320×320 |
| 重装远征背包 `ue_expedition_backpack` | 统一正交平视，保留中央外袋、侧仓与底仓 | 240×320 |
| 简易斜挎包 `ue_simple_sling_bag` | 统一正交平视，展示翻盖与中央扣具 | 213×320 |
| 开拓者战术背包 `ue_pathfinder_backpack` | 从 R2 真实展示源重出正面，展示外侧 Y 形织带与侧仓 | 320×320 |
| 远界智能远征背包 `ue_farreach_backpack` | 同批正式输出，保留硬壳与中央灯条正面 | 320×320 |
| 特勤重载远征背包 `ue_special_duty_backpack` | 同批正式输出，保留三段硬壳与外扣正面 | 320×320 |

两款独立展示件已保存于 `/Game/Characters/BackpackFit20261024/InventoryFront20261025/`，保留源网格的 UV、材质和结构。通过配置事务写入 `inventory_static_mesh`；原穿戴／拾取网格继续使用各自原引用。图标源优先级为 `ue_equipment_icon_mesh` → `inventory_static_mesh` → `world_static_mesh`。

七款均使用图标棚旋转 `(0, -90, 0)`，正式图与实时图消费同一个网格。PNG 已写入 `Content/ColdSteelData/Icons/<id>.png`；本批七项的目录 `ue_icon` 也均指向这些路径。

统一制作入口为 [Tools/BackpackIcons/run.ps1](../../Tools/BackpackIcons/run.ps1)，支持七款或指定 ID 导出。开拓者、远征背包的旧发布器已停止把斜角 `source_icon.png` 写回正式目录；后续正式发布接此统一入口。新增背包须登记实际显示源与正面识别点。

Editor、Game 后台构建完成；两款展示资产保存、配置引用发布、七张正式 PNG 输出均已完成。制作清单、原文件备份、构建及保存发布回执位于 `SourceAssets/BackpackIcons20261025/FrontR1/`，最终发布记录为 `published.json`。

本轮为图标制作，没有启动游戏或继续联机测试。已运行编辑器保留；其显示源、实时图标及 PNG 缓存由用户下次重启刷新。文件落盘不等于已逐一运行库存、仓库、商店等界面验收。
