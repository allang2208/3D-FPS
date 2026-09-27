# 废弃地牢刷新池调整 — 2026-09-27

用户要求：剔除女僵尸，加入感染犬、大手、小手。对应类分别为 NurseZombie、InfectedDog、FleshHand、FleshHandMinion；手脑仍是现有 Boss，不与大手混淆。

## 刷新配置

修改真源 `SourceAssets/DungeonSpawn20260925/Config/spawn-groups.json`，保留现有数量范围、锚点、等级加成和普通/精英选择方式。感染犬原先已存在于 ShoredBreach，此次扩展到其他家族。

| 房间家族 | 新池内权重 | 每房数量 |
| --- | --- | --- |
| Distribution | 胖子 2、感染犬 2、小手 2、大手 1 | 2–4 |
| Drainage（包括桥位变体） | 毒蛆 3、感染犬 1、小手 2、大手 1 | 2–4 |
| ShoredBreach | 野狼 2、感染犬 3、小手 1、大手 1 | 2–3 |
| VentilationLoop（包括共享房壳配方） | 突变体 2、感染犬 2、小手 2、大手 1 | 2–4 |
| FreightTransfer | 胖子 3、突变体 1、感染犬 2、小手 1、大手 2 | 2–4 |

权重是每槽抽签比例，不保证每间或每次地牢都出现全部种类。普通房和封门精英房共用这些候选；原有全局存活上限和导航/落点约束继续生效。

`extend_catalog.py` 同时更新源房、以 family_id 继承的共享房壳配方和其内部库，适配目前十二个活动普通房 ID。Composition 重建先刷新源房池，避免再次复制出女僵尸候选。地图安装从当前生成器目录增量修改，保留此前的设备布置、门洞、路线及资产引用。

## 小手作为地牢成员

现有小手类原本属于召唤物：90 秒寿命、零经验、排除技能训练。导演在 FinishSpawning 前写入 `DungeonSpawned`，小手 BeginPlay 只针对该标签应用自然刷新规则：

- 取消存活倒计时，死亡后仍按原尸体时间回收；地牢重新生成时仍由导演清场。
- 移除召唤物/禁止训练/禁止击杀奖励标签，纳入技能训练及正常击杀登记。
- 保留已有正值经验配置；原值为零时使用 **20 基础经验**，这是本轮为自然刷新小手设置的初始数值，尚未做平衡测试。
- 专用小手动作、伤害、尺寸、导航规格、LOD 和低小目标受击规则继续使用原实现。其他来源的召唤小手仍有 90 秒寿命并排除奖励和训练。

## 接入状态

源码及刷新池真源已修改。接入脚本为原批次 `Scripts/install.py`；完成必要原生构建后，通过既有编辑器桥或适用的后台 commandlet 保存。一次性 Live Coding 包装脚本已在发布整理时归档，实际保存状态以 `Receipts/install.json` 的 `spawn_pool_revision=20260927-hands-infected-dog` 为准。

已完成后台常规构建及实际地图保存：

- `Saved/BuildEditor/build-20260927-204016.log`：Editor 基础 DLL 链接成功，Result: Succeeded。过程中定向重建了两份带旧重复符号的中间对象文件，没有修改对应的其他玩法源码。
- `SourceAssets/DungeonSpawn20260925/Receipts/install-pool-revision-20260927.log`：Python commandlet 执行成功，进程退出码 0。
- `Receipts/install.json`：`stage=map_saved`、`spawn_pool_revision=20260927-hands-infected-dog`，保存目标生成器 ExternalActor。十二个活动房间配方、十五个含池模块（含保留源房）、七类怪物硬引用已接入；最终池 ID 列表不包含 NurseZombie。

未运行 PIE、生成预览、多种子或战斗测试。新池用于下一次生成的地牢，不替换正在进行的战斗中的怪物。编辑器保持关闭。
