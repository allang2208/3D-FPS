# 双手锤普通攻击恢复划空气声，重击保留提前出手音效

2026-10-16 用户最新要求：“普通攻击还是还原回原来划动空气的声音”。当前普通三连击恢复原挥舞声，重击保留此前提前的上挑出手声音。

`ProductionToolComponent.cpp` 的普通三连击恢复 `/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing`，即原“钝器挥舞”划空气声，播放音量 0.38、音高 1.0、从文件头开始。蓄力重击继续选择 `WarhammerAudioPaths::Uppercut`，即现有 `/Game/Weapons/SteelWarhammer20261014/UppercutAudioV1/S_Warhammer_Uppercut`，音量 0.72、音高 1.0，从 0.25 秒处起播。不复制、处理或重新导入音频。

- 普通三连击按原 `WhooshClip`（0.875 / 0.885 / 0.865 作者秒）经已有动作/攻速映射，在各段挥出时播放一次，挥空也播放；装备时明确预加载原挥舞资产。
- 用户随后反馈重击播放滞后：蓄力重击现在在 `BeginUse` 成功进入重击后的同一输入帧播放，不再等下一次动作 Tick。播放从原声音的 0.25 秒开始，跳过渐强前导；不在蓄力按下时播放。
- 沿用每击的 `bSwingSoundPlayed` 门控，挥空同样播放，取消后不继续触发；上挑自己的播放逻辑保留。
- 复用装备异步加载集合中已存在的上挑声音，出手时仅解析驻留对象。普通挥舞旧音仍供行走检视使用，通过原检视 cue 的资源收集保留。
- 冲刺砸地、命中/砸地音、旋风和其他工具声音保持原有选择。未改伤害、动画、攻速、连击、蓄力和网络协议；新增出手声音沿用本地持有者表现入口。

## 重击出手提前

对当前声音制作输入作 10 ms 分段测量后发现：0.00–0.20 秒约为 −39～−23 dBFS RMS，0.25 秒进入约 −14 dBFS 的渐强主体，0.27 秒约 −11 dBFS。原声音从文件头开始，重击却在约 0.075 作者秒内接触，因此明显听感出现在挥击之后。

此前只为蓄力重击将 `PlaySound2D` 的 StartTime 设置为 0.25 秒，保留同一声音的音高、播放速度、音量及后续尾音。上挑仍从文件头播放；未覆盖共享资产。输入帧播放后立即设置 `bSwingSoundPlayed`，后续 Tick 不重复触发。重击的备用动作 Tick 入口也使用相同偏移。本次恢复普攻挥舞声不改变这些重击设置。

测量用于确定制作参数，不是试听或运行测试；0.25 秒是本轮反馈调整值，实际音画由用户确认。

本轮只修改 `Source/FPSGAME/Production/ProductionToolComponent.cpp`。修改前快照保存在 `SourceAssets/SteelWarhammer20261014/AttackReleaseAudio20261016/Before/`，包含当时的共享源码，不得整文件回退覆盖后续工作。

初版“普攻与重击都播放”的 `FPSGAMEEditor` 与 `FPSGAME` 常规构建曾成功。后续“仅重击播放”的源码已落盘，但本次 Live Coding 未成功应用：UBT 115.45 秒后报 `OtherCompilationError`，错误位于其他在途模块 `Building/AlchemyTabletopInteraction.cpp` 的 `TObjectPtr` / `auto*` 类型推导，以及 `UI/ColdSteelAlchemyWidget.h` 的反射声明。本任务没有修改这些文件，也没有启动或关闭编辑器。

当次日志保存在 `Saved/WarhammerAttackReleaseAudio20261016/heavy-only-livecoding-ubt.log`，桥结果为同目录 `heavy-only-livecoding-result.json`（提示 `CompileNotStarted` / `Live coding failed`）。当时编辑器未应用“普通攻击静音”这一后续修订；最终常规构建结果见下方。

“提前 0.25 秒”修订落盘后，等待外部构建结束时桥调用返回 `CompileNotStarted / Live coding canceled`，结果为同目录 `earlier-release-livecoding-result.json`。当时原编辑器已从外部退出，项目进程改为带 `-NoLiveCoding` 的实例；本任务没有关闭或重启它。后续独立 Game 构建在启动前又检测到新的构建占用，因此没有并发启动，当时只交付源码。

## 2026-10-16 续编译完成

用户要求继续完成编译后，等待现有构建与编辑器占用自然释放，依次完成 `FPSGAME`、`FPSGAMEEditor` Win64 Development 常规构建，均返回退出码 0、`Result: Succeeded`。

- Game 成功（26.51 秒），更新 `Binaries/Win64/FPSGAME.exe`。
- Editor 成功，实际编译 `ProductionToolComponent.cpp` 并完成基础 `UnrealEditor-FPSGAME.dll` 链接。
- 两个目标构建前后，本次音效源文件的 SHA-256 保持一致；收据为 `Saved/WarhammerAttackReleaseAudio20261016/FinishBuilds/build-receipt.json`，完整日志为同目录各目标的 `.log` / `-output.log`。
- “普通攻击出手静音、蓄力重击同输入帧从声音 0.25 秒处播放”的修改已进入正式构建产物，不再依赖前述失败/取消的热编译。

本任务没有启动或关闭编辑器，没有启动游戏。

## 最新修订：恢复普通攻击划空气声

在上述常规构建成功之后，用户要求恢复普通攻击原挥舞音。已恢复普通攻击播放门控和独立声音选择，并显式区分普通攻击与蓄力重击，避免普攻再次选到上挑音源。修改前源码快照在 `SourceAssets/SteelWarhammer20261014/AttackReleaseAudio20261016/RestoreOrdinaryAir/`。

本次 `FPSGAME` Win64 Development 常规构建成功（45.97 秒），正式 EXE 已更新。已有编辑器内 Live Coding 返回 `Result: Success / Live coding succeeded`（UBT 275.86 秒，随后完成补丁链接与应用），当前编辑器已应用本次普攻恢复；没有关闭或重启编辑器。日志位于 `Saved/WarhammerAttackReleaseAudio20261016/RestoreOrdinaryAir/`：`game.log`、`editor-livecoding-ubt.log`、`editor-livecoding-result.json`。

本次没有更新基础 Editor DLL，编辑器下次启动前仍需正常完成 Editor 常规构建，不能将上方“普通攻击静音”版本的基础 DLL 记录当作本次恢复的持久 Editor 构建证明。

未试听、未启动游戏、未做运行测试；实际音画效果由用户体验。
