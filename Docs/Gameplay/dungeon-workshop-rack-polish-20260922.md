# 工作间货架：线缆、贴条与料箱陈设

2026-09-22 08:58:19 已保存到 `/Game/GameMaps/L_Dungeon_Prototype`。只更新货架陈设 Actor `DGN_Room_WS_RackContents` 和原标签 Actor `DGN_WSDetail_Markings` 的网格引用，保留两者位置、缩放及其余场景。未主动启动 PIE、测试、截图或验收渲染，实际表现由用户查看。

## 本次修改

- 原盘线由四个独立圆环及折线组成，改为一根连续的 11 mm 线缆：椭圆盘绕、逐圈尺寸与中心变化、平滑过渡、两个松弛线头及端部护套。橡胶材质复用工作台电源线的材质家族。
- 原纸箱标签只离箱面约 0.3 mm，旧网格还开启了 Nanite。新纸箱标签、料箱牌和封箱胶带直接分配在箱体相应表面的独立面区，不再叠加近乎共面的贴片。保留原标签图集，胶带改为哑光材质；新陈设和保留标签网格使用原始三角面，不启用 Nanite 简化。
- 五个料箱采用不同内容：8 个密封圈、6 个轴承组件、13 个紧固件、7 个电气件、5 个清洁零件。打散朝向、间距与数量，料箱整体也有小角度偏转；制作阶段用重力落位并烘焙为静态网格，游戏中不运行这些刚体。
- 开口纸箱补充错落的垫片；滤芯前后位置错开。货架框架保持原有结构。

## 后续制作

根目录：`SourceAssets/DungeonWorkshopRackPolish20260922`。

- `Config/layout.json`：固定随机种子、各料箱件数和偏转、线径与盘绕参数。
- `Authored/DungeonWorkshopRackPolish.blend`：保留独立零件的可编辑源；`SOURCE_RackPolish` 收纳制作对象，导出网格单独保存。
- `Authored/manifest.json`：材质来源、固定随机布局与烘焙后的变换。
- `Scripts/build.py`：重新制作、更新完整房间源文件，再通过工程互斥桥导入和保存。
- `Receipts/rack-install1.txt`、`Receipts/install.json`：本次导入和地图保存结果。

UE 新资产目录：`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopRackPolish`。旧网格与源文件保留。

`DungeonWorkbenchKit20260921/Config/surroundings.json` 已记录新的陈设和标签引用；`Config/surrounding-sources.json` 记录 Blender 房间源的对应替换。以后完整地牢恢复和工作台房间源重建会沿用本次货架修订。

修改固定种子后，用项目 Python 执行 `Scripts/build.py` 即可重新生成；`--assets-only` 只制作外部资产。重力落位属于资产制作，不是游戏运行测试。此次未进行视觉或性能验收。
