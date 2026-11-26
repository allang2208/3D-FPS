# 双手锤第三人称：出手速度与实际攻击节拍

2026-10-17，用户确认武器身份修复后动作成功生效，进一步要求：“第三人称的动画有点像慢动作，一点冲击力都没有，加快出手速度，匹配我们的实际攻击”。本轮保留当前全身素材、握持姿态及头部稳定，只调整第三人称播放时钟。

## 原因与修改

旧 `FDonorPlayback` 将素材开始至 Contact 的全部姿态线性铺满准备时间；达到命中后仅按 `Seconds += Delta` 推进，忽略实际收势进度。重击释放也以独立素材时钟推进，没有用释放后的命中窗口定位接触帧。这使原本很短的挥击被摊慢，素材收势也可能落后于战斗状态。

新时钟区分准备、出手、接触后的惯性和收势。准备阶段先播放素材 Contact 前半段；真正释放时加速穿过剩余挥击，并在游戏 Contact 节点精确取到素材 Contact。接触后快速推进到素材 Release 标记，再按本次动作剩余进度完成收势。全身骨骼姿态不重写，不从第一人称复制手腕或锤头轨迹。

## 路径与时间来源

| 动作 | 第三人称时间来源与处理 |
| --- | --- |
| 普通三连击（未命中） | 沿用现有 `BluntClipTime` 进度及攻速换算；以各段 `ProductionBluntCombo::Apex` 作为出手开始，Contact 作为命中，Turn 作为短惯性段末端 |
| 普通三连击（命中） | 保留同一素材，在 `ToolRecover` 的新进度上继续；首段惯性使用 0.10 作者秒，其余时间完成回收；迟到的确认不会将已显示的挥击倒回 |
| 蓄力重击 | 同一素材的准备姿态接续释放；释放后按实际 Contact（基础 0.075 秒，并遵循现有攻速）落到命中姿态，之后 0.12 作者秒完成短惯性段 |
| 冲刺攻击 | 保留既有 0.25 秒举锤状态，释放按原有固定速度的 Contact 对齐；不修改冲刺技能位移或攻速规则 |
| 上挑 | 第三人称改用真实技能时间：1.225 秒开始出手，1.28 秒踏步攻击节点对应接触，1.33 秒结束短惯性段；原有命中暂停继续冻结进度 |
| 快速近战 | 0.22 秒准备结束，0.28 秒接触，0.34 秒惯性段结束，0.72 秒动作结束，读取现有 `WarhammerQuickCombat` 常量 |
| 格挡与旋风 | 已按各自状态阶段同步，本轮保留原播放方式 |

普通攻击的 Apex / Contact / Turn 是既有逻辑片段时钟，不能直接当作所有装备攻速下的实际秒数；`BluntClipTime` 已承担实际攻击时间到这些节点的换算。新逻辑只消费该进度，不修改伤害或攻击间隔。

`ActionEntryFraction` / `ContactFraction` / `ReleaseFraction` 沿用既有复制字段，本地与远端使用同一分段采样逻辑，无新增网络协议。前一轮真实 `warhammer` 身份修复继续保留。

## 文件与状态

- `Source/FPSGAME/Characters/FPSBodyWarhammerMotion.h`：分段素材采样及命中回收连续性。
- `Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp`：发布对应攻击的准备、接触和惯性节点。
- `Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp`：将现有素材 Contact / Release 标记交给新时钟。
- 保留现有 10 个 V7 动画包和 20 处引用，不需要重新导入动画。

源码已保存。首轮构建 `Saved/BuildEditor/build-20261017-001847.log` 被当前工程中 `Super90SpeedloaderAssets.h` 的格式字符串编译错误及构建期间变化的 `SkillWireAudit.h`/生成头文件阻断。后续读取时，两处文件均已更新，本轮没有改写它们；等待共享构建结束后，以更新后的工程继续正式构建。

正式 Editor 构建已成功：`Saved/BuildEditor/build-20261017-003151.log`，结果 `Succeeded`。前面的共享 Editor 构建已编入当前源码，本轮 UBT 返回 `Target is up to date`。本批输出保存为 `SourceAssets/WarhammerThirdPersonTempo20261017/build-editor-retry.log`，交付记录为同目录 `build-receipt.json`。

未启动编辑器、游戏、PIE 或自动测试；新的冲击力与同步观感由用户体验。
