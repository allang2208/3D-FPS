# 工作间近景细节与表面材质 / 2026-09-21

按用户提交的四张截图，调整小抽屉柜、墙上工具、洞洞板及标题牌、双联插座，并细化这些组件及桌面工具的表面材质。已于 **2026-09-21 20:16:56** 导入并保存到 `/Game/GameMaps/L_Dungeon_Prototype`，本轮替换 6 个 Actor。

## 针对截图的处理

1. **抽屉柜**：源代码中标签和抽屉正面同处一个平面，本轮将纸面、金属标签框和抽屉面分层放置；标签 UV 按实物比例独立排版。重做薄板抽屉、侧壁、底板、翻边、拉手安装座，收窄抽屉间隙；保留一格略打开的状态。十二格分别标注螺栓、螺母、垫圈、保险丝等收纳内容。
2. **工具**：锻造体与磨亮工作面使用不同材质。锤头改为连续成形轮廓，补通柄眼和固定楔；木柄替换为项目内已有的木纹扫描材质，重新沿柄长映射。钳头、铆钉、包胶握柄分别处理，桌面工具同步使用新金属和握柄材质。
3. **洞洞板与标题牌**：原孔边为八边形、板厚偏大，改为薄钢板的冲孔圆边和内壁；外围边框带倒角。标题牌重新排版，纹理矩形与物理长宽比一致；工具尺码标签也使用独立图集区域。
4. **双联插座**：替换原方盒加低段数圆环，制作圆角外壳、绝缘盖板、凹入插座腔、实际插孔、接地触片、盖板螺钉、进线接头及额定标签。原管道支架保留。

## 材质处理

- 抽屉使用三种轻微差异的漆面，局部磨损集中在翻边、拉手附近；粗糙度和金属度按漆层／露底分别制作。
- 洞洞板采用低对比漆面变化与细尺度漆纹，局部补工具摩擦痕迹，不再沿用原先较显眼的大块斑纹。
- 金属分别制作锻造钢、加工钢的颜色／粗糙度／金属度／法线通道，并复用项目内的 Quixel 金属表面瑕疵图层。该图 **R 为污迹遮罩，G 为粗糙度，B 不是金属度**。
- 握柄与绝缘塑料使用各自的非金属材质。木柄采用原始扫描颜色、粗糙度及 NormalGL 通道，着色器调整色调、粗糙度与法线强度。
- 纸标签重新制作 2048 图集，以物理比例映射；UE 标签颜色纹理使用 BC7 压缩。
- 共新建 14 种材质资源，旧材质保留；没有删除已被场景引用的材质节点图。

## 源文件、来源与接入

制作目录：`SourceAssets/DungeonWorkshopSurface20260921`。

- 组件编辑源：`Authored/DungeonWorkshopSurfaceDetails.blend`。
- 完整场景编辑源：`Authored/DungeonRooms_WithWorkshopSurfaces.blend`。
- 6 组 FBX 和材质清单：`Authored/manifest.json`、`Authored/material-manifest.json`。
- UE 独立资产路径：`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopSurface`。
- 保存回执：`Receipts/asset-import.json` 为 `assets_saved`；`Receipts/scene-install.json` 为 `map_saved`。
- 作者脚本：`Scripts/author_finish.py`、`make_materials.py`、`modeling.py`；接入脚本：`import_finish.py`、`install_finish.py`、`import_and_install.py`。
- 地牢整套重建入口末尾已追加本轮阶段，避免以后重建退回旧细节。本轮没有执行整套重建。

木纹复用 `SourceAssets/AKMIntegration20260910/Redwood/Wood051` 的 ambientCG Wood051；该既有来源记录为 CC0，原始通道复制保存，未改动其他资产。金属瑕疵来自已有 `SourceAssets/ChestZiarat20260909/Source/dirty_metal_rmmodbdp_4k__extracted`；原始元数据保留在原目录。本轮未新增在线下载或重新生成 5080 模型。

用户抽屉截图的辅助文字判读使用工程 DeepSeek 图片通道，问题为“标签和表面材质有哪些明确可见的问题，只列可见问题，不猜测引擎原因”，记录于 `Receipts/user-cabinet-observation.txt`。实际同面关系和图集比例依据模型制作代码确定；辅助文字不作为模型效果验收。

**未启动 PIE、自测、新截图或验收渲染。** 以上为制作、导出及 UE 保存结果，最终视觉效果由用户查看确认。
