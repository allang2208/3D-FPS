# 地牢墙面剥落基层与凹凸升级（2026-09-22）

依据 `ue5-pcg-building` 的可复用室内组合件规则，本轮只重建瓷砖墙组里的低位砂浆基层，保留已完成的工作间布景、现有瓷砖铺装、局部缺口、残片、灯光和渗水布局。凹凸制作借鉴 [当前地形材质方法](../WorldGeneration/ground-material-optimization-20260920.md)，按墙面毫米尺度重新制作。

## 改动

原低位砂浆使用较弱的普通法线，缺砖处另叠多段刮齿几何。现在删除这部分低位表面，替换成有连续起伏的砂浆床。细节按粗砂浆、残留粘结层、砂粒、孔隙和短刮痕共同生成，刮痕具有弧度、磨损、深浅与断续变化。

- **几何层**：2.5 cm 间距的平滑网格，低频起伏设计幅度 ±2.2 mm；原有近表面填缝和瓷砖背后的支撑片继续保留。
- **材质层**：1.28 m 的连续贴图尺度；原创 2K 色彩、法线、粗糙度/AO/覆盖打包图与 16-bit 高度源图。高度图在 UE 使用 Half Float，减少浅起伏的量化台阶。
- **高度分层**：粘结层覆盖由不规则覆盖场与基层/粘结层的高度竞争共同决定，颜色和粗糙度使用同一遮罩。没有独立随机染色去伪装深度。
- **近景凹凸**：视差粗步进后细化最后一个交点区间，所有通道使用同一坐标；mip 梯度来自未偏移 UV。擦痕主要改变表面形状和反射，不加浓黑描边。
- **浅填缝**：与大面积裸露基层使用两个实例，砖缝采用十分之一的视差与法线强度。

## 接入与源文件

覆盖入口端墙、南北走廊、工作间、机房、检修壁龛、转折段和末端平台，共 8 个现有墙组 Actor。独立新版网格和材质在 `/Game/Dungeons/AtmosphereV2/WallRelief/`，旧网格保留；地图目标为 `/Game/GameMaps/L_Dungeon_Prototype`。

作者目录为 `SourceAssets/DungeonWallRelief20260922`。`Authored/DungeonWallRelief_Source.blend` 是本批可编辑墙面源；工作间的 `Config/surrounding-sources.json` 追加墙面覆盖源，完整 `DungeonRooms_WithWorkbenchKit.blend` 已重新组装，旧版本在源装配中隐藏保留。

整场景安装脚本最后应用本轮墙面阶段。局部接入只替换墙面 Actor 的网格引用，保留原组件的可见性、碰撞配置和变换。独立网格继续使用 Nanite 与三角面碰撞；材质视差本身不改变碰撞。

## 参数

| 参数 | 默认 | 用途 |
| --- | --- | --- |
| `WallReliefDepthCm` | 基层 0.65，填缝 0.065 | 视差高度范围，0 关闭 |
| `WallNormalStrength` | 基层 1，填缝 0.1 | 与高度尺度相配的法线强度 |
| `WallReliefSteps` | 12 | 近景粗步数上限设置，按角度降低 |
| `WallReliefRefineSteps` | 4 | 最后一个交点区间细化次数 |
| `WallReliefFadeStartCm` / `WallReliefFadeEndCm` | 250 / 650 | 距离渐隐范围 |
| `WallMacroAmount` | 0.035 | 弱化重复的大尺度色彩变化 |

`Config/surface.json` 中的贴图物理尺度同时参与几何 UV 和法线制作。改变尺度应重制源资产，不单改材质的厘米转换参数。

## 交付状态

材质与 8 个网格已在当前 UE 工程导入保存，8 个墙组 Actor 已切换到新网格，`L_Dungeon_Prototype` 保存完成。接入回执为 `SourceAssets/DungeonWallRelief20260922/Receipts/install.json`，状态 `stage=map_saved`。

未运行 PIE、截图、验收渲染、碰撞回归或性能测试，实际观感由用户测试。此处不把资产导入/保存当作视觉或性能通过。
