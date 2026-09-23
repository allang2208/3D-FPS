# 地牢差异房间建筑骨架

管线分配间、排水检修室、破损支护室；同一美术语义下的不同轮廓、路线、顶棚和服务结构。只使用原创规则几何及工程现有材料，不采用被否决的 5080 道具。

`Config/rooms.json` 是作者配方；`Scripts/author_rooms.py` 生成各房间的局部坐标 FBX、完整 Blender 装配源与灯光／锚点清单。UE 分批导入后用 `Scripts/install_rooms.py` 替换扩展地图中重复的 B 段。

完成状态读取 `Receipts/import.json`、`Receipts/install.json`。未测试或用户未体验的结果不标为视觉通过。空间说明：`Docs/Gameplay/dungeon-distinct-room-shells-20260922.md`。

## 视觉细化（2026-09-22）

`Scripts/corridor_surfaces.py` 直接读取已认可的 `DungeonTileFracture20260922/Authored/DungeonTileFracture_Source.blend`，按墙段铺设，并裁去门洞范围。保留原始材质槽、图集 UV、厚陶瓷残边、粘结层和砂浆起伏；禁止回退到随机删方砖或三角片。此依赖本身是通道剥落与墙面高度算法的最终烘焙结果，不是新设计的破损风格。后续更新该母版后重新生成即可同步。

`Scripts/room_detail_geometry.py` 负责薄壁圆管、弯头、双法兰／垫片／螺栓、实际顶棚吊架、可拆格栅及承托、分层破墙、嵌入式骨料、变长弯曲带肋钢筋和不规则碎石。房间外轮廓与服务路线继续来自原配置。

重新制作运行 `author_rooms.py`；当前地图的细节更新用 `import_visual_upgrade.py`（也提供四个分房间入口），仅重导入 15 个网格。**不要为了细节更新运行 `install_rooms.py`，它会重建房间实例。** 细节接入状态单独读取 `Receipts/visual-upgrade.json`。`Authored/corridor-surface-reuse.json` 保存母版墙段来源与放置记录。旧作者脚本留在 `Archive/BeforeVisualUpgrade`。

本轮未执行 PIE、运行测试或验收渲染，效果由用户测试。
