# 暴风雪 B 版乌云恢复（2026-11-15）

用户查看四套同机位 GIF 后选择 B：ChargedV3，更接近记忆中的原版乌云。此次只恢复释放后的区域乌云，保留当前地面寒气、冰锥碎裂和玩法数值；后台接入，不打开 UE、不主动测试。

## 接入

- `AFPSBlizzardZone::ZoneAssetPaths()[0]` 改为 `/Game/Skills/Blizzard/ChargedV3/NS_BlizzardStormCloud.NS_BlizzardStormCloud`，直接复用本次 B 版 GIF 使用的已保存资产；不重新制作或覆盖 Niagara、材质。
- 玩家施放、远端副本自载和 `PlayerSkillAssets.cpp` 后台预加载继续共用该表，其他资产项不改。近手凝聚云保持现有 RollingV1。
- 地面寒气、降雪、霜面、冰锥心/壳与碎裂入口、室内环境采样和玩法逻辑均保持现有实现。
- 旧版比较录制器的 `RollingV1` 选项改为显式旧版路径，避免正式入口切到 B 后将 B 错标为 D；本轮不执行录制。

选择依据：`SourceAssets/BlizzardVisualReview20261115/VersionComparison/ChargedV3/ChargedV3.gif`。旧版源资产与各候选均保留，不清理或覆盖。

## 交付状态

源码已接入，Game / Editor 常规构建均成功并落盘，回执为 `Saved/BlizzardChargedCloudRestore20261115/delivery.json`。复用现有 B 版资产，本轮没有重新保存或修改 UE 资产。本轮不打开编辑器、运行游戏或追加渲染、测试，观感交由用户确认。
