# 凉亭穹顶：候选与选定白金星图（2026-09-19）

当前制作只使用C4：`prepare_c4_constellations.py` → Blender `build_roof_previews.py -- C4_WhiteCelestial` → UE `integrate_c4_white_celestial.py`。2026-09-19 发布整理已把首轮A/B/C及C2/C3候选源、导出、预览与回执移入 `trash/building-polish-20260919/SourceAssets/RomanPavilionRoof20260919/`，下文历史文件名均在该归档下。逐文件散列见 [归档清单](../../Docs/AssetArchives/building-polish-20260919.json)。C4当前源、共用脚本、原主体参考与UE `SourceBackup/*_BeforeC2` 是现行重建依赖，继续保留。

## 当前采用：C4 真实星座图形

用户要求不再普遍采用圆圈形式，参考真实星座表复刻。C4 以 d3-celestial 的真实赤经赤纬与连线数据制作十二组：双子、狮子、仙女、英仙、大熊、天鹰、天琴、金牛、天蝎、天鹅、猎户和仙后。

- 沿用源星图的节点与连接关系，保留 W 形、十字、腰带三星、分支和弯尾等图形差别；不随机增删星位，不额外补闭合边。
- 各组使用局部球心投影，北向上、东向左；等比缩放适配分格，再贴合穹顶曲面。组中心仍在同一高度，并位于肋线之间的中央。不同星座的天然宽高比例保留。
- 星形浮雕大小参考恒星星等，同时缩小密集节点避免挤在一起。继续取消孤立散星、上两道金环，保留白色大理石、金色肋线与浑天仪。
- 来源、BSD 许可和适配说明在 `References/README.md`；原始 JSON、许可全文保存在 `References/d3-celestial/`。这是各分格的真实星座图形，不是全穹顶全天星图。
- 作者数据：`prepare_c4_constellations.py` → `C4_constellations.json`；平面参考表：`previews/C4_constellation_reference.svg`。
- 可编辑源：`C4_WhiteCelestial.blend`；模型预览：`previews/C4_WhiteCelestial_hero.png`、`*_roof.png`、`*_finial.png`。
- 已由 `integrate_c4_white_celestial.py` 更新正式整体与穹顶网格；另存 C4 修订模型，C2/C3 历史资产保留。保存回执：`C4_integration.json`。现有两个材质槽、静态几何方式和建筑占格沿用。
- 接入期间编辑器处于 PIE，`EditorAssetLibrary` 的部分操作会将已存在资产误报为缺失。作者脚本改用 `unreal.load_asset` 与直接 GeometryScript 复制到本任务的临时网格，完成指定资源的组装和保存；未停止游戏、未启动额外测试。
- 预览为 Blender 渲染。按项目入口用 DeepSeek 图片通道读取了屋面图案的定性描述，提示为“描述这张穹顶模型预览中正面几个星座的连线轮廓，是否呈现不同的折线与分支；只描述图中看得见的形状，不推断未显示的背面。” 文字记录为 `c4-preview-description.txt`，其星座名称推测不作为图形身份依据；身份与连线来自上述 JSON。
- 未进行游戏测试或性能测试，视觉效果由用户确认。

## 上一版：C3 居中对齐的复杂星座

按用户最新要求调整 C2：

- 去掉上两道横向金环（极角 58.15°、66.15°），保留下沿金环和回纹；原石质穹顶的台阶造型沿用。
- 十二组星座分别位于金色肋线之间的中央，组中心统一极角 45°，上下范围统一为 31°–59°，沿穹顶同一高度排布。
- 删除屋面上所有单独散落的星点。每组 8–10 个星节点，采用不规则闭合轮廓、内部连接及外部分支；各组形状、大小和转角有固定种子的变化。
- 白色大理石、金色肋线、下沿回纹及顶部浑天仪继续沿用。新增装饰仍为静态几何，两个材质槽，没有新增 Tick 或运行时随机计算；短连线按角跨度采样。
- 可编辑源：`C3_WhiteCelestial.blend`；排布记录：`C3_constellations.json`；预览：`previews/C3_WhiteCelestial_hero.png`、`*_roof.png`、`*_finial.png`。
- 接入脚本：`integrate_c3_white_celestial.py`；保存回执：`C3_integration.json`。从 `SourceBackup/*_BeforeC2` 原主体组装，更新正式整体和单独穹顶网格，保留 C2 与 C3 修订资产。最高点与 47 格高度延续 C2。
- 图片为 Blender 模型预览；未进行游戏测试或性能测试，由用户自行体验。

