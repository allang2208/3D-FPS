# 待提交动物掉落

适用于 FPSGAME 丘陵动物：多只动物同帧死亡先合批，下一次 Tick 提交原生肉块。只保存现存拾取物会漏掉尚未提交的队列。

- UWildlifeSubsystem::FlushLoot 返回提交结果，成功才清空 PendingLoot；保存失败或物品定义缺失保留队列，避免静默丢弃。普通 Tick 保留原合批和重试节奏。
- 单人世界通过玩家档案事务提交并带 HarvestWorldId；监听主机通过共享世界库存 AddWorldDrops 提交。客机不创建自己的自然掉落，不把客机本地档案当共享掉落权威。
- 共享库存 FlushForTravel 先冲刷动物队列，再保存共享库存。单人传送、出征和退出菜单也接入相同边界；失败应阻止正常离场并允许重试。
- OnWorldBeginTearDown 在依赖仍存活时补交“旅行已接受之后最后一帧”的掉落。Deinitialize 清空队列太晚，不能承担唯一保存职责；强制结束进程不等于正常退出，不能宣称已覆盖强杀时未提交队列。
- 保存和动作快照是不同合同，连续受击/尸体表现参见同技能的 wildlife-action-snapshots.md。所有自然动物当前只掉 raw_meat_chunk；普通 pig 不进入自然种群，boar 的资产目录仍叫 Pig，不能只靠目录名判断种类。 原因：可施放实现还需要被目录、习得和存档路径识别，漏登记会使入口状态不一致。

入口：Monsters/HillsWildlifeLoot.cpp、WildlifeSubsystem、ColdSteelSharedInventorySubsystem，以及 SceneTestPortal/退出菜单。2026-11-15 完成 Editor 后台构建，未在这轮启动游戏或新增联机实机测试。
