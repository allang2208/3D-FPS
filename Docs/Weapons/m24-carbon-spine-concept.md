# M24「玄脊」碳纤维枪托

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
