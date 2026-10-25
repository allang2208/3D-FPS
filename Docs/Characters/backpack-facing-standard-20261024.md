# 背包方向统一标准与当前差异

> 2026-10-25：七款正式正面图已另批完成，见 [七款背包栏正面图落盘记录](backpack-icons-front-20261025.md)。以下保留 2026-10-24 的历史盘点，不代表本次完成后的状态。

2026-10-24，按用户“所有背包统一方向，正面在背包栏显示”的要求制定。正式规范见 [背包统一朝向与背包栏正面展示标准](../../skills/ue5-item-asset-workflow/references/backpack-facing-standard.md)，个人 SKILL 与工程镜像同步维护。

本轮完成现有图片、目录、显示源引用与消费者代码的检查，并将标准落盘；没有批量旋转资产、重出图、编译或启动 UE／游戏。

## 定下的统一结果

外袋／包盖所在的外侧为正面，背负垫所在的贴身面为背面。背包栏统一正交平视正面，顶部朝上，不额外斜视或俯视。展示源正面 −Y、顶部 +Z；当前 UE 图标棚使用 Pitch=0、Yaw=−90、Roll=0。完整轮廓居中、限制轴占幅约 91%、透明背景，并保持与物品占格一致的画布比例。

第三人称的原生骨骼、各款包体安装倾角和衣物贴合不由这组图标角度覆盖。正式 PNG 与实时图标使用同一显示源和拍摄流程。

## 五款盘点

| 名称／ID | 当前 PNG | 画布 | 按标准需处理 |
|---|---|---|---|
| 行军背包 `ue_portable_backpack` | 外袋正面可见，仍带侧面角度 | 320×320 | 统一为正面平视，与实时源同批出图 |
| 登山包 `ue_mountain_backpack` | 贴背面及肩带成为主要画面 | 320×320 | 重新识别显示源正面，修正展示朝向并重出图 |
| 重装远征背包 `ue_expedition_backpack` | 外侧正面可见，存在斜角／顶面信息 | 240×320 | 统一正面平视，保留完整侧仓轮廓 |
| 简易斜挎包 `ue_simple_sling_bag` | 翻盖主面可见，采用斜视机位 | 213×320 | 统一正面平视，背带自然置后／置侧 |
| 开拓者战术背包 `ue_pathfinder_backpack` | 本轮实读活动 PNG 仍显示贴背垫及肩带面 | 320×320 | 从实际保存的显示源重新辨认正面，正式图与实时图同步制作 |

五款均为 RGBA，画布比例符合当前占格。目录均没有 `ue_equipment_icon_mesh` 或 `ue_icon_pitch/yaw/roll` 覆盖，因此实时显示源走 `world_static_mesh`、角度走消费者默认值。**本轮只确认了这条路由，没有读取五款 UE 静态网格的实际可见面或运行图标棚；不能据默认角度相同认定实时结果都合规。**

当前显示源：

| 物品 | `world_static_mesh` 包路径（省略同名对象后缀） |
|---|---|
| 行军背包 | `/Game/Characters/PortableBackpackAlice20261019/SM_AliceBackpack` |
| 登山包 | `/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/SM_SovietBackpack_Corrected` |
| 重装远征背包 | `/Game/Characters/ExpeditionBackpack20261022/SM_ExpeditionBackpack` |
| 简易斜挎包 | `/Game/Characters/SimpleSlingBag20261022/SM_SimpleSlingBag` |
| 开拓者战术背包 | `/Game/Characters/PathfinderBackpack20261023/OrientationFitR2_20261024/SM_PathfinderBackpack` |

## 当前制作链的差异来源

- 三款新包的独立 Blender 出图机位不一致：远征 `(1.05,−2.2,0.85)`，斜挎／开拓者 `(0.95,−2.4,0.65)`；都不是统一的正面平视。
- `ColdSteelEquipmentIcon.cpp` 使用正交图标棚和 91% 轮廓取景。独立 PNG 不能仅凭同一模型名认定与它一致。
- `ColdSteelInventoryWidget.cpp` 对支持实时图标的物品固定使用 `Icons/<id>.png` 作为回退；仅更改目录中另一个 `ue_icon` 路径会漏掉该入口。
- 当前 `ColdSteelWeaponIconCatalogCommandlet` 的默认列表仅包含登山包。五款完整出图需逐 ID 指定，不能依赖默认列表。
- 开拓者活动 PNG 与 R2 `Icon/source_icon.png` 本轮散列均为 `2a20cbd54eb7777599332074a54ca03cb3a9f0b632292abafd61afbb7be6f74c`，图像显示贴背面。R2 标签和“源图与活动图相同”不足以证明朝向正确；上一轮保存回执保留为资产接入历史，不作为本次统一正面标准的视觉通过记录。

后续落实顺序：辨认并规范五款真实显示源 → 通过同一图标棚逐款正式出图 → 同步目录及固定命名回退 → 更新生产发布入口，避免旧出图脚本覆盖。保存、当前进程缓存刷新及用户游戏体验分别记录。
