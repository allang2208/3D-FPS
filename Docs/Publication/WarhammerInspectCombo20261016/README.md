# 战锤检视、第二段换手与普通连击节奏发布

2026-10-16，工程 `D:/FPS3D/FPSGAME`，目标 `allang2208/3D-FPS` 的 `main`。本批次是在 [战锤战斗批次](../WarhammerCombat20261015/README.md) 中被特意保留在原位的检视系列与 `NormalComboSwapV5/FlowV6/RhythmV7`。用户已回复“成功了”并要求收尾。本轮只做了归档散列、公开内容与 Git 推送检查，没有重新运行游戏或联机测试。

## 本机已完成内容

- **L 检视（InspectV1）**：双手举锤 → 握紧来回拧 → 逐指抬放 → 右手拨出 → 锤子绕实测柄中线整转一圈 → 双手接住 → 回到待机。纯表现时钟，任何动作都会打断。
- **行走自动检视（InspectWalkSpeedV3）**：只播转锤半段，节奏照双手剑。甩腕过冲 12°；音效只保留挥动风声，钢铁层已按用户要求移除。
- **第二段换手（NormalComboSwapV5）**：把已认可的第一段左右镜像成左手在上。起手竖直时换手，随势前指时换回，首末回到共同待机。
- **普通连击节奏（NormalComboRhythmV7，当前版本）**：每段分四拍（蓄力 → 蓄满一拍 → 0.11–0.14 s 爆发下劈 → 打击），命中时震颤加回弹，挥空时续行后刹住，三段各有性格。被否定的 V6 匀加速版已归档。
- **运行时**：
  - 生成的时序表 `ProductionBluntComboTiming.h`。
  - 非线性攻速：下劈和挥空刹车最多加快 15%。
  - 不改 DPS 的连击视觉承接（`ProductionBluntFlow.cpp`）。
  - 镜头：预备收紧、头部领先、阻尼回位、硬顿挫。
- **联机复核修正**：
  - 缓冲连击遇网络抖动时，服务器给 120 ms 容差，服务器时钟起点放在就绪时间。
  - 拥有端在接触帧做命中表现预测，不结算伤害。
  - 缓冲被撤销时承接立即交还。
  - 第三人称承接的身体发力渐入，进度上报真实速率。
  - 近战下劈到接触附近的身体采样提到约 60 Hz。

接触、挥空与命中回收时长，以及伤害、体力和服务器计时都未改变。完整本机 `FPSGAMEEditor` 与 `FPSGAME` 已于 2026-10-16 00:10／00:11 构建成功。这是构建结果，不是实机验收。

## 公开源码与共享接入边界

[source-manifest.json](source-manifest.json) 记录 Git 基线与散列，分三类发布：

1. **原路径发布**（可完全归属本次）：`ProductionBluntInspect.cpp`、`WarhammerInspectWalkCues.h`、`ProductionBluntFlow.cpp`、`ProductionBluntComboTiming.h`，以及与 HEAD 的差分只含本次修改的 `Characters/FPSPlayerBodyNetwork.cpp`。
2. **[shared-integration.patch](shared-integration.patch)**：只含本次修改的共享文件补丁，涉及以下文件，与其他战锤/并行工作混在一起，公共主线上还没有它们的完整前置：
   - `ProductionToolComponent.h/.cpp`
   - `ProductionToolMotion.cpp`
   - `ProductionAxeContact.cpp`
   - `ProductionBluntAuthority.cpp`
   - `ProductionBluntCombo.h`
   - `FPSGAMECharacter.cpp`
   - `FPSGAMECharacterActionPriority.cpp`
   - `Characters/FPSPlayerBodyActions.cpp`
   - `Characters/FPSBodyMeleePose.h`

   补丁基线是“当前文件逆向去掉本次编辑”（`ProductionBluntCombo.h` 用首次编辑前读到的 V4 文本），**不是直接针对公共 HEAD 的补丁**。基线只留在本机 `Saved/WarhammerInspectComboPublication20261016/`，清单只记它的 LF SHA-256。本机完整文件保持原样。
