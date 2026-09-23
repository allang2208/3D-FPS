# 地牢墙面：砂浆基层与高度凹凸

本批为现有地牢瓷砖剥落区域制作连续砂浆基层、分层 PBR 与近景 POM。基于工作间组合件的局部重建规则，以及 2026-09-20 地形材质的同坐标采样和交点细化方法。

- 新 UE 资产：`/Game/Dungeons/AtmosphereV2/WallRelief/`。
- 目标地图：`/Game/GameMaps/L_Dungeon_Prototype`，现有 8 个 `DGN_AV2_*_Tiles` Actor。
- 可编辑墙面源：`Authored/DungeonWallRelief_Source.blend`；完整工作间装配源继续由 `DungeonWorkbenchKit20260921/Scripts/assemble_room_source.py` 生成。
- 配方：`Config/surface.json`；表面生成器：`Scripts/author_surfaces.py`；局部几何：`Scripts/author_walls.py`；视差代码：`Scripts/wall_relief.hlsl`。
- 原始恢复输入：`Sources/scene-inputs.json` 记录墙面 Actor、旧网格及材质槽。旧结构 Blender 与其内嵌贴图仍是制作依赖。
- 生产记录：`Receipts/materials.json`、`Receipts/meshes.json`、`Receipts/install.json`。仅 `install.json` 的 `stage=map_saved` 表示地图接入完成。

真实基层按 2.5 cm 网格制作，叠加连续低频起伏。旧低位砂浆床、硬条状齿纹和低位平面粘结片被替换；现有瓷砖、陶瓷断面、近表面填缝及残片支撑保留。细节由原创 2K BaseColor、Normal、Surface 和 16-bit Height 四张无缝数据图承担。Surface 的 RGB 分别是粗糙度、AO、粘结层覆盖；没有把颜色亮暗当作高度。

高度图在 UE 导入为 Half Float；源法线为 OpenGL，UE 导入翻转绿通道。所有 PBR 通道沿相同的视差交点取样，梯度取未偏移坐标。完整起伏实例与浅填缝实例分开，避免在狭窄砖缝里出现过深视差。材质视差不改变碰撞与轮廓，真实低频起伏来自已导出的网格。

制作：在工程根运行 `py -3.11 SourceAssets/DungeonWallRelief20260922/Scripts/build.py`；加 `--install` 经项目桥执行材质、网格与地图接入。仅需切换已保存资产时，桥执行 `Scripts/install_saved_walls.py`，不再次导入。整场景 `DungeonAtmosphereV2_20260921/Scripts/install_v2.py` 最后自动应用本阶段。

本批不运行 PIE、截图、渲染、性能测试或验收。保存/导入记录不代表已通过画面验收，由用户测试。二进制模型与旧 Blender 恢复输入保留本机，不据此宣称公开仓库包含完整恢复素材。
