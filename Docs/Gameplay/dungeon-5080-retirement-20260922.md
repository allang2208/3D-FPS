# 地牢 5080 生成物品整批废案（2026-09-22）

用户明确判定：本次地牢构建中通过 5080 管线生成的物品全部不合格、不可用。本记录覆盖已接入和未接入候选；不将任何一件保留为可直接复用的合格资产。

## 废案清单

| 来源批次 | ID | 物品 |
| --- | --- | --- |
| DungeonProps20260920 | goddess_statue | 女神像 |
| 同上 | demon_statue | 恶魔像 |
| 同上 | supply_pile | 冒险者遗物／补给堆 |
| 同上 | bone_pile | 骨堆 |
| 同上 | broken_crate | 破损木箱 |
| DungeonAtmosphereV2_20260921 | broken_concrete_jamb | 破损混凝土墙端 |
| 同上 | maintenance_cabinet_cluster | 维修电柜组合 |
| 同上 | collapsed_tile_rubble | 混凝土与碎砖堆 |
| 同上 | weathered_pipe_assembly | 阀门管道组合 |
| DungeonRoomInteriors20260921 | buried_masonry_bank | 埋藏砌体土坡 |
| 同上 | repair_motor | 维修电机，此前已从生成清单退役，本次一并归档 |

共 11 类。当前地图中仍引用这些模型的 15 个实例已经移除，包括隐藏的旧装饰。原本精确建模的墙体、瓦片剥落、管线、灯具、工作台与已有 Fab 土坡不属于本次否决范围。

## 实际归档位置

`D:/FPS3D/FPSGAME/trash/dungeon-5080-rejected-20260922`

- `SourceAssets/...`：原始 GLB、细化后的 FBX/Blender、贴图、三视图和该候选的生成回执。
- `Content/...`：被否决的 UE 网格、材质及贴图包；同时归档仍引用旧女神像的 V1 历史地图及其外部 Actor/Object 包。
- `configuration-before/...`：修改前的生成任务清单、摆放配置与相关装配清单。
- `moved-sources.json`、`moved-mixed_sources.json`、`content-archive.json`：原路径、归档路径、大小和 SHA-256。
- `retirement-plan.json`、`completion.json`：本轮范围及归档完成记录。

加载中的 UE 资源不能直接通过文件系统移动，实际采用“先完整复制并核对归档散列，再由编辑器资产 API 移除原包”的可恢复迁移方式。所有已归档内容保留，不永久销毁源模型。

包含生成物品的 11 份整场景源／备份也先归档原版；其中 10 个当前 `.blend` 重新保存为去除生成对象的版本，保留手工与已接入 Fab 布景。移除了对象及其失去引用的网格和贴图，清理记录位于 `SourceAssets/DungeonMaintenance20260922/Receipts/source-pruning`。

## 防止旧候选再次装回

- 三批生成清单的活动 `props` 已清空，并标记整批否决；原始参数保留在 trash。
- V2 生成物品布局、房间生成物品清单及已退役对象的移动/隐藏配置已更新。
- 当前装配不再导入或摆放旧女神像，不重新创建被归档的 V1 快照。
- 房间、土坡和完整工作间的源装配继续使用去除废案后的版本。
- 历史女神像导入和砌体重新提交入口明确停止；普通完整场景重建在最后接入新的手工维修柜。

这次否决也包括原本不规则的碎料与土坡，所以“5080 优先考虑粗糙天然主体”只是未来候选的制作分流，不能用来声称本批粗糙物品已合格。未经用户重新选择，不从 trash 恢复这些候选。

## 本轮深化：维修配电区

新增精确建模的 `SM_MaintenanceCabinet`，分别接入维修凹室和机电区。柜体约 1.14 m 宽、1.90 m 高，使用薄板箱体与回折边；左门开启 23°，具有门封、内加强筋、四段铰链及独立把手。内部包含三层 DIN 导轨、15 个断路器、接线槽、铜排、紧固件、电缆格兰头和弯曲导线；右门包含百叶、机械表盘、刻度、指针、铭牌和低亮度指示灯。

材质区分烤漆、内板、裸钢、胶木、电缆、铜、陶瓷及铭牌文字。沿用项目原创的微表面纹理，利用实际边缘距离和顶点色控制局部露底、底部积灰及粗糙度变化。大面板加入内部采样顶点，避免边角磨损插值到整块面板。未采用新的图生模型，也没有给装饰电柜添加未经请求的互动玩法。

- 作者与接入：`SourceAssets/DungeonMaintenance20260922/Scripts/author_cabinet.py`、`import_cabinet.py`、`install.py`。
- 可编辑模型：`SourceAssets/DungeonMaintenance20260922/Authored/MaintenanceCabinet_Source.blend`。
- UE：`/Game/Dungeons/AtmosphereV2/Maintenance`。
- 地图：`/Game/GameMaps/L_Dungeon_Prototype`。
- 完整房间源：`SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonRooms_WithWorkbenchKit.blend`。

已完成必要建模、导入、资产和地图保存。未进行游戏测试、碰撞验收、截图或渲染验收；最终观感与使用效果由用户测试。本轮未提交或推送 Git，二进制交付位于本机工程。
