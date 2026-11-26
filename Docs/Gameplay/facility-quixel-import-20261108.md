# 废弃设施 Quixel 第一批资产

2026-11-08。用户要求查看已导入资源，并延续此前下载、导入授权。五款源文件位于 `D:/FPS3D/VaultCache/FabLibrary`；已分两批通过后台 Python commandlet 完成正式资产导入和保存。第二批追加 Leakage，没有重写之前四款资产。

## 已保存内容

UE 目录：`/Game/Dungeons/FacilityQuixel20261108`。

| 子目录 | 类型 | Fab listing | 导入后的模型尺寸（厘米） |
| --- | --- | --- | --- |
| ConcreteRubble | 静态网格 | 516fe299-d5b7-4cb4-a4b3-0097b4b9c576 | 14.01 × 10.14 × 5.72 |
| RustyPipeJoint | 静态网格 | 2a46daa8-baf6-40a5-98a2-904d57bccf43 | 20.04 × 15.17 × 15.17 |
| WoodenCableReel | 静态网格 | 09bca95b-2b4c-4db3-a08f-56c025e88451 | 68.91 × 80.19 × 80.22 |
| DamagedConcrete | 延迟贴花材质 | 2628087c-19db-4254-93cb-3a9d42d34be8 | 扫描范围 1 × 1 米 |
| Leakage | 延迟贴花材质 | ccfed800-5be1-41a6-a2fd-fa5d2a869390 | 扫描范围 1 × 1 米 |

共 30 个 `.uasset`：3 个静态网格、5 个材质、5 个材质实例、17 张贴图。每个模型的材质槽绑定对应 `MI_` 实例；FBX 导入生成简单碰撞。当前每个模型有一个 LOD，未制作额外 LOD。

源文件为 High 档，下载贴图均为 4K。保留完整原始文件，UE 贴图 `MaxTextureSize` 设置为 2048；颜色使用 sRGB，法线和遮罩使用线性采样和对应压缩类型。三个 FBX 沿用 Fab 默认 DirectX 法线；glTF 贴花法线翻转绿色通道。模型材质使用原有颜色、法线、粗糙度、AO，Metallic 为 0，Specular 参数默认为 0.5；未从颜色生成金属度。源文件中的其他辅助贴图仍保留在制作目录。

破损贴花保留 BaseColor/Opacity、Normal、ORM 和 Height。Substrate 贴花的 Coverage 显式连接原图透明度；Height 作为资产保留，尚未用于几何位移。未把下载包中的展示平面当成真实破损模型导入。

## Leakage 补齐

`Leakage` 的 Quixel ID 为 `skiubhzc`，其缓存目录于 18:14 出现。下载包只有一张 4K BaseColor/Opacity 贴图，已保存 `T_Leakage_BaseOpacity`、`M_Leakage`、`MI_Leakage`。Substrate Coverage 连接透明度，Roughness 默认值 0.5、Metallic 0，沿用 glTF 参数。没有法线源图，Normal 输入保持未连接，没有伪造法线或高度。五款清单现已齐全。

## 制作入口与范围

- 源文件和下载来源：`SourceAssets/FacilityQuixel20261108/Sources/`、`manifest.json`。
- 导入脚本：`SourceAssets/FacilityQuixel20261108/Scripts/import_assets.py`。
- 单独追加 Leakage：后台入口参数 `-ScriptName Scripts/import_leakage.py`；保留其他四款保存回执。
- 后台入口：`SourceAssets/FacilityQuixel20261108/run_background.ps1`；沿用 UE MCP 批次互斥，已有交互编辑器时转现有桥，不另起进程覆盖资产。
- 保存回执：`SourceAssets/FacilityQuixel20261108/Receipts/import.json`。
- 两批 commandlet 均退出码 0，五项保存回执完整，30 个资产已保存。第一批回执另存 `Receipts/import-before-leakage.json`。

本次只导入可复用资源，没有修改地图、随机地牢布局、运行时生成代码或 F6 目录。未启动编辑器窗口、游戏、截图或渲染；材质外观、碰撞体验及游戏性能仍由用户测试。
