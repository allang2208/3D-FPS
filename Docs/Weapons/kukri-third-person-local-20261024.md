# 尼泊尔弯刀：本地第三人称动作接入 · 2026-10-24

当前普攻三连击改用下述 Combo V3。此前 [全身协调 V2](kukri-full-body-coordination-20261024.md) 未获用户认可；它的待机、装备及其他武技暂时保留，不能把它们视为已接受的动画母版。本页下半部分保留第一轮制作记录。

## Combo V3：用户选定前两刀与中位前刺

用户认可 `Sword Regular Combo` 的前两次攻击，并认可 `Front_Thrust_Middle` 的公开演示作为第三刀参考，随后授权制作第三人称三连击。制作入口为 `SourceAssets/KukriThirdPerson20261024/ComboV3/`。

- Slash1、Slash2 从本地 Quaternius UAL2 CC0 原始完整连击取段，保留原身体、胯、膝和脚的动作。第一段结束与第二段开始使用同一源姿态，第二段低位结束直接接前刺起始；不在连击中插入直立待机。
- 原始动画的参考姿态朝向与当前玩家参考姿态不同。V3 按解剖方向重新映射原始骨骼，使用各身体原生骨长，并以原片脚踝目标求解支撑腿，不复用旧 UAL2 重定向的手臂与脚距结果。
- Thrust 为本轮制作的关键帧：低位收腕、后脚回收、提踵送胯、右手中位前刺、左手护身和回收。刀尖方向按实际右掌挂接与弯刀网格的 +Z 刀尖轴制作。只参考公开动作演示，没有购买、下载或导入该付费包的动画曲线。
- 原玩法仍按原有每段时钟、缓冲窗口、顿帧与命中时刻推进；三段攻击均为 38/30 秒作者长度，第三人称骨轨道为 60 fps。连段尾部保留蓄势，衔接不改变伤害、体力、胶囊移动、镜头和第一人称手臂序列。
- 未续击时播放独立的 Recover1／Recover2（各 0.5 秒）回到当前待机。脚步种子携带作者动作标记，使收势不会被普通站立锁脚抹掉。此标记只影响表现和接地，不触发战斗结算。

