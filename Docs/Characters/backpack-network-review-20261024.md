# 背包收尾与联机检查（2026-10-24）

## 范围与已修复问题

当前七款背包，Jason/Kaitlin，容量与装备/外观复制、异步模型生命周期、保存与重连。之前的 98 个贴合/重力组合记录见 `backpack-contact-audit-20261024.md`；该历史组件记录不是本轮 socket 联机证据。

1. **同装备 ID 切换身体时旧骨架配件可能残留。** 装备异步请求键原来没有身体身份；现在包含身体类型和原生身体网格。切换身体前先取消旧装备请求、清除动态和旧网格，阻止旧回调在新骨架上发布；EndPlay 使用同一清理入口。
2. **旧动画曲线元数据可使无界面游戏客户端崩溃。** 实际联机过程中 `UAnimSequenceBase::PostLoad → USkeleton::AccumulateCurveMetaData → UEditorEngine::BeginTransaction` 在无 GEditor 的编辑器链接游戏进程中崩溃。已通过 commandlet 备份并重新保存当前配置的 460 个动画和 2 个身体骨架，以及选中头部依赖的 3 个骨架。没有修改作者动作或关键帧。保存回执为 `AnimationMetadataReview/animation_metadata.json` 和 `HeadMetadataReview/head_metadata.json`，原包保存在各自 `Before/`。
3. **容量与联机夹具落后于新增款式。** 容量夹具补齐远界/特勤，开拓者夹层改为 10×6；边界迁移样例同步。新联机入口按当前目录读取容量，旧开拓者入口转为兼容包装。检查器补上带下划线的斜挎模型路径识别，保留正常重力/异步加载；测试专用空地图固定载体防止坠出网络相关范围。

## 当前落盘与构建（完成于 2026-10-25）

- Editor/Game 两目标构建成功，回执 `SourceAssets/BackpackFit20261024/NetworkReview/Build-Support/build-FPSGAMEEditor.json`、`build-FPSGAME.json`。
- 容量命令 `BackpackCapacityAudit -SyntheticOnly`：111 项通过，0 失败。回执 `SourceAssets/BackpackFit20261024/CapacityReview/capacity_checks.txt`。不读写正式玩家档案。
- 检查专用 `-BackpackWireAudit` 跳过与背包无关的学习技能预热；正常游戏行为不变。人体/装备异步加载和背包重力保持开启。
- 构建期间共享源码 `AncientBreakingSealComponent.cpp` 的复制宏参数名与标准宏要求不一致，已仅改为 `OutLifetimeProps` 以恢复构建；不属于背包逻辑修改。

## 实际联机状态

已按用户要求在开拓者完成后停止。本轮五款、75 个阶段全部通过；远界与特勤未继续执行本轮实际联机，第三观察客机也未运行。总回执为 `SourceAssets/BackpackFit20261024/NetworkReview/final-review.json`。

| 背包 | 实际阶段 | 结果 |
|---|---:|---|
| 简易斜挎包 | 15 | 通过 |
| 行军背包 | 15 | 通过 |
| 登山包 | 15 | 通过 |
| 重装远征背包 | 15 | 通过 |
| 开拓者战术背包 | 15 | 通过 |
| 远界智能远征背包 | 未运行 | 用户要求停止后未继续 |
| 特勤重载远征背包 | 未运行 | 用户要求停止后未继续 |

斜挎完整回执在 `Run_20261024-235328/ue_simple_sling_bag/`；其他四款在 `Run_20261025-000017/<物品 ID>/`。每款含主连接 14 阶段及同档案重连 1 阶段，三份 host/client/rejoin 回执均为通过。主机权威库存容量、复制槽位、各端所选模型/绑定均符合预期，未记录到切换期间残留旧身体背带。记录中的最大包体/背带缝接位置误差为 0.00010 cm。

保留失败尝试，不计为通过：首次空地图启动同步停滞；第二次旧曲线元数据崩溃；第三次测试器漏识别带下划线的斜挎带件。第四次还发现用包中心 Z 位移判断斜挎重力不成立：受背带/躯干支撑时，包中心可略微上移；最终夹具使用实际挂点带长和躯干探针核对支撑。双肩包仍检查明确重力下沉。另已修复测试批次没有等待自身进程退出导致下一款过早触发内存门槛的问题。

已覆盖同机监听主机与客机，每端 60 ms 延迟、3% 丢包；男女身体互换、工装/法袍、背包交换/卸下、快速重配、角色重建、同档案重连。特勤款的晚加入观察客机按用户停止要求未执行。组件检查实际资源、原生骨架绑定、复制槽、服务端容量、CPD 重力下垂和包体/背带缝接变换。

没有覆盖渲染画面、所有跑蹲动画、完整死亡业务、专用服务器或跨机器打包版本；不能将无界面检查表述为以上范围通过。

## 制作现场说明

一次工具写入失败使 `FPSPlayerBodyComponent.h` 暂时变为空文件。已从本轮之前备份和编译对象中的源文件校验和恢复原文件，恢复内容 SHA-256 与对象记录完全一致：`9cca21c2bdc324eedd2b549fe076d27bc7857ba1b5af9112f139fe9c3baba548`。随后仅加入清理方法声明，并成功构建。恢复回执/备份在 `C:/Users/allan/.codex/tmp/backpack-review-recovery-20261024/`。

制作缓存 `SourceAssets/BackpackFit20261024` 当前通过目录联接指向 `E:/CodexAssetCache/FPSGAME/BackpackFit20261024`。UE Content、源码及运行资产仍在 D 盘；联接保留。自动审批拒绝了移除联接并迁回 D 盘的恢复操作，仅返回 blocked by policy，因此保留现场，没有绕过拒绝。此位置是制作/检查缓存依赖，不是游戏运行时加载路径。
