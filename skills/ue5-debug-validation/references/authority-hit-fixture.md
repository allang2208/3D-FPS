# UE 隔离权威命中夹具的边界

只在用户明确要求排查/测试时采用。整理、更新技能和发布 Git 不恢复旧测试授权。

- 每个用例声明 World BeginPlay、真实 NetDriver/socket、客户端进程、角色初始化、实际入口和序列化是否存在。一个 authority World 内的 remote-controller 替身只能证明被调用的权威链。
- 角色创建后未初始化 Actor 分派时，注册的 ForwardHit 可以非空但 UFunction/RPC 包装仍不执行。必要时使用 `World->InitializeActorsForPlay(FURL())` 初始化分派，保持与真正 BeginPlay 的边界；不要改成直接 `_Implementation` 后宣称客户端入口已通过。
- 手动检查复制字段前调用目标 Class 的 `SetUpRuntimeReplicationData()`。否则 RepIndex 尚未分配，GetLifetimeReplicatedProps 可能触发 PushModel bIsPushBased 断言；这是夹具错误，不能报告成游戏复制故障。
- `FVector_NetQuantize` 赋值并不等于传输量化；用 FBitWriter/FBitReader 调用实际 NetSerialize。先编码客户端接触，再推进权威时间、位置和姿态，才能测延迟回执。
- 检查实际注册的转发器、Actor/UFunction 包装、权威公式和生命变化；身体与器官生命分别断言。命中返回 true、显示血效和扣血不能互相替代。
- 夹具崩溃、退出码、完整结果、失败数及保存产物分别记录。共享构建遇到无关未完成源码时保留归因，等文件稳定后继续，不能修改他人的半成品来凑编译成功。
- 静态目录审查不足以覆盖出生失败：使用真实组件构造、实际查询半高、封闭闸门和分阶段拒绝记录；空房点位成功不证明生产刷怪成功。

2026-10-18 怪物夹具覆盖 34 个战斗类，守寝者原型排除；没有实际双端通信、真实时延/丢包、地图 BeginPlay、动态布料或视觉验收。完整历史回执在本机 `SourceAssets/MonsterNetworkHitAudit20261018`，公开摘要见 `Docs/Publication/FacilityMonsterHits20261019`。


## 技能档案夹具必须先合法（2026-10-19）

`ColdSteelSkills::Validate` 要求已存储技能等级至少为 1。为了模拟“未学会”而在整个初始档案中塞入 Level=0，会让 ApplyGuestProfile 拒绝并导致 ShadowModel 为空；随后崩溃不证明游戏的 RPC 或旋风有故障。先建立可接受的一级档案并清空无关快捷绑定；仅在对应拒绝用例中调整技能状态，结束后恢复。一级数值下限可独立通过求值器的 Level=0 输入检查，别混淆数值接口与序列化合同。

逐风检查需区分目录／公式、原生权威直接调用、反射归档回读和真实网络传输。2026-10-19 的最后记录为目录 18 项、原生 38 项，0 失败；前三轮为夹具构造／编译问题，保留归档原因，不将其混作已修复的线上玩法问题。
