# M24「玄脊」碳纤维枪托

## 当前游戏资产（2026-11-06）

用户截图指出 DirectFlush 接头仍有折面、凸起且贴图消失。本轮已恢复未形变的 Meshy 主体，在机匣尾缘至碳壳之间局部重建 34.5 mm 曲面：沿真实边界顺序和弧长布面，两端焊接，按相邻表面修正法线与切线。抵肩位置沿用前版 Y=-306.099 mm。贴图丢失原因是前版合并时 UV 层名称不同，碳托图集留在后续通道而材质读取常量 UV0；现已统一主层名称，将原图集恢复到 UV0，继续使用原底色、粗糙度／金属度与法线贴图。原厂和先进枪机两个正式网格及各三档 LOD 已保存至原游戏路径，接入时已读取碳托 UV0 坐标范围，见[保存回执](../../SourceAssets/M24CarbonSmooth20261106/saved.json)和[制作说明](../../SourceAssets/M24CarbonSmooth20261106/README.md)。本轮未运行游戏或生成验收渲染，游戏内观感由用户测试。

DirectFlush 版本因凹形截面按极角排序、原三角形局部拉扯及 UV 合并错误而被本轮替代，其[历史记录](../../SourceAssets/M24CarbonFlush20261106/README.md)保留。此前托身整体前移 55.5 mm，使抵肩面由 Y=-361.599 mm 改至 -306.099 mm。

2026-11-05 的 35.4 mm 放样连接颈已被用户否决，由本轮直接拼接替代。其[历史制作记录](../../SourceAssets/M24StockJunctionR2_20261105/geometry-readback.json)与[历史保存回执](../../SourceAssets/M24StockJunctionR2_20261105/saved.json)留档。下段及“外形与装配”中的旧肩部基准属于首次接入记录。

按用户指定，玄脊现使用 `Meshy_AI_Carbon_Stock_1105135808_texture.glb`。原厂和先进枪机的两个正式静态网格均已在原路径保存，各自保留原机匣、接面、肩部基准与三档 LOD。后托使用该 GLB 自带的 4K 底色、2K 粗糙度／金属度及 4K 法线，法线绿通道已转换为 UE 约定。普通与带框枪匠图标已同步。制作源与原包备份位于 `SourceAssets/M24Meshy1105135808Replacement/`。[安装回执](../../SourceAssets/M24Meshy1105135808Replacement/installed.json)记录两套正式网格、材质绑定及图标。本次未运行游戏。

## 历次设计与接入记录

2026-11-05 Meshy 后续：用户提供 `Meshy_AI_Carbon_Stock_1105124237_generate.glb`，以 A 稿为外观依据进入贴图与渲染阶段。已为该几何制作独立 UV、4K 底色、ORM（R 环境遮蔽、G 粗糙度、B 金属度）及切线空间法线。[内嵌贴图 GLB](../../SourceAssets/M24MeshyCarbonFinish20261105/M24_Xuanji_CarbonStock_PBR.glb) 使用 OpenGL 法线；[UE 单独导入用的法线](../../SourceAssets/M24MeshyCarbonFinish20261105/Textures/T_Xuanji_NormalDX_4K.png) 已翻转绿通道。[棚拍工程与渲染图](../../SourceAssets/M24MeshyCarbonFinish20261105/) 随制作源保留。当前产物是独立外观资产，游戏仍引用旧版，实际装配和游戏内观感待后续处理。

2026-11-05 续作：已恢复外观设计，新增[正侧面候选 A](../../SourceAssets/M24CarbonSpineImagegen20261105/SideConceptR2/M24_Xuanji_Side_A.png)。左端连接颈和右端肩垫同时侧向呈现，长贴腮面下方采用带底的叶形凹面，下缘收成托钩和平底。当前等待选形，选定后再补同一造型的俯视和肩垫后视，交用户用于 Meshy。现有游戏模型仍沿用下述旧版。

2026-11-05：用户否决当前游戏模型的完成质量，要求改走生图设计稿、三视图，再由用户通过 Meshy 生成模型。下文是旧版接入记录，不能视为用户认可的模型母版。旧游戏引用暂时保留，等待新模型接入；本轮没有重新建模或替换游戏网格。

用户指出新概念图的两端透视不一致，后续修图也未形成可用三视图。新造型已暂停。被否决的设计稿、旧展示图和放大织纹版归档于本机 `trash/m24-retired-20261105/SourceAssets/`。现用网格仍需初版 ArtSource 中的形体脚本和织纹输入。

枪匠的 M24 枪托栏使用「玄脊碳纤维枪托」，选项 ID 为 m24_carbon_spine_stock。原厂枪身和先进枪机各有一套配合模型。枪身金属沿用各自的 M24 统一材质，枪托使用初稿的细斜纹、缎光树脂和哑光橡胶。织纹放大 40% 的 R2 仅作设计留档。

## 外形与装配

宽肩垫保留已有后托的抵肩位置。贴腮板的主要接触段沿枪身纵轴找平，前端保留向枪颈收低的过渡。下缘保留浅托钩和平底，贴腮处增加细刻线。碳壳前颈以各自机匣端面为界，顶边中点对中，侧脊在接近端面时跟随壳体收窄。前颈与侧壳之间的短过渡延续主体纹理的 UV。

装配使用现有 M24 安装挂点、独立后握把和普通／扩容弹匣动作配置。两套模型共享肩垫纵向基准，保留各自实际机匣与金属材质绑定。玄脊提供稳定性+45%、后坐力-15%、换弹速度+30%。普通换弹与空仓换弹均按 1.30 倍速度播放。正式网格、材质、贴图和枪匠图标已保存。实机操作和观感由用户验收。

本机装配源为 `SourceAssets/M24CarbonSpineGame20261104/M24_CarbonSpine_Fitted.blend`，同目录保留 `install_receipt.json`。两套正式网格位于 `/Game/Weapons/M24/CarbonSpine20261104/Meshes/`，后缀分别为 `Native` 和 `Advanced`。[源码与资产恢复说明](../Publication/M24_20261105/README.md)

## 设计参考

现实外形参考：Manners MCS-PRS2 的梁式设计和贴腮外形启发了主体轮廓，其 Elite Tactical 系列使用碳纤维外壳。[Manners PRS2](https://mannersstocks.com/mcs-prs2/) · [Manners 壳体说明](https://mannersstocks.com/faq/)。McMillan A-5 的后托钩和贴腮配置启发了下缘收口。[McMillan A-5](https://mcmillanusa.com/shop/browse-mcmillan-rifle-stock-models/tactical-stock-models/a-5/)

以前的设计板、三视图包和俯视图按原相对路径保存在本机归档中。
