# 接待大厅完整环绕街景 — 2026-10-09

## 背景结构调整

用户连续反馈矩形背景边缘拉伸、竖线和灰色填充。本批按认可方案改为“实体近景门廊 + 同一三维场景烘焙的完整 Cubemap”，停用有限照片 UV、边界 Clamp 展开和纯色补边。

制作源位于 `SourceAssets/DungeonFacilityFlow20261007/NightStreetCube20261009`。

独立街景场景包含工厂体块、装卸卷帘、细分窗框、路灯、下垂电线、架空管廊、储罐、烟囱、湿路面、路缘、月光、云层与低浓度雾。树木和叶片贴图复用既有生态区 RuralAustralia 资产；来源路径见 `provenance.json` 和 `Sources/Foliage/materials.json`。这批完整街区模型、离线灯光和植被不接入运行时地牢。

六个方向以相同相机位置、90° 视角、2048 × 2048 分辨率、96 samples 在 Cycles 中离线烘焙。PNG 原像素封装为 DDS DX10 RGBA8 sRGB Cubemap，没有裁切拼图、扩图或像素重采样。DDS 顺序 +X/-X/+Y/-Y/+Z/-Z；UE 局部方向到贴图方向为 `(-Y,+Z,-X)`。

## 门口实体衔接

新增有厚度和倒角的混凝土门柱、侧墙转角、底部金属保护带、雨棚檐口、滴水边与排水管。沿用已制作的实体道路、路缘、格栅、告示牌和固定关闭的铁栅门。

网格三角形：{"NearPortico": 7416, "Background": 8}。新的背景网格保持原围合几何，其默认材质直接引用 Cubemap，避免通过旧网格默认槽继续加载矩形照片。近景仅为关闭栅门后的布景，原有门栅和建筑碰撞不变。

## 材质与运行开销

原生 TextureCube 一次采样覆盖任意方向，完全撤掉照片边缘权重和纯色外侧分支。材质使用每实例局部位置，做以地面为底面的有限包围盒视差校正，保持地牢旋转平移时方向一致；近处柱墙使用真实几何遮挡。

运行时不加入烘焙城市、不运行 SceneCapture、不新建 Tick 或定时器。Cubemap 以 BC7 保存，2048 六面完整 mip 数据理论约 32 MiB（仅压缩纹理数据估算，不是整场显存实测）。本方案较原单张照片增加了全方向纹理覆盖，避免新增整套街区的实时灯光、植被与建筑绘制。

全部近景模型保留在原门廊空间内，生成器房间边界、cells、ports、路线与 layout bank 的位置数据保持不变；资源签名随新资产更新。沿用既有房间可见性和异步准备机制。

## 导入与制作链

后台导入入口：`install_background.ps1 -ScriptName 'NightStreetCube20261009/install.py'`。源配方按当前已保存生成器目录增量合并；导入前备份地图、ExternalActors/ExternalObjects 和旧目录。

`NightStreet20261009/recipe.py` → `NightStreetEdgeFix20261009/recipe.py` → 本批配方的后置重放链已接续；只有本批 `install-receipt.json` 为 `map_saved` 才启用。旧照片和旧材质保留用于恢复，正式新版本引用本批资产。

当前制作阶段：六面生产贴图已烘焙，近景 FBX 已导出，4 个正式资产和地图已实际保存。安装回执阶段为 `map_saved`，后台进程退出码 0。

保存日志：`SourceAssets/DungeonFacilityFlow20261007/Receipts/import-20261009-101226.log`。备份目录：`D:\FPS3D\FPSGAME\SourceAssets\DungeonFacilityFlow20261007\NightStreetCube20261009\Backups\20261009-101240`。视觉配方合同 SHA：`fbca7d8fbe7c1d627b1aeb7684c58b8a1df0104e`。

这是资产制作所需的离线贴图烘焙，没有运行游戏、截图验收、帧率测试或生成回归。最终游戏观感由用户体验。