## 上一版：C2 白色大理石与随机星座

用户选中第三款，要求保持白色大理石、取消蓝色、增加星座随机性。已制作并接入 C2：

- 屋面及浑天仪中央球体均为白色石材，保留金色肋线、回纹与浑天仪。
- 每组星座有不同的星数、位置、大小和旋转，采用短分支连线，并在组间散布小星点；不再按每个分格复制同一组四星。
- 固定种子 `20260919`，排布记录在 `C2_constellations.json`，烘入静态模型，无运行时随机、动画或新增 Tick。
- 可编辑源为 `C2_WhiteCelestial.blend`；更新预览为 `previews/C2_WhiteCelestial_hero.png`、`*_roof.png`、`*_finial.png`。这是 Blender 预览，游戏使用项目现有白色大理石材质。
- 已更新正式 `SM_RomanPavilionFull_20` 和 `SM_RomanPavilionDome_20`，原网格保存在 `/Game/Props/RomanPavilionRoof20260919/WhiteCelestial/SourceBackup/`，另保留同目录中的 C2 修订模型。
- 原主体几何、UV、法线和碰撞策略保留；装饰仅增加一个不透明金属材质槽，总计两个槽。石材沿用制作时实际加载的 `M_WhiteMarble_V2`。
- 实体最高点约 9.31 m，整体建造占格从 `(48,48,38)` 更新为 `(48,48,47)`；只给顶部包围盒补齐至 9.4 m，配合既有包围盒居中放置，保持底座落地位置。
- 接入作者脚本为 `integrate_white_celestial.py`；保存回执为 `C2_integration.json`。未修改 C++，为恢复命令行导入环境完成了一次普通 Editor 构建。
- 资产制作已完成；日志包含部分近零切线/副法线警告，未做游戏画面或碰撞测试，由用户体验。不把预览图作为 UE 实机验收。

## 首轮三套候选

用户要求优化圆弧顶的外立面花纹、增加顶部装饰物，先出三套预览供选择。

源模型为当前 UE `SM_RomanPavilionFull_20`（9.6 × 9.6 × 7.6 m），由 `export_reference.py`
只读导出 FBX。十柱、台基、檐口、半球穹顶及原有三圈外侧台阶沿用现有模型。
预览使用 Blender 5.1 Cycles，照明与石材为预览场景表达，**不是游戏内截图**。

| 方案 | 屋面图案 | 顶部装饰 | 风格 |
| --- | --- | --- | --- |
| A 月桂石雕 | 放射石肋、成对月桂浮雕、细金色绞绳边饰 | 石雕松果 | 与现有白色罗马建筑较统一 |
| B 铜穹花冠 | 铜绿鱼鳞纹、金属分格和环线 | 莨苕叶花冠 | 屋面层次更丰富，有金属年代感 |
| C 星纹天球 | 深蓝屋面、八角星、星座连线、回纹 | 浑天仪和极星 | 辨识度较高，偏幻想圣所 |

文件：每套都有同名 `.blend` 可编辑候选；`previews/` 下的 `*_hero.png` 为整体效果，
`*_roof.png` 为屋面近景，`*_finial.png` 为顶饰近景。作者脚本为 `build_roof_previews.py`。

首轮只做了候选建模与预览渲染；后续选定版接入状态以上面的当前版本记录为准。
导出 C2 装饰时降低了曲线截面细分，仍采用静态几何表达；更细密图案后续可按实际视距改为法线/粗糙度遮罩。
未执行游戏测试或性能测试。