3. **作者配方**：`SourceAssets/SteelWarhammer20261014/{InspectV1,InspectWalkSpeedV3,NormalComboSwapV5,NormalComboRhythmV7}` 下的 `.py/.ps1/.md`。

**公开切片不能作为干净检出即可构建/运行的完整 FPSGAME**，前置依赖同前一批次的 [本地接入依赖](../WarhammerCombat20261015/integration-dependencies.json)。恢复时先合并工具声明、执行器与共享档案协议，再应用本补丁。

## 制作与资产恢复

| 内容 | 当前入口 | 前置 |
| --- | --- | --- |
| L 检视 | `InspectV1` | `NormalComboV4` 待机、`SprintDragV1` 烘焙函数、`WhirlwindInertiaV8` 求解辅助 |
| 行走检视 | `InspectWalkSpeedV3`（含 `Audio/` 风声提示生成） | `InspectV1` 的握持规则与常量（AST 读取） |
| 第二段换手 | `NormalComboSwapV5` | `NormalComboV4` 的已认可第一段/旧第二段 |
| 普通连击 V7 | `NormalComboRhythmV7`（生成 `ProductionBluntComboTiming.h`） | `NormalComboV4` 与 `NormalComboSwapV5` 的 Blend |

正式包：`/Game/Weapons/SteelWarhammer20261014/InspectV1/A_Warhammer_Inspect[Walk]`，以及写入 `NormalComboV4` 包目录的六段普通攻击（revision `NormalComboRhythmV7_20261015`）。Blend、FBX、UE 包、回执与测量 JSON、诊断图、日志均不随公开 Git 分发；[local-assets.json](local-assets.json) 只记本机散列，不授予再分发许可。恢复次序：原生供体与依赖阶段 → 当前作者脚本 → 对应导入器 → 正式原生构建。换机器时要调整脚本里的本机 Blender/UE 路径。旧导入器会覆盖同名包，不要按目录顺序重跑。

## 废案归档

共 239 个文件、394,519,557 字节（约 376 MiB）移入 `trash/warhammer-inspect-combo-retired-20261016/`，全部按 SHA-256 读回一致，没有永久删除：

- 被否定或已替代的 `InspectWalkV1`、`InspectWalkWristV2` 与 `NormalComboFlowV6` 整个目录。
- 三份 Before 快照：`InspectWalkSpeedV3/Before`、`NormalComboSwapV5/Before`、`NormalComboRhythmV7/Before`。
- `NormalComboSwapV5/Diagnosis/Frames` 逐帧渲染（对照图与脚本保留）。
- 各阶段重复的控制台运行日志。

[archive-plan.json](archive-plan.json) 与 [archive-manifest.json](archive-manifest.json) 记录原路径、目标、大小、散列与原因。归档工具为 [close_warhammer_inspect_combo_20261016.py](../../../Tools/Publication/close_warhammer_inspect_combo_20261016.py)，已执行的有日期清单不再重新生成。

## 技能

个人技能维护源与工程镜像同步更新：

- 新增 [绕柄检视、换手与出击节奏](../../../skills/ue5-fps-arms-animation/references/warhammer-inspect-swap-rhythm.md)，从 [战锤原生骨链](../../../skills/ue5-fps-arms-animation/references/warhammer-native-chain.md) 进入。
- [战锤战斗合同](../../../skills/ue5-weapon-workflow/references/warhammer-combat-contracts.md) 补充运行时钟、承接与联机修正。
- [格挡轮次](../../../skills/ue5-save-load-replication/references/melee-guard-intent.md) 补充缓冲容差与表现预测边界。

## 剩余项

以下尚未实测：

- 真实主机/客机下的连按承接、命中预测与远端下劈观感。
- 预测与服务器判定不一致时的表现。
- 旁观者的空间挥舞音效（沿用前一批次的剩余项）。
