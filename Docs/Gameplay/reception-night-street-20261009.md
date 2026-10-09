# 接待大厅门口告示板与夜景 — 2026-10-09

## 已落盘

正式地图：`/Game/GameMaps/L_Dungeon_Randomized`；房间：`FacilityReceptionHall`。
本次后台导入并保存 4 个网格、2 个材质、1 张夜景贴图和正式地图生成器配方。保存回执为 `SourceAssets/DungeonFacilityFlow20261007/NightStreet20261009/install-receipt.json`，状态 `map_saved`。

## 告示板修复

西侧两块落地告示板的文字资产并未丢失。前次旋转后，导出过程对独立的面片重算法线，令 8 个文字三角形朝向 -X（墙壁），背面剔除使字样不可见。本次在派生网格中逐面翻转这 8 个面，保留原有 UV、文字比例和位置，不再对这些未闭合面片猜测外侧方向。文字面与牌体已有 1 cm 间距。

替换 `SM_FrontEntry_Signs` 为本批 `SM_ReceptionNight_Signs`；其他告示牌的版式与贴图不变。

## 门外设计

- 铁栅门维持固定关闭；原门廊顶棚和灯具成为入口雨棚。
- 栅门后制作约 2.1 m 湿沥青路面、分段倒角混凝土路缘、纵横排水格栅。
- 原创夜景图表现冷灰工业街、少量暖色路灯和远处薄雾。远端柔化直接来自原图，不给武器或门栅施加全屏景深模糊。
- 四个背景面覆盖旧门廊后壁、两侧与远端地面。侧面与旧压条留有深度间隔，避免再次共面闪动。
- 一个不受手电直射影响的 Substrate Unlit 材质，在每实例局部空间内将视线投射到虚拟远平面（X = -3800 cm），按 19.8 × 9.9 m 投影范围保持图像 2:1 比例；随机房间旋转和平移时背景跟随实例。
- 图像边缘越界渐暗，避免极端斜视角出现重复贴图。它是关闭栅门后的有限视域布景，不是可进入的完整街区。
- 原门廊点光由 700 lm 调到 100 lm，半径 440 cm 调到 230 cm，偏冷色；大厅其他灯光不变。

## 开销与生成合同

本批网格三角形：{"Signs": 324, "Forecourt": 972, "Drain": 1836, "Background": 8}。Signs 是替换；新增近景与背景合计 2816 个三角形。

夜景原图 1774 × 887，在 UE 导入为 2048 × 1024、BC7、带 mip 且允许流送，整套 mip 纹理数据约 2.67 MiB（仅纹理数据估算，不是整场显存测量）。背景主纹理每像素一次采样，不增加实时 SceneCapture、RenderTarget、Tick 或全场扫描。

新几何均在现有门廊边界内；房间 min/max、cells、ports、路线和预计算布局位置不变。配方视觉资源签名随实际内容更新；layout bank 合同为 `a4af9e7b3d6c515b62fc62e6ba8ec50b24030517`。沿用现有房间可见性和异步资源加载机制。

`extend_catalog.py` 已接入本批保存回执对应的增量配方，后续常规重建会继续应用该修订。

## GitHub 方案来源

参考 [Meta Unreal Rendering Techniques 的 Portals 说明](https://github.com/oculus-samples/Unreal-RenderingTechniques#portals) 中预制背景与视差校正的思路。本次自行实现单张投影图像，不复制其代码或素材，不安装该示例工程。

另参考 [Parallax Materials](https://github.com/osreboot/Parallax-Materials) 的方案方向，但本场景不引入整套插件。原图来源、摘要和散列记录于本批 `provenance.json`。

## 保存与恢复

后台保存日志：`SourceAssets/DungeonFacilityFlow20261007/Receipts/import-20261009-092818.log`。
保存前备份：`D:\FPS3D\FPSGAME\SourceAssets\DungeonFacilityFlow20261007\NightStreet20261009\Backups\20261009-092831`，含地图、外部 Actor/Object 与旧配方。新资产采用本批独立路径，未覆盖共用原始网格和材质。

首次导入发现旧混凝土材质路径不对应现有资产，已改为工程实际共用 `MI_WallConcrete` 后继续保存。之前 PIE 占用时脚本在任何资产写入前停止，用户关闭后才进行正式导入。

按用户规则，本次没有运行游戏、布局回归、视觉验收或帧率测试。背景角度、手电下文字可读性和最终亮度交由用户进入新生成的地牢体验。
