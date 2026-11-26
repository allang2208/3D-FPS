# 战锤第三人称：Sevarog 动作适配

2026-10-16。用户已将 Epic 官方免费 Paragon: Sevarog 导入当前 FPSGAME，并授权继续双手锤第三人称动画替换。

## 范围与动作映射

本批先替换普通三连击、各段命中回收、蓄力和砸地。Sevarog 的完整骨架动作作为来源，离线重定向到当前 `player_body.json` 的 Jason 身体，并按实际战锤握点适配双臂。第一人称动作资产、伤害、体力、攻速规则及命中权威不修改。

| 现有状态 | 本批动画键 | 时钟 |
| --- | --- | --- |
| WarhammerSlash1 | Warhammer.FullBody.Slash1 | 普攻非线性作者进度 |
| WarhammerSlash2 | Warhammer.FullBody.Slash2 | 普攻非线性作者进度 |
| WarhammerSlash3 | Warhammer.FullBody.Slash3 | 普攻非线性作者进度 |
| ToolRecover + WarhammerSlash1 | Warhammer.FullBody.Slash1Recover | 独立命中回收进度 |
| ToolRecover + WarhammerSlash2 | Warhammer.FullBody.Slash2Recover | 独立命中回收进度 |
| ToolRecover + WarhammerSlash3 | Warhammer.FullBody.Slash3Recover | 独立命中回收进度 |
| WarhammerCharge | Warhammer.FullBody.Charge | 蓄力进度及取消权重 |
| WarhammerSlam | Warhammer.FullBody.Slam | 现有砸地时钟，含固定 0.7 秒停留 |

旋风、上挑、快速近战、格挡、装备和检视本批沿用原实现，不将它们计入本批替换数量。

## 实现边界

- 新增 `FPSBodyWarhammerMotion.h`，仅选择 `Tool/warhammer` 对应动画。继续沿用现有第三人称动作混合与联机状态，不扩展游戏行为枚举或复制协议。
- `FPSPlayerBodyAnimInstance.cpp` 直接使用战锤已同步的作者进度，不再次通过剑的 Contact/Release 规则重定时；新动画接管时关闭旧程序发力和视模手腕轨迹。
- `FPSPlayerBodyMotion.cpp` 在有同骨架战锤动画时采样冻结的装备握持，保留锤体及模块挂点，避免第一人称挥击重复驱动第三人称武器。
- 人物实际移动仍由原角色移动负责。普通攻击移动时沿用现有下肢混合，站立时保留全身动作；重击保留现有发力及接地策略。
- 未取得并保存对应新资产时不发布配置引用。源文件、资产保存、DLL 构建和用户视觉验收分别记录。

## 制作入口

`SourceAssets/WarhammerThirdPersonSevarog20261016/`：

- `prepare_sources.py`：读取原始动作及真实武器握持，保存独立 IK Rig、Retargeter 和 Jason 候选。
- `selection.json`：实际选片和作者时钟映射；普攻取 Swing1/2/3，回收取对应 Return2Idle，蓄力砸地使用 Swing3 的上举、下压和收势。
- `author_actions.py`：保留原动作的身体发力，适配原生骨长、双手握柄、接地及收势。
- `save_actions.py`：保存最终独立动画、同步标记和来源元数据。
- `run_commandlet.ps1`：使用已有资产批次互斥，后台执行制作，不打开 UE 界面。

目标目录：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/`。

## 来源与当前状态

来源：[Epic Games — Paragon: Sevarog](https://www.fab.com/listings/a4882b5e-cfad-4830-a3dd-46a6c31a79b2)。第三方源资产及派生密集骨轨道留在本机，遵守来源许可；不将 Paragon 名称用于游戏宣传。

源骨骼轨迹显示 Swing3 的双腕明显下压至身体低位，作为本批砸地来源；Soul Siphon 的左手脱离武器，不用于双手重击。12 段候选已保存至本批 Retargeted 子目录，来源与路径在 `retarget-receipt.json`。第二、三击入口承接上一击的连段点，命中回收保留 0.08/0.07/0.12 秒的停顿。蓄力末帧与砸地起帧使用同一源姿势。

运行入口与制作脚本已落盘。2026-10-16 16:52 的 `FPSGAMEEditor Win64 Development` 构建成功，DLL 已生成，记录见本批 `build-receipt.json`。

2026-10-16 17:07，后台 commandlet 已将最终八段动画保存至 `Animations/J_SevarogHammer_*`；`assets-saved.json` 为 `complete: true`。八个 `Warhammer.FullBody.*` 引用已写入 `Content/ColdSteelData/player_body.json`，发布记录在 `assets-published.json`。制作使用既有批次互斥，源资产只读，最终动画写入本批专属目录。

120 Hz 动画在关闭数据写入 bracket **之前** 调用原生 `finalize_authored_animation`，使 `NotifyPopulated` 先同步压缩采样率；关闭后再等待最终压缩并保存。否则 1.75 秒和 1.275 秒片段会与默认 30 Hz 压缩采样发生非整数帧冲突。无需修改引擎或共用作者工具。

本轮未主动打开或重启编辑器，未运行游戏、PIE、测试或验收渲染。实际重量感、双手接触、移动混合及联机表现由用户在新启动的游戏会话中体验；构建和资产保存不代表视觉验收通过。

## 头部跟随修订

用户要求战锤第三人称头部参照双手剑，不再随镜头扭动。头部组件沿用身体的局部骨骼姿态，面部额外 HeadMovementIK 已由共用外观流程关闭；本次修改 `FPSPlayerBodyAnimInstance.cpp`，仅对 `Tool/warhammer` 去掉基础脊柱姿态的镜头俯仰叠加，覆盖待机、移动、动作进入和退出。保留源动画自身的胸颈发力、下蹲、滑铲和受击姿态，不改第一人称镜头或实际瞄准方向。

源码已保存。现有编辑器的 Live Coding 返回 `CompileNotStarted / Live coding canceled` 后，用户保存并关闭 UE；随后 `FPSGAMEEditor Win64 Development` 常规构建成功，重新编译 `FPSPlayerBodyAnimInstance.cpp` 并链接正式 `UnrealEditor-FPSGAME.dll`。日志：`Saved/BuildEditor/build-20261016-172253.log`；本批输出：`SourceAssets/WarhammerThirdPersonSevarog20261016/head-follow-build.log`。此修订未进行运行测试，未重新打开编辑器。

## 冲刺举锤修订

冲刺举锤不再把普通 2 秒蓄力压缩到 0.25 秒。已新增并接入独立的 `SprintLift` 和 `SprintSlam`，修复冲刺入口、参考姿态偏移、前臂滚转与两段之间的混合；普通蓄力及普通砸地仍保留本页原资源。详见 [第三人称冲刺举锤衔接](steel-warhammer-third-person-sprint-lift-20261016.md)。
