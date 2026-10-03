# 自动存档周期与写盘开销（2026-09-21）

用户提问：自动存档是不是太频繁、开销大？能不能像主流游戏那样隔一段时间（例如 5 分钟）才自动保存。

结论：**定时存档只是开销的一部分，真正密集的是"动作级"带校验事务**——每次击杀、每次闪避、每次近战命中、每次左轮逐发装填都会写一整份存档。本次把定时周期改成可配置（默认 300 秒）并把进度型事务并入该周期，玩家主动事务、升级与退出仍立即写盘。

## 一、一次存档到底做了什么

`PersistState`（`Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`）在游戏线程上同步完成：

| 步骤 | 内容 |
| --- | --- |
| 1 | `Snapshot()` + `Validate` + 版本迁移（`Migrate`／`ColdSteelQuickBar::Migrate`／仓库布局迁移） |
| 2 | `SaveGameToSlot` 写本次槽位（A/B 交替，本机实测 `Saved/SaveGames/ColdSteelPlayer_A.sav` 约 101 KB） |
| 3 | `LoadDataFromSlot` 回读同一槽位 |
| 4 | `HashBytes` + 写 `.sha1` 校验文件 |
| 5 | `ReadCheckedProfile` 第三次读盘、反序列化、再校验一次 |
| 6 | 升级事务时 `ApplyToPawn` 重算派生属性；`Publish` 后 `OnChanged` 广播给所有面板 |

即一次存档 ≈ 1 次 101 KB 写 + 2 次读 + 2 次反序列化 + 2 次校验，全部同步。数量少时无感，数量密时就是射击中的顿挫。

## 二、改动前的写盘清单（按频率）

| 触发 | 位置 | 频率 |
| --- | --- | --- |
| 定时自动存档 | `ColdSteelProfileRuntime.cpp:412`（旧） | **无条件每 5 秒** |
| 修行经验补写 | `ColdSteelProfileRuntime.cpp:411`（旧） | `bTrainingDirty` 时最快 **每 1 秒** |
| 击杀奖励 | `AwardKill`（`ColdSteelProfileRuntime.cpp:286` 旧） | **每只怪一次** |
| 闪避修炼 | `TrainDodge`（`ColdSteelSkillModel.cpp:47` 旧） | **每次闪避**（`FPSPlayerDodge.cpp:48/84` 两处各一次） |
| 巧手修炼 | `TrainDexterousHands` | 每次换弹／近战奖励 |
| 快捷战斗修炼 | `TrainQuickCombat` | 每次使用／击杀 |
| 大旋风／冲刺攻击／重击修炼 | `ColdSteelWhirlwindModel.cpp:50`、`ColdSteelDashAttackModel.cpp:41`、`ColdSteelHeavyStrikeModel.cpp:12` | **每次命中批次** |
| 火球／火系魔法／冰锥／闪电／圣光命中与击杀结算 | 各 `*Model.cpp` 结算尾 | **每轮命中** |

实测参考：连射杀怪时，"1 秒补写 + 每杀一次"叠加，平均每秒都在写约 100 KB 并回读两次——这正是用户感觉到的开销。

## 三、改动后的口径

1. **定时自动存档改为可配置周期**：新增控制台变量 `fps.Save.AutosaveSeconds`，默认 **300 秒**（0 = 关闭定时存档，下限不做额外钳制，取负值等同关闭）。可在 `Config/DefaultEngine.ini` 的 `[ConsoleVariables]` 里写死默认值，也可运行时用控制台／F6 面板临时调整。
2. **只在有未写盘增量时写**：累加器到点时若 `bTrainingDirty` 为假就跳过，不空写。空闲挂机不再产生任何写盘。
3. **进度型事务统一走 `StageTraining`**（与子弹命中修炼同一机制）：实时档案立刻更新，伤害、奖励、面板读数保持精确；写盘并入上面的周期。涉及：`AwardKill`、`TrainDodge`、`TrainDexterousHands`、`TrainQuickCombat`、`TrainWhirlwind`、`TrainDashAttack`、重击修炼、火球／火系／冰锥／闪电／圣光的命中与击杀结算。
4. **仍然立即写盘**（不能被周期推迟）：
   - 玩家主动事务：拾取、移动／交换／拆分／丢弃、使用消耗品、强化、附魔、仓库存取与整理、快捷栏绑定、枪匠应用、弹种换装（`ConsumeAmmo`）等 `CommitState` 路径；
   - **升级**：`StageTraining` 内部检测到角色或技能升级时立刻走一次带校验事务，升级提示与派生属性同一次提交；
   - **退出**：`Deinitialize(){SaveNow();}`（`ColdSteelProfileRuntime.cpp:110`）与 `FPSGAMECharacterProfile.cpp:144` 的角色存档路径。