Jason 与 Kaitlin 分别按各自原生骨架制作，每套 3 条攻击 + 2 条收势，共 10 份已保存资产。路径分别为 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/Jason/Animations` 与 `ComboV3/Kaitlin/Animations`。`player_body.json` 的对应 10 个角色入口经共享配置事务接入；Cook 目录同步登记。

可编辑源为 `prepare.py`、`inputs.json`、`author.py`、`jason-actions.json` 与 `kaitlin-actions.json`；保存、配置与构建回执分别为 `assets-saved.json`、`published.json`、`build-receipt-FPSGAME.json` 和 `build-receipt-FPSGAMEEditor.json`。该版本默认在后台制作并落盘，没有启动游戏或进行截图、渲染、联机及观感测试；用户认可的是参考方向，尚非最终角色动画验收。

必要 Editor 构建曾被 `AncientBreakingSealComponent.cpp` 对不存在头文件 `ColdSteelInventoryData.h` 的引用阻塞；本轮将该行改为实际声明 `FColdSteelItem` 的 `ColdSteelInventoryTypes.h`。

最终交付：10 份动画资产保存完成，10 个配置角色入口写入完成；Game 构建成功，最终 Editor 构建返回 `Succeeded / Target is up to date`。汇总回执为 `SourceAssets/KukriThirdPerson20261024/ComboV3/delivery.json`。未进行游戏运行、联机或视觉验收。

## 第一轮制作记录

用户选择先使用本地库。制作源与回执集中在 `SourceAssets/KukriThirdPerson20261024/`；第一人称弯刀动作、攻击数值、技能消耗和命中结算保持原执行器。

## 动作来源与制作

| 运行角色 | 本地来源／派生方式 |
| --- | --- |
| Idle | Kevin FREE `HumanM@CombatIdle1H01`，保留呼吸循环 |
| Equip | 从单手待机派生放低到持刀架势；第三人称不复刻第一人称抛刀 |
| Slash1 / Slash2 / Thrust | KayKit 单手横砍、斜砍、突刺，统一进入与恢复到 Kevin 待机 |
| Charge / Heavy | KayKit 单手下劈，按蓄势与释放切分，两段接点相同 |
| Dash | KayKit 单手跳劈；去掉重复的水平髋位移，由现有胶囊冲刺负责移动 |
| Uppercut | Kevin 右手攻击中向前上方出手的片段派生；并非素材包独立提供的原生上挑 |
| Pommel | KayKit 全身出拳片段适配持刀快速近战；保留现有一次命中时钟 |
| Whirlwind.Start / Loop / End | 单手横砍的起势、横扫架势循环与收势；实际转身角度由原技能驱动，不叠加另一圈根骨旋转 |

Jason 共 13 条动作；Kaitlin 使用同组动作独立重定向到原生女性骨架。她的配置只追加本轮角色键，不复制男性配置作为回退。最终资产保存状态分别见 `assets-saved.json` 和 `kaitlin-assets-saved.json`。

源动画重定向结果保存在本轮 `Retargeted/`，最终运行资产为 `Animations/` 和 `Kaitlin/Animations/`。本轮也读取了 UAL2 候选，但最终基础动作使用 Kevin／KayKit；UAL2 候选不接入运行角色。来源记录沿用此前本地原包，详见 [搜索记录](kukri-third-person-animation-search-20261024.md)。

## 接入合同

- 新的 `Kukri` 身体动作分支读取 `UKukriWeaponComponent` 的当前片段、作者时间、普攻播放速率、武技速度及顿帧。接触与释放映射读取实际弯刀时钟，不从第三人称动画触发伤害或扣除资源。
- 服务端的远端玩家从影子档案识别实际弯刀装备；使用现有身体快照、实例匹配、表现租期和有限外推。新增表现不增加战斗 RPC 或修改命中权威。
- 世界刀体是一个跟随右手的静态网格。握点和右手手指来自现有 `A_Kukri_Idle`，通过现有掌骨映射适配身体；不复制一套隐藏的第一人称手臂逐帧播放。
- 左手保留书、枪、施法和消耗品的既有所有权；不建立双手剑的左手扶柄约束。翻越、死亡、收起与切装沿现有生命周期。
- 走跑、蹲姿、跳跃和滑铲保持现有下身移动图；站立攻击保留素材身体姿态，移动时让腿部跟随当前步态。持刀移动保留部分原有上身步态变化。
- 重击蓄满到释放不重启额外交叉淡化；旋风阶段共用相接的横扫姿态。特殊武技属于本地动作派生初版，最终自然度和握刀刃向交由用户体验。

## 文件与制作入口

- `prepare_sources.py`：导入本轮独立 Kevin 源、重定向本地素材并读取生产用骨骼数据；已有素材作为只读输入。
- `selection.json`、`author_actions.py`：动作裁剪、首尾衔接、源比例适配和原生握点头文件生成。
- `save_actions.py`、`save_kaitlin.py`：实际创建并保存各身体的动画包。
- `publish.py`：经 `Tools/PlayerBody/config_transaction.py` 按每个角色键合并 `player_body.json`，保留并行修改。
- `run_commandlet.ps1`：沿现有端口互斥，后台执行本轮独立包制作。
- `build.ps1`：串行 Game／Editor 构建；不关闭或启动编辑器，不运行测试。
- 原生接入：`FPSPlayerBodyKukri.cpp`、`FPSBodyKukriMotion.h`、`FPSBodyKukriGripData.h`，以及既有身体 Actions／Equipment／AnimInstance／Component 的必要入口。
- `DefaultGame.ini`：加入最终两组动画目录的 Cook 路径；制作源和候选不作为本轮新增 Cook 根。

## 本轮完成状态

Game 构建成功（43.70 秒），Editor 构建成功（37.98 秒），日志及回执在本轮源目录。上一轮右下角武器状态栏的源码也已包含于本次二进制。后续 Kaitlin 动画与配置接入不改变原生源码，不重复编译。

Jason 13 份与 Kaitlin 13 份动画均已实际保存，共 26 份；两套身体各自的 13 个动作角色均已通过共享配置事务写入。女性动画保存时遇到 UE Python 未公开同步标记属性的问题，已改为直接读取本轮作者数据中的同一接触／释放比例后保存完成；首次错误日志保留在 `save_kaitlin-first-error.log`。

没有启动可视编辑器、游戏或 PIE，没有运行测试、截图、渲染、联机验收或动作自然度验收。实际保存／配置写入回执不替代用户体验；没有提交或推送 Git。
