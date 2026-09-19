# 毒蛆黏液表现（2026-09-15）

用户选定液团为伤害主体，细液滴与轻雾补充尾迹，命中后飞溅并留下短暂湿痕。代码与资源制作说明见工程 `Docs/poison-maggot-liquid-venom-20260915.md`，效果尚未用户测试。

- 湿润半透明外层与浑浊内核配合，使用暗黄绿色、流动法线和轻微形变；保持液体重量感，避免发光球和透明玻璃珠。用两组共享实例网格表现碎滴、雾片，按世界设置固定容量；真实性能仍需按用户授权实测。
- `PoisonMaggotProjectile` 保留权威扫掠、一次命中、中毒和射程。`PoisonMaggotVenomFX` 仅接收视觉事件，不创建范围伤害；视觉随机流不改变散布和中毒概率的随机序列。
- 实体场景表面接湿痕，玩家不可见胶囊只接飞溅。主投射物死亡清理与已发出的短寿命外观尾迹分开，不让表现系统推迟命中或销毁。
- UE5.8 Substrate 中，湿痕的 ShadingModels 输出须经过 `SubstrateConvertToDecal`，确保材质域为贴花。半透明软边需要 SceneDepth 时，不同时开启基于深度的半透明速度输出。
- `Tools/PoisonMaggot/build_venom_liquid.py` 制作独立资源，原创程序化 HLSL 写入 `SourceAssets/PoisonMaggotVenom20260915`；无需改写旧怪物材质或下载新素材。制作与编译不等于视觉验收。
