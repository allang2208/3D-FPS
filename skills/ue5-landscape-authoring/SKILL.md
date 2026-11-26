---
name: ue5-landscape-authoring
description: FPSGAME 户外地编构建入口，用于丘陵景观、道路景观、高度图、地表衔接、森林 PCG 分层与林雾。按主题定位制作源、地图组件和恢复版本。
---

# FPSGAME 户外地编

**第一条　文件落盘与引用。** 先从[制作目录与功能索引](../../Docs/Production/README.md)找到本功能，再按[存储分配与文件操作边界](../../WORKFLOW.md#41-存储分配与文件操作边界)确定制作源、正式输出和工作目录。工程资产使用 `/Game/...` 包名，制作脚本相对工程根或已配置的制作源根寻址。交付在同一功能条目登记实际位置与恢复版本。

按[标准地编流程](../_shared/ue5-landscape-authoring/SKILL.md)选择改动范围。整地、接路和材质按[高度场、道路与地表](../_shared/ue5-landscape-authoring/references/terrain-and-surfaces.md)施工。种植、树林装饰、雾气、联机或性能按[生态组合与光照](../_shared/ue5-landscape-authoring/references/ecology-and-atmosphere.md)施工。

## 本工程的入口与依据

- 复用录像中的搭建方法，先查[逐章时间码与原始资料](../../Docs/Production/HillsForestPathStudy.md#按视频定位)。原创高度图、作者测试图和正式地图分别登记在[高度图制作记录](../../Docs/Production/HillsForestPathStudy.md#fpsgame-独立制作的丘陵高度图)。
- 以[双主题操作说明](../../Docs/WorldGeneration/hills-landscape-themes.md)、[主题注册表](../../Tools/WorldGeneration/ForestVillage/landscape_themes.json)和[制作入口](../../Tools/WorldGeneration/ForestVillage/landscape_themes.py)决定写哪个组件。生态层、分页及组合示例见[林地 PCG 分层](../../Docs/WorldGeneration/forest-village-ecology.md)。
- 做出可行走的凹凸，参考[路床残差](../../Docs/Production/HillsForestPathStudy.md#trail-cover-r21)、[自然地表起伏和水坑](../../Docs/Production/HillsForestPathStudy.md#hill-relief-pools-r28)、[村墙及山脚等高线](../../Docs/Production/HillsForestPathStudy.md#village-loess-r32)。露岩与碎石分用[岩壁和岩架](../../Docs/Production/HillsForestPathStudy.md#cliff-exposure-r35)、[坡脚堆积](../../Docs/Production/HillsForestPathStudy.md#cliff-talus-r36)。
- 地表表现按[默认 B full 和全图草皮](../../Docs/Production/HillsForestPathStudy.md#continuous-meadow-r26)、[R27 细叶草替换](../../Docs/Production/HillsForestPathStudy.md#fine-meadow-r27)、[落叶随机边缘](../../Docs/Production/HillsForestPathStudy.md#road-leaf-edges-r34)复用。照明与时段按[林雾实装参数](../../Docs/Production/HillsForestPathStudy.md#forest-mist-r22)。
- 联机与运行成本参照[正式图审查记录](../../Docs/WorldGeneration/forest-village-network-performance.md)。涉及角色档案、采伐或世界时钟时沿用现有权威实现。
- 修复装饰悬空、样板大石缺失或分析用户导出的 F6 文件时，读[参考装饰和 F6 工作流](../_shared/ue5-landscape-authoring/references/ecology-and-atmosphere.md#从参考林地扩展装饰)。本工程的两机位数据、春草 mip 查证与布光取舍见[城镇与城门性能对照](../../Docs/WorldGeneration/forest-village-f6-town-gate.md)。

- 改动村内地基、路肩和林床斑块，见[村内改址与林床点缀](../_shared/ue5-landscape-authoring/references/terrain-and-surfaces.md#村内改址与林床点缀)。按需参考[村庄交付复查](../../Docs/WorldGeneration/village-delivery-review-20261125.md)。

修改扫描泥路的实物尺度和车辙裁剪，见[村外道路的扫描材质](../_shared/ue5-landscape-authoring/references/terrain-and-surfaces.md#村外道路的扫描材质)。迁移 Nanite、流送或核对客机树木与地面，见[迁移林图的渲染和联机预算](../_shared/ue5-landscape-authoring/references/ecology-and-atmosphere.md#迁移林图的渲染和联机预算)。
