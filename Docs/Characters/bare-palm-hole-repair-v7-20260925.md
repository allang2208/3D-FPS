# V7 共享手模掌面漏空修补（2026-09-25）

用户在符文剑检视中指出右手手模建模漏空导致穿模，并要求按弓 ContactV9 的同一局部拓扑法修补共同 V7，同时修复棕色与黑色野外手套。

## 方法

按弓手型与弦接触的表面修补：开口与翻折是网格问题，不是抖动。在规范空间处理母版，再回放到各原生 Authored profile，避免在已蒙皮姿态空间独立补洞把袖口扩进修补范围。

- 焊接 |x|>40 的手部重合顶点，不焊接材质边界全局。
- 只收集材质 2 的开边与法线翻折面，邻域生长后只替换外轮廓跨度 <=2 cm 的连通分量。
- 从边界中心扇形补面；保留逐角 UV、法线；新增中心点权重由边界插值并归一。
- 不写双面材质遮盖开口。腕口开放边保留。

结果与弓 ContactV9 一致：4 处局部（左/右各 2），90 旧面 -> 54 新面。母版顶点数 18646。

## 作者源与接入

- 母版：SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json
- 未修补备份：M4_original.before_holes.json
- 修补记录：surface_repair.json
- 20 个 Authored profile 已回放同一面操作。
- 手套 FittedFieldGlovesV1 已按修补后裸手重生成；ue_field_gloves 与 ue_field_gloves_black 共享网格。
- 已导入全部 V7 裸臂、回烤各 native_bare 视模（含 AzureRunesword_Manny）以及 SK_RuneSword_Arms；两款手套配置已指向修补后网格。弓 ContactV9 仍是独立派生，未改共享母版以外的弓专用表面。

脚本：Tools/ModularOutfit/repair_bare_palm_holes_v7.py、author_fitted_field_gloves.py。

未运行游戏或自动测试；游戏观感由用户确认。
