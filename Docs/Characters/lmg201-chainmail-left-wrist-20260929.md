# 201 锁子甲左腕缺漏与穿插（2026-09-29）

当前 LMG201 profile 使用独立 ADS34 衣袖，不能直接改回 PKM 家族：ADS34 已修复右侧肩部上臂的躯干权重拉伸。其左袖保持旧版，尚未包含通用 InsetBinding 家族的内收包边。

本次从当前磁盘资源导出 ADS34 衣袖、201 原生视模与实际使用的露指手套皮肤伴随网格。左腕附近的衣袖与可见皮肤权重并不一致。本次修改左侧远端衣袖 7,599 个顶点，在同侧前臂／腕部皮肤三角面上做重心插值，并在近端 7 cm 内平滑过渡；不使用另一侧、手指或枪身作为权重来源。同时只将左侧旧外凸深色卷边移到新版内收轮廓。

保留右袖全部位置和权重，包括 ADS34 右肩修复；保留原生骨架、衣袖拓扑、UV、材质、内衬及共享摆动遮罩。不改枪械、握点、动作或其他武器衣袖。原版资源不覆盖，新资产为 /Game/Characters/ModularOutfit20260924/LMG201Wrist20260929/SK_LMG201_Chainmail_Wrist。

作者与保存记录位于 SourceAssets/LMG201Wrist20260929：collect.py、author.py、edits.json、production.json、install.py、published.json，以及可编辑交换格式 FBX。配置仅更新 ue_chainmail_shirt.rig_meshes.LMG201；下一次进入游戏加载。

后台完成资产构建和保存，未运行修改后的游戏或全动作测试；实际左腕弯曲、换弹和瞄准接触由用户测试。
