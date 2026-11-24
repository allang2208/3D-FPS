# 边境复合弓与通用弓弦

这批源码对应三弓配件回写、持续拉弓耗体、光柱积累条、极光光束批处理和村庄城垛脚架回归。三弓的正式数据位于 [弓定义](../../../Content/ColdSteelData/bows.json)、[改造目录](../../../Content/ColdSteelData/bow-gunsmith.json)和[武器伤害公式](../../../Content/ColdSteelData/combat-weapon-formulas.json)。

[源码映射](source-map.json)记录各个文件的工程相对路径。光束组件、伤害飘字和回写辅助代码位于根 Source。旧公开基线将拉弓、搭箭和释放集中在 BowWeaponComponent.cpp，正式工程已拆分这些入口。Runtime 保存配套弓模块，可与相同版本宿主按路径比较合并。Integration 中的统一差异应用于映射中的共享文件；其中的 PlayerState 声明、改造提交和库存回写要一起合并。免费配件按玩家实际改动的槽位等待确认，材料消耗仍由库存事务处理。现有存档继续使用原弓弦 ID。

[本地正式工程的检查记录](review.json)列出测试范围、GPU 场景和文件清理凭据。GPU 数据来自 RTX 3080 Ti、1280 × 720 的本机联机测试场景，含全帧开销。[作者脚本](../../../SourceAssets/FrontierCompoundBow20261122)配合正式宿主的授权模型、贴图、音频和 UE 资产使用。Git 提供源码及配方。完整二进制资产和逐文件还原清单由本地制作批次保存。

主机、客机及重连进程同时附加 `-BowSparrowWire -BowFlightWire -FrontierBowWire` 可选择复合弓飞行夹具。具体启动参数见宿主联机工具。
