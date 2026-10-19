# 灰钢闭面盔制作

用户参考为闭面 armet，采用已生成的 `SourceAssets/SteelArmet20261019/Design/SteelArmet_Concept.png` 作为外观目标。第一版程序化模型被用户明确否定；它未导入、未发布，不是交付母版。

## 当前版本：ReferenceMatchV5

针对用户的第一人称截图，重新对照原设计制作，源文件位于 `SourceAssets/SteelArmet20261019/ReferenceMatchV5/`。上一版 Refined 保留为历史版本。

- Blender 外部头盔：压低过高的盔顶，强化前额、面甲和下颌折面，调整冠片、铆钉、前护颈接缝与可见皮衬。127 个可编辑部件、241852 个三角面；保留原生头部和设计图参考集合。
- 材质：2048 PBR 贴图，局部氧化、磨蚀、细划痕和皮革纹理；没有用新概念图替代实际模型。
- 第一人称：独立内壁实体模型渲染的 3072×1728 透明视野层。眼缝约占画面高度 20%、最大宽度 90%，短直侧壁、磨削内壁和明确倒角替代原来的圆管式眼沿；皮衬延伸到屏幕外，带缝线和固定铆钉。
- 眼缝使用按弧长均匀采样的连续切线曲线，避免近景切边的稀疏顶点和衬垫接点折线。金属沿轮廓平滑，跨内壁/倒角保留折面法线。
- 第一人称仍为烘焙光照视野层，没有实时光照与视差；本轮不改相机 FOV、瞄准射线或 C++ 显示生命周期。
- 共用现有 head_equipment 和装备复制接口，各武器使用同一个头部装备定义。目录图标、备用 PNG、展示网格和掉落模型随本版更新，保留现有装备数值。

制作脚本为 `author_reference_match.py`、`bake_reference_surfaces.py`、`author_reference_visor.py`、`package_reference_blend.py`；接入脚本为 `save_reference_assets.py`、`publish_reference_match.py`。实际保存和发布阶段以本版目录内 `saved_assets.json`、`published.json` 为准；缺少回执不能视为接入完成。

实际模型渲染位于本版 `Renders/`，其中 `SteelArmet_Interior.png` 使用中性背景展示开口；正式 `Textures/T_SteelArmet_Visor.png` 的眼缝透明。本轮未运行游戏或联机测试，用户自行试玩。

## V4 制作记录（历史）

Blender 精细重制源：`Tools/SteelArmet/author_refined.py`。输出隔离在 `SourceAssets/SteelArmet20261019/Refined/`，不复用旧版模型作为正式装备。

- 盔顶采用指定轮廓截面、中央折脊和独立冠部加固片。
- 面甲左右折面、颊片和后颅分件；保留真实厚度、面甲叠边、眼缝和通气孔。
- 铰链座、轴销、铆钉、提柄、短护颈卷边和皮革内衬分别建模。
- 灰钢与皮革使用可重建的微表面高度场，输出 BaseColor、Normal 和 ORM；边缘倒角保留几何。
- 原生 Jason 头部作为隐藏参考收进 `.blend`，装备绑定使用原生 head 骨坐标变换。

## V4 第一人称方案（历史）

外部头盔使用真实静态模型挂接头骨。内沿在 Blender 制作实体厚度与皮衬后，渲染为带透明眼缝的视野层。当前中央开口高度约为画面 40%，最大宽度约 90%。这是屏幕归一化覆盖比例，不是角度或相机 FOV。

选择此方案是为了避免真实相机内壳的近裁切、武器插进盔壁及各武器不同视模缩放的问题。内沿高光为烘焙效果，不宣称实时光照或视差。瞄准投影与射线不修改。

显示层位于瞄具画面之上、正常 HUD 和背包之下。装备切换先移除旧遮罩；异步加载以请求序号丢弃过时结果；死亡、第三人称、观察其他角色时不显示。只有拥有者加载视野纹理；第三人称和远端玩家复用原有头部装备外观及装备复制路径。没有增加逐帧 JSON 解析或同步加载。

## V4 接入记录（历史）

正式装备 ID 预留 `ue_steel_armet`，头部槽位 `helmet`。保存脚本和目录发布脚本位于 `Tools/SteelArmet/`。发布必须以全部资产实际保存完成为前提，同时提供模型生成的目录 PNG、运行时标准备用 PNG、图标展示网格和世界掉落网格。

当前以最新 `Refined/authored.json`、`saved_assets.json` 和 `published.json` 记录实际阶段；缺少后两者表示尚未导入或发布。编译结果不代表视觉、联机或游戏验收。没有启动编辑器或游戏进行试玩。

精细重制已输出 `reference-profile-v4` 几何和 `physical-uv-refined-steel-v4` 表面，四个实际 Blender 渲染在 `Refined/Renders/`。`package_blend.py` 将可编辑部件按用途分组，保留隐藏的原生头部参考。

后台 Editor 构建回执 `helmet-build-02-FPSGAMEEditor.txt` 为 Succeeded。首次接入遇到之后启动的现有编辑器 PIE，`refined-import-02.txt` 在任何写入之前返回 Preserve current play session。用户随后授权停止 PIE 并继续保存；执行停止入口时试玩已结束，沿现有编辑器保存成功，回执为 `refined-import-03.txt`。

`saved_assets.json` 已记录装备、掉落、图标展示网格、五种材质、PBR 贴图和两种 UI 纹理，正式资产位于 `/Game/Characters/ModularOutfit20260924/SteelArmet20261019/Refined/`。`published.json` 记录 `ue_steel_armet` 已写入 items 与 head_equipment，目录 PNG 和标准备用 PNG 同步保存。没有发布被否定的第一版模型，没有主动启动编辑器或试玩，没有进行游戏或联机测试。
