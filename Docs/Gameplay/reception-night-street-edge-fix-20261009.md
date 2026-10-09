# 接待大厅夜景边缘修订 — 2026-10-09

用户截图反馈顶部、底部竖向拖线以及两侧横向拉伸。本批只调整夜景材质，不改铁栅门、告示牌、道路网格或地牢连接。

## 原因与实现

上一版的 UV 越界渐隐发生在照片之外，且保留最多 0.125 UV 宽的可见区。纹理的 Clamp 寻址在此区间反复返回边缘行/列像素，因此建筑和灯光变成横向/竖向长条。

本批材质 `M_NightStreet_BackgroundV2`：

- 使用原始未夹取 UV 计算照片权重，在照片内部的 0.8% 到 8%（横向）／7%（纵向）完成渐隐。任何越界 UV 的照片权重均为零。
- 纹理采样坐标单独限制在半纹素边界内。夹取结果只能出现在原图有效覆盖内，不能作为外侧背景显示。
- 以平滑冷灰天空／暗地面／淡远雾的解析颜色填充外侧，没有重复边缘纹理。
- 投影范围由 19.8 × 9.9 m 调整为 26.4 × 13.2 m，保留 2:1 比例和既有虚拟深度，使贴近门栅时有更多边界余量。
- 在局部高度 2–32 cm 内使远景过渡到暗地面；门廊底面不再被远处照片铺满，近处实体道路继续提供表面层次。
- 沿用每实例局部空间，房间随机旋转平移时方向仍跟随房间。

仍为一张原有可流送贴图、一次图像采样；没有新纹理、网格、实时摄像机、Tick 或动态模糊过程。未采集帧率，不作性能增益结论。

## 接入

正式地图 `/Game/GameMaps/L_Dungeon_Randomized` 的 `FacilityReceptionHall`，仅覆盖 `SM_ReceptionNight_Background` 的材质槽。房间边界、cells、ports 和 layout bank 放置数据未改，视觉合同 SHA 更新为 `4c41274c6181b4c0072583ac92e8c214de87969c`。

实际保存回执：`SourceAssets/DungeonFacilityFlow20261007/NightStreetEdgeFix20261009/install-receipt.json`，阶段 `map_saved`。
后台保存日志：`SourceAssets/DungeonFacilityFlow20261007/Receipts/import-20261009-094104.log`，退出码 0。
旧地图和配方备份：`D:\FPS3D\FPSGAME\SourceAssets\DungeonFacilityFlow20261007\NightStreetEdgeFix20261009\Backups\20261009-094129`。旧材质保留，新材质采用独立资产路径。

原始 `NightStreet20261009/recipe.py` 已接入本批保存回执对应的后置修订，重新导入原始夜景或常规重建目录时继续使用 V2。

本批没有运行游戏、截图、验收渲染或测试；最终近距离和斜视角表现由用户体验。
