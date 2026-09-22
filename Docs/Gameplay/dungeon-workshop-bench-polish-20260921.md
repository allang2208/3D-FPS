# 工作间桌面、台灯与电线调整 / 2026-09-21

按用户截图移除不合格的发动机，并继续处理木质工作台、台灯和穿桌电线。已导入并保存到 `/Game/GameMaps/L_Dungeon_Prototype`，最终保存时间为 **2026-09-21 22:43:42**。未启动 PIE、截图、渲染或额外测试，视觉效果由用户查看。

## 本轮变更

- 删除 `DGN_Room_WS_RepairMotor` 场景实例，同时从 `DungeonRoomInteriors20260921/Scripts/author_rooms.py` 与 `Authored/room-manifest.json` 的摆放清单中移除该项。原始生成文件保留，不再摆回房间。
- 两张桌面共六块木板保持原轮廓和 93.9 cm 顶面高度，换用项目已有 Wood051 的 2K 颜色、法线与粗糙度。每块木板独立偏移纹理，并给正面、长侧面和端面分别映射，纠正原先侧面沿厚度拉伸的问题。
- 桌面增加稀疏细划痕、短端裂、板间轻微色差；UE 材质按维修区域叠加局部油污和前缘接触磨亮，避免整桌均匀脏污。油污破碎细节复用已有 Quixel imperfection 的 R 通道，不将其当作金属度。
- 重建台灯灯罩：1.25 mm 的实际壳体厚度，按曲面法线向内偏移，内外表面分配不同材质，去掉旧版重叠的反光内衬。增加卷边、贯穿通风孔、陶瓷灯座、凹入灯泡、旋钮螺钉、弹簧、开关和橡胶底脚。
- 主电源线直径从旧版 7.6 mm 调整为 **5 mm**，灯臂线为 **3.3 mm**。补上墙插、握持筋、护线套与固定夹。桌上电源线沿后缘布置，最低平放段中心为 94.45 cm，按半径计算底面高于 93.9 cm 桌面；移除原来低至 84 cm 的穿桌控制点。曲线采用分段三次 Bezier 制作。
- 台灯实际光源移到灯罩开口外侧，朝向桌面；亮度由 95 调整为 65，色温 3400 K，扩大光锥以减轻旧版局部过亮。其他工作间灯光未改。
- 保留上一轮 Fab 工具及当前桌面零件的摆放。本轮替换桌面、局部划痕、台灯三组组件，并增加新的电线组件；旧独立电线继续隐藏。

## 交付与重建

制作根目录：`SourceAssets/DungeonWorkshopBenchPolish20260921`。

- 可编辑组件：`Authored/DungeonWorkshopBenchPolish.blend`。
- 完整房间源：`Authored/DungeonRooms_WithBenchPolish.blend`。
- 四个导出网格及结构、材质清单：`Authored/`。
- UE 资产：`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopBenchPolish`。
- 首次修改前地图备份：`Sources/L_Dungeon_Prototype_before_bench_polish.umap`。
- 接入入口：`Scripts/import_and_install.py`，通过项目 `mcp_call_codex.ps1` 执行。整套地牢重建入口已追加此阶段，未运行整套重建。
- UE 材质包含局部使用痕迹层；Blender 保留可编辑几何和基础 PBR，UE 使用层逻辑在 `Scripts/import_assets.py` 中。

接入回执为 `Receipts/asset-import.json`、`Receipts/scene-install.json` 与 `Receipts/bridge-final-install.txt`。发动机删除记录保存在 `Receipts/scene-install-initial.json`。导入、材质创建与关卡保存已完成；这些回执不代表实机视觉验收。
