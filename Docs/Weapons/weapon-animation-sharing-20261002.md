# 武器动作复用扩展（2026-10-02）

本轮补齐 Pit Viper 的双持配件姿态差量，并将后续枪械、剑、弓、法杖和工具的动作复用纳入统一接入流程。已有共用序列和程序姿态继续沿用，机构、接触与玩法时钟保持各自职责。

## Pit Viper 已保存制作

- 作者输入仍为单持17段、双持右/左各21段，共59段；沿用当前 V7 原生绑定和已经适配该枪的动作，不直接跨枪引用 M1911 骨架动画。
- 四份 `WeaponGripProfile` 已实际保存：左右手各 fitted、long，位于 `/Game/Weapons/AnimationProfiles20261001/ue_pit_viper2011/Dual_r|l/DA_fitted|long`。
- 每份配置包含 quickcombat、quickcombat_empty、quickcombat_left、quickcombat_left_empty 四个基础/变体配对；16组全部制作为差量，无独立保留配对。
- 配置合计234,424字节、4,394个差量关键帧。统计来自实际保存回执；不是运行内存或帧率测量。
- 运行源码 `PistolDualWieldComponent::LoadHand` 已按定义、左右手和 family 查找配置，用基础序列替代变体播放；`StartAction` 选择动作层，`Pose` 设置动画实例 GripProfile，原动画通道按同一动作时间应用差量。本轮复用这些既有接口，没有修改原生 C++。
- 完整动作集合中16段变体不再需要独立完整序列播放，剩余部分为43段。59份作者资产仍保留，也仍可能被原目录 Cook；未删除资产或宣称包体下降。

末发、空仓待机/奔跑、普通/空仓换弹、左右侧动作和转枪收势保留。没有将半自动射击、不同装填机构或不同骨架合并。

## 制作和维护入口

- `SourceAssets/WeaponAnimationSharing20261002/prepare_manifest.py`：读取该枪当前作者配方，生成四份明确输入清单。
- `install_profiles.py`：调用共用制作器，以独立清单、回执和资产归属执行保存。
- `run_install.ps1`：通过现有 UE 批次互斥后台制作，再汇总保存回执。
- `install_receipt.json`、`production_summary.json`：实际保存的配对、输入散列、配置大小和关键帧数量。
- `SourceAssets/PitViper2011Integration20261002/run_import.ps1`：动作重新导入后同步调用差量制作，避免源动作与运行配置不同步。
- 原整批 `WeaponAnimationSharing20261001/make_manifest.py` 也已加入该枪和稳定制作归属；没有重写10月1日的历史清单或统计。

共用制作器新增可选批次根目录与归属参数，原入口默认行为保持。后续武器可用同结构清单，无需复制制作算法。重制配置时清除旧条目，再按当前配对完整生成，保留作者动作作为输入。

## 弓、法杖和工具的后续标准

| 当前武器 | 已有共享方式 | 后续接入规则 |
| --- | --- | --- |
| 弓 | `bows.json` 的 `bow_animation_prefix` 共用 ElasticV15 手臂序列，搭箭使用 NockContinuityV21；改造部件、弦和弓体形变沿用动作状态 | 同手型的弓体/弦/箭台不复制整套手臂动画；需要不同接触姿态时，配对同骨架同源时长的作者序列，并接入弓自身采样链后保存差量 |
| 法杖 | `StaffGripPose`、`StaffChargeFlow`、走跑与空闲左手共用程序动作和原作者姿态键，按握柄选择变体 | 杖头、颜色或材质变化不新增整套动画；握柄和新动作沿用共有时钟及变体姿态键。只有确需作者序列时才增加对应的 Profile 消费层 |
| 剑/斧/矿镐 | 同类武器的共同动作前缀及既有长握柄差量 | 同类姿态变体采用差量，挥砍、突刺、格挡与采矿继续保留独立用途 |

本轮没有新增弓或法杖的作者动作，也没有生成这些武器的 Profile 资产：它们当前已有共享实现，额外复制或转换不会减少重复动画。统一标准要求下一次新增/改版武器时同时完成作者动作、共享配置、运行消费、重导入联动和落盘记录。

规则同步至工程与个人 `ue5-fps-arms-animation`、`ue5-weapon-workflow`。源码、动作集合、已保存配置、实际 Cook 和运行测量分别统计。

## 构建与交付边界

本轮差量制作 commandlet 退出码为0，回执 `complete=true`；日志为 `SourceAssets/WeaponSurface20260930/logs/install_profiles.20261002-161857-111.log`。没有启动编辑器界面、游戏、PIE、测试、截图或验收渲染。

此前新枪原生接入曾因现有编辑器占用而未完成构建。用户关闭 UE 后，执行 `SourceAssets/PitViper2011Integration20261002/build_editor.ps1`，正式 `FPSGAMEEditor Win64 Development -Module=FPSGAME` 构建结果为 `Succeeded`，`UnrealEditor-FPSGAME.dll` 已链接落盘，耗时75.33秒。日志为 `Saved/BuildEditor/pit-viper2011-20261002.log`，实际 DLL 路径、大小及保存时间记录在作者目录的 `build_receipt.json`；交付回执已同步。没有启动编辑器或游戏、没有运行测试，效果由用户测试。
