# 地牢墙面材质正式接入

2026-09-24。用户确认继续后，已将[样板版本](dungeon-wall-material-upgrade-sample-20260924.md)接入正式地牢。后台 commandlet 已编译并保存主墙材质及六个既有实例入口，[保存回执](../../SourceAssets/DungeonWallUpgrade20260924/Receipts/production-install.json)状态为 `production_materials_saved`。

## 接入方式

保留既有材质资产的路径，让使用这些材质的普通房间、通道、BOSS 房和已保存的组件覆盖一起继承新版表面。无需重新生成模型或改写地牢地图。

| 既有入口 | 新版表面 |
| --- | --- |
| `AtmosphereV2/Materials/M_Concrete` | 扫描主墙、浅层视差高度和毫米级颗粒；水平面保留既有混凝土分支 |
| `WallDamage20260923/Materials/MI_FabExposedBed` | `MI_ExposedMortar` |
| `WallDamage20260923/Materials/MI_FabBondingMortar` | `MI_BondingMortar` |
| `WallDamage20260923/Materials/MI_FabBrokenConcrete` | `MI_BrokenConcrete` |
| `AtmosphereV2/WallRelief/Materials/MI_WallMortar_Bed` | `MI_ExposedMortar` |
| `AtmosphereV2/WallRelief/Materials/MI_WallMortar_Finish` | `MI_BondingMortar` |
| `HazardPolish20260922/Materials/MI_FracturedConcrete` | `MI_BrokenConcrete` |

表内旧入口均位于 `/Game/Dungeons/`，新版实例位于 `/Game/Dungeons/WallUpgrade20260924/Materials/`。

主墙入口是 Material，发布程序追加新版节点并连接材质输出，不删除正在被模型引用的旧节点。使用新版实例的实际参数与纹理生成发布签名，重复导入不会继续追加相同节点。其他六个入口保留 Material Instance 身份，清除旧参数覆盖后继承新版实例，避免同名旧参数盖过新版外观。

## 后续导入

公共接入模块：[dungeon_wall_release.py](../../Tools/AssetPipeline/dungeon_wall_release.py)。发布配置：[production-release.json](../../SourceAssets/DungeonWallUpgrade20260924/Config/production-release.json)。

已接入主墙恢复、剥落层恢复、Fab 破损材质制作、旧版 WallRelief 导入和 HazardPolish 截面导入流程。后续重建这些资产时，保留正式版本的材质继承关系；房间结构导入原有的主墙恢复调用也会进入该模块。

比较地图的 A/C 分组及旧材质板共 14 个材质槽，已改为显式使用 `WallUpgrade20260924/Baseline/*_BeforeUpgrade` 并保存，避免正式入口升级后旧版对照也一起变化。样板制作脚本同样优先使用该历史副本。

## 保留与范围

发布前原材质包及比较地图备份位于 `SourceAssets/DungeonWallUpgrade20260924/BeforeProduction/Content/`。每份材质包的摘要及保存进度记录在发布回执内。备份应在资产没有被编辑器加载时恢复，不应直接覆盖正在使用的包。

本次只修改材质及独立比较地图的材质覆盖，不调整房间模型、碰撞、门框拼接、寻路、地牢布局、灯光和正式地图。细节纹理仍使用流送，保留已制作的距离衰减与有限步数 POM。具体纹理来源与参数见样板记录。

接入时现有编辑器已关闭，使用后台 commandlet 完成，没有主动重开交互编辑器。最终执行记录为 [production-build-03.log](../../SourceAssets/DungeonWallUpgrade20260924/Receipts/production-build-03.log)。

本次正式主墙编译统计为 468 条像素指令，与样板一致。Commandlet 返回 0；同一进程启动时另记录既有血迹材质 `M_FleshStainV3` 的编译警告，该资产不在此次墙面修改范围内。这里的完成结论只涵盖本次墙面材质的构建与保存。

仅执行制作所需的着色器构建、导入与保存；未运行 PIE、截图、性能测试或游戏验收，实际外观与运行体验由用户自行测试。
