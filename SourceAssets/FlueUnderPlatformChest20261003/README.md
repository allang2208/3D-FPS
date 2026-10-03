# 烟气净化站平台下宝箱

在模块 `AbandonedFlueGasStation` 的二层平台下增加一个地牢探险宝箱，位置与碰撞尺寸见 `Config/chest.json`。`Scripts/extend_catalog.py` 按专属 identity 替换本条目，保留其他箱柜/宝箱及房体。

共用 `/Game/Props/GamedevTreasureChest20260922` 正式骨架、网格和动画；其几何已由 `GamedevTreasureChestDetail20261003` 在原对象上升级。正式运行采用生成器原生宝箱入口；保留线路测试图的碰撞承载仍引用本地 `BP_StationUpperTreasure`，不代表要求发布第三方素材或整个车站场景。该预览蓝图与本地 Content 同属恢复依赖。

实际地图保存结果留在本地 `Receipts/install.json`。未生成怪物或进行开盖测试；后续由用户测试。
