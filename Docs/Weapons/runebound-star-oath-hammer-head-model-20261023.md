# 符文战锤 · 星誓封界锤头模型

2026-10-23 按用户选定的“星誓·封界之砧”设计制作传说专属外锤头。本阶段是高精度模型与 PBR 资产制作，未切换现有游戏引用，也未实现新被动。

制作和交付位于 `SourceAssets/RuneboundWarhammer20261022/StarOathHammerHeadV1/`，详细入口见该目录 README 和 `production_receipt.json`。可编辑制作源与 PBR 装配源分别保存，配套实际 FBX、GLB、4K BaseColor/Normal/ORM 和完整作者脚本。

两侧安装面沿用本锤原装网格截面，保留原装接口带与 UV；原中央锤座、锤颈、长柄、握持与配重作为不改写的宿主参考。新锤头包含连续承力芯、层叠八棱甲片、六处切面核心、176 枚凹刻符印及金属嵌线、压爪、沉头紧固、拱形能量槽与轴向细刻。微表面以实际物理尺度制作，不使用无目的平面细分增加面数。

表面、细嵌线、光学核心、能量分别分区。能量材质保留蓝色基线及独立的亮度/色彩入口，供后续连接符文苏醒与破坏魔力符文的红色表现；目前这些仍是模型内的材质参数。

本阶段完成范围：实际模型、可编辑源、UV、PBR 烘焙与静态导出。后续已完成 UE 资源保存、Game/Editor 必要构建与改造被动接入，详见 `runebound-star-oath-integration-20261023.md` 及 `SourceAssets/RuneboundWarhammer20261022/StarOathIntegrationV1/delivery_receipt.json`。未进行游戏测试或验收渲染。