5. 删除 `TickRuntime` 里的 1 秒补写分支。`TrainingFlushAccumulator` 成员暂时保留（见"热补丁注意"）。

## 四、代价与边界

- 硬崩溃／断电最多丢**一个自动存档周期**（默认 5 分钟）的战斗收益：击杀计数、角色与技能经验、修炼进度。物品、装备、强化、仓库、弹种换装、升级都不会丢。
- 弹匣／背包弹药、法力、体力、冷却、树木生长日晷等会随周期一起写盘；崩溃后回退到上一次写盘值。回退方向对玩家有利（弹药回补），不影响存档校验。
- 这不是回到"每次命中都写盘"，也没有改存档格式、槽位交替（A/B）或校验语义；`Validate`／迁移／失败不提交的合同不变。

## 五、热补丁注意（重要）

`UColdSteelStatusModel::Current`（内存档案）与 `SaveAccumulator`、`TrainingFlushAccumulator` 都是**非 UPROPERTY** 成员。若热补丁因类布局变化触发对象重实例化，`Current` 会被默认构造，内存中的角色档案归零，随后任何事务都可能把空档案写回覆盖好档。因此本次**特意没有删除** `TrainingFlushAccumulator`，让本批只改函数体，类布局不变；要删它请随一次关闭编辑器的常规构建一起发布。

## 六、验证状态

- 编译：本批 10 个翻译单元全部编译成功（`.obj` 均晚于源码，见下"最终状态"）。
- 构建过程：链接曾三次被并行会话正在编辑的文件阻塞，均不属于本次改动、未做任何修改——`Source/FPSGAME/Characters/FPSBodyAssetPreloader.cpp`（`GetAssetsByPath` 参数类型、`IsWantedPath` 未定义，exit 6，日志 `Saved/BuildEditor/build-20260921-235946.log`）与 `Source/FPSGAME/Monsters/WitchRebuiltMonster.h:21`（UHT：参数名 `Mesh` 与 `ACharacter::Mesh` 同名，`-WarningsAsErrors` 下报错，日志 `Saved/BuildEditor/build-20260922-000101.log`）。这两个文件随后被各自会话修正，`Saved/BuildEditor/build-20260922-000331.log` 记录 `Result: Succeeded`。
- 最终状态：本批 10 个翻译单元的 `.obj` 均晚于各自源码（9 个技能／修炼文件 23:58:47–23:59:06，`ColdSteelProfileRuntime.cpp` 00:03:52，含最后一次 include 顺序整理），`Binaries/Win64/UnrealEditor-FPSGAME.dll` 在 **00:03:54** 重新链接、晚于全部相关 `.obj`，即改动已进入模块 DLL。
- 未做：运行期验证、卡顿实测、崩溃丢档观察。按项目规则由用户自行测试。
- 热补丁（Live Coding）：本次刻意保持类布局不变（见第五节），不会触发 `UColdSteelStatusModel` 重实例化清空内存档案。

## 七、调参建议

| `fps.Save.AutosaveSeconds` | 用途 |
| --- | --- |
| 300（默认） | 主流节奏，战斗中基本无写盘感 |
| 600–900 | 长时段探索，进一步减少写盘 |
| 60–120 | 想更保险地保留战斗收益时的折中 |
| 0 | 只保留事务／升级／退出写盘 |