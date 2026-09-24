# 墙面霉斑与渗水痕调整

用户明确指向深绿发黑的霉斑和下垂水痕。此次调整已有墙面贴花及其运行时保留方式，不改扫描主墙、瓷砖剥落、颗粒法线和视差凹凸。

旧的 `M_LocalDampStreak` 将混凝土粗糙度噪声强拉伸，使用接近黑绿的颜色及最高 0.68 不透明度；旧地图还保存了多个版本的渗水贴花。它们是固定作者锚点，并非原来就有独立的出现概率。

## 生成方式

- 在地牢成功完成装配后，对三个明确的墙面渗水材质入口筛选一次。合格锚点保留概率为 32%，同时设总量上限、180cm 水平近邻排斥，减少旧层叠加。原作者已隐藏的贴花继续隐藏。
- 使用地牢种子加锚点位置的独立随机流，不消耗路线随机数。失败的装配不修改旧场景；同一世界再次生成时可重新选择此前被本规则隐藏的锚点。
- 保留已有作者位置和朝向，只在原投影范围内随机切换四种水痕、左右镜像、宽度、下垂长度和浓度。不新添满墙水渍，不移动模型或碰撞。
- 每张水痕不透明度系数 0.22–0.34，乘以非满幅遮罩后实际更淡；长度系数 0.55–0.95，源头保持在上方。投影半深度最多 8cm，减少影响邻近构件。
- 可用 `fps.Dungeon.WallStainKeepFraction` 调整下一次生成的保留概率，默认 0.32。近邻与总量限制仍适用，32% 不表示每轮强制保留固定数量。

## 材质制作

四种自制水痕打包在一张 1024×1024 RGBA 遮罩内，继续使用 mip 与纹理流送。形状包含不规则湿源、逐渐收窄的断续水道、浅淡吸水边缘和少量斑点。三种旧入口保留路径并更新材质图，避免已保存关卡继续绑定旧版。

颜色改为低饱和灰褐，粗糙度在 0.65–0.8 之间变化；不输出法线，让原墙体的颗粒与凹凸继续透出。贴花没有 Tick，不新增实时噪声循环或额外灯光。

目标入口：

- `/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak`
- `/Game/Dungeons/AtmosphereV2/TilePolish/Materials/M_TileLeak`
- `/Game/Dungeons/AtmosphereV2/NaturalPass/Materials/M_NaturalLeakVertical`

备份位于 `/Game/Dungeons/WallStains20260924/Baseline/`。后续三个旧导入入口都调用 `Tools/AssetPipeline/dungeon_wall_stains.py`，保留本次修改。固定预览地图使用新的淡化材质；32% 的筛选在实际地牢运行生成结束时应用。

## 交付记录

制作源：`SourceAssets/DungeonWallStains20260924/`。必要导入／着色器制作回执为 `Receipts/install.json`，运行规则为 `Source/FPSGAME/Dungeons/AuthoredDungeonWallStains.inl`。

三种材质与遮罩已通过后台 commandlet 导入并保存，最终制作日志为 `Receipts/install-02.log`。`FPSGAMEEditor Win64 Development` 返回成功且目标已是最新，`FPSGAME Win64 Development` 增量构建成功，分别记录在 `Receipts/build-editor-01-console.txt` 和 `Receipts/build-game-01-console.txt`。没有启动交互编辑器。

未启动游戏、PIE、截图或视觉验收，实际外观由用户测试。
