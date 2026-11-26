# 篝火原始需求：已有实现核对（2026-10-18）

本次接续 10 月 10 日“篝火加入其他建筑、附近玩家饥饿和缺水减缓 50%”的委托。当前工程已经实现、注册并保存该功能；不需要重复制作或覆盖。首版见 [2026-10-12 接入记录](campfire-20261012.md)，后续用户授权的添柴、烹饪和火焰调整保留。

本轮只读取相关源码、保存的资产文件和历史回执，新增本记录及 [文件证据](../../SourceAssets/CampfireExistingReview20261018/review.json)。未修改生产源码、UE 资产、用户存档或记忆；未启动编辑器、commandlet、游戏、PIE、构建、截图或渲染；未提交或推送，也未向其他任务发送消息。仓库及上一级的 `.agents/skills` 均不存在；已读取仓库技能入口及其指向的本机维护源。

## 当前行为与首版差异

| 项目 | 当前实现 |
| --- | --- |
| 面板入口 | **B → 其他 → 篝火**，稳定 ID 为 `campfire`，沿用 `DA_VoxelBuildPalette` 与现有构件卡片。中文详情已显示 5 m、饥饿自然消耗 −50%、水分自然消耗 −50%。 |
| 范围 | 篝火底部锚点到角色胶囊底部的三维球形距离不超过 **500 cm**；取暖不要求视线畅通。 |
| 减耗 | 服务器对每名存活、受玩家控制的 Pawn，给饥饿和水分自然消耗各乘一次 **0.5**；多个篝火不叠加。保留天气自然日进度、清泉赐福和 SAN 等原有乘区。 |
| 进入与离开 | 在下一次生存结算重新按当前位置查询；常规间隔 **0.25 秒**，不是离开当帧回调。不增加宽限时间或持久 Buff。 |
| 失效与生命周期 | 燃尽、熄灭、拆除、销毁或脱落后不再提供减耗；死亡不结算自然消耗，重生及读档重新查询当前位置与有效篝火。没有需要从存档撤销的篝火倍率。 |
| 不改变的数值 | 不立即恢复饥饿或水分，不减免已经缺食／缺水时的生存伤害，不改变 SAN 消耗。 |
| 建造与保存 | 原有构件放置、R 旋转、右键拆除、支撑和 Prefab 存档流程。当前普通构件放置路径不扣建造材料；本轮没有另设成本。公共燃料／队列沿用已有建筑保存及篝火事务。 |
| 后续已有扩展 | 首版无需燃料，后续用户已经授权添柴与烹饪。**现在必须燃烧才减耗**：每份木材 60 秒、燃料上限 600 秒，未添柴或燃尽无效果。本轮没有新增或撤销这些玩法。 |

减耗查询使用碰撞场景空间索引，不遍历全世界玩家，不在每个篝火上运行 Actor Tick，也不缓存玩家或叠加状态。火焰表现由已有共享调度管理，最多 8 处、30 m 进入／35 m 保留；表现预算不决定服务器减耗资格。

## 复用资源与实际接入位置

- 炉体与柴薪石圈：`/Game/EasyBuildingSystem/Meshes/Props/Stylized/SM_Stylized_Campfire`。沿用已有模型，没有重复建模。
- 当前火焰：`/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire`；专用火焰／烟材质与历史保存回执的 SHA-256 一致，三个包均在本机存在。没有换回首版火把或已被替换的 Realistic 版本。
- 已有烤架：`/Game/Building/Campfire20261014/RoastingRack/SM_Campfire_RoastSupports`、`SM_Campfire_RoastSpit`；目录组合预览为 `SM_Campfire_WithRack`。
- 范围与清理：[ColdSteelCampfire.h](../../Source/FPSGAME/Building/ColdSteelCampfire.h)、[ColdSteelCampfire.cpp](../../Source/FPSGAME/Building/ColdSteelCampfire.cpp)。
- 权威自然消耗：[FPSSurvivalComponent.cpp](../../Source/FPSGAME/Survival/FPSSurvivalComponent.cpp)，`TickComponent → ConsumptionMultiplierAt`。
- 中文卡片及放置：[VoxelBuildComponent.cpp](../../Source/FPSGAME/Building/VoxelBuildComponent.cpp)。
- 构件生成／删除／加载：[VoxelBuildWorldPrefab.cpp](../../Source/FPSGAME/Building/VoxelBuildWorldPrefab.cpp)、[VoxelBuildPrefabActor.cpp](../../Source/FPSGAME/Building/VoxelBuildPrefabActor.cpp)、[VoxelBuildWorldSave.cpp](../../Source/FPSGAME/Building/VoxelBuildWorldSave.cpp)。
- 共享表现预算：[FluidCampfirePresentation.cpp](../../Source/FPSGAME/WorldGeneration/FluidCampfirePresentation.cpp)。

## 证据与验证边界

1. **历史实际保存**：首版调色板注册回执确认保存成功；[2026-10-14 UE 只读加载](../../SourceAssets/CampfireCompletionReview20261014/asset-readback.json) 确认只有一个篝火条目、中文名、其他分类、原生类、烤架预览及 5×5×4 格。当前调色板文件仍包含篝火 ID、原生类、组合网格和中文名引用；本轮没有重新用 UE 反序列化它，字节引用不等于重新证明唯一性或占格值。
2. **历史构建成功**：[2026-10-15 Editor 日志](../../SourceAssets/CampfireCompletion20261015/20261015-182823/FPSGAMEEditor.log) 和 [Game 日志](../../SourceAssets/CampfireCompletion20261015/20261015-182823/FPSGAME.log) 均为 `Result: Succeeded`。当前两个二进制的修改时间为 10 月 18 日，均包含当前火焰的精确 UTF-16 对象路径；这只确认引用进入二进制，不证明当前全工程源码／二进制完全一致或游戏效果已验收。生产代码未改，因此本轮不重复触发构建。
3. **历史隔离测试**：[2026-10-15 回执](../../SourceAssets/CampfireCompletion20261015/delivery.json) 记录 105 通过、0 失败，包含真实篝火空间查询、两项自然消耗减半和销毁清理。这是当时隔离 commandlet 的结果，不是本轮复测，也不是实机多人或视觉验收。

本次原始需求未发现缺少的制作／接入步骤，没有新增构建或资产保存阻塞。当前整体版本的游戏体验、真实多人减耗与显示、范围边界、重生和存档往返仍交由用户测试。

## 用户自行测试步骤（本轮未执行）

1. 使用已构建版本打开 **B → 其他 → 篝火**，放置、旋转；准备木材，在篝火旁按 E 添柴。确认未点燃不减耗、燃烧后生效。
2. 固定 SAN、清泉赐福及天气速度，在 5 m 内外各停留同样时间。饥饿和水分自然下降量在范围内应各减半，进入范围时数值不跳升。
3. 放置两处范围重叠的燃烧篝火，仍应只减耗 50%；拆除其中一个继续生效，离开全部范围、拆除最后一个或燃尽后恢复原消耗。燃料／原料无法退回时现有事务可能拒绝拆除，需先腾出空间。
4. 由现有合法主机建造入口放置，让两名玩家分别进出范围；再分别重生、退出读档，确认只对当前附近且存活的玩家生效，没有永久倍率。已经饥饿或缺水归零时，伤害规则应保持原样。
