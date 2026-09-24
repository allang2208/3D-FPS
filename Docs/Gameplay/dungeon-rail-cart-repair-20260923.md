# 通道、装配间栏杆及液压拖车建模修订

## 本次问题与修改

通道对应 `SM_V2_EndStairRails`。旧扶手斜段由 `(y=7.95,z=1.0)` 连至 `(9.9,2.0)`，但立柱顶点独立写成 `(8,1)`、`(8.9,1.5)`、`(9.8,2)`，没有与该斜段重合。立柱轴线也位于踏步边缘外侧。

装配间对应 `FreightTransfer`。旧楼梯栏杆位于 `Dock` 网格内，平台栏杆位于 `Frames` 内，楼梯扶手端点外伸 15 cm 后仍使用原立柱高度，且平台端点与楼梯侧边错开。由此出现露头、脱节和互相交叉。

两处改用 `SourceAssets/DungeonRailCart20260923/Scripts/rail_geometry.py`：

- 扶手随楼梯和平台形成连续圆滑路径；装配间每段楼梯直接连接相邻平台护栏。
- 立柱根据扶手实际管面构造贴合切口，顶部收在扶手下方。
- 通道立柱内收至踏步范围内，底座随实际踏步高度落地。
- 增加中间横杆、回弯收口、底板及锚栓，延续原有旧化金属材质。

装配间手动液压拖车使用 `pallet_jack.py` 重建，保留左侧货运区的位置和原有尺寸级别。新增折弯叉架、前端双承载轮、独立后轮及轮毂轴承、转向支架、液压泵和活塞杆、密封环、回位弹簧、操纵柄铰接、橡胶握套、释放杆、拉线和紧固件。原有木托盘及货架保留。

## 已落盘内容

通过 Blender 后台执行 `SourceAssets/DungeonRailCart20260923/Scripts/rebuild.py`，更新两份原始 `.blend` 和四份 FBX；原始作者脚本已接入新的几何函数。修订前源文件及已安装资产副本位于该任务的 `Sources` 目录。

使用当前已运行 UE 会话，经项目 MCP 批次互斥执行 `Scripts/import_assets.py`。导入器按现有材质槽保留材质绑定、Nanite 与碰撞设置，已保存以下资产：

- `/Game/Dungeons/AtmosphereV2/Structure/SM_V2_EndStairRails`
- `/Game/Dungeons/VentFreight20260922/Meshes/SM_RS_FreightTransfer_Dock`
- `/Game/Dungeons/VentFreight20260922/Meshes/SM_RS_FreightTransfer_Frames`
- `/Game/Dungeons/VentFreight20260922/Meshes/SM_RS_FreightTransfer_Props`

资产沿用原路径，现有通道和房间引用直接使用新版模型。无需修改地图或地牢路线，也没有本次 C++ 编译依赖。

制作记录：`SourceAssets/DungeonRailCart20260923/Receipts/authoring.json`。
保存记录：`SourceAssets/DungeonRailCart20260923/Receipts/import.json`，状态 `saved`。

本次未启动编辑器或游戏，未进行截图、渲染、碰撞测试或视觉验收。模型已制作、导入并保存，实际游玩效果由用户测试。
