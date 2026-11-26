# 双手锤第三人称未切入全身动画：武器身份修复

2026-10-17 用户反馈 V7 几乎无变化，动作仍不似挥锤、手臂扭曲，并提出若来源不合适就换源。本轮找到阻断全部双手锤第三人称分支的确定性代码错误，因此先修接入，不把用户看到的旧路径表现归咎于新素材。

## 错误链路

`UProductionToolComponent::UsesPickaxeMotion()` 对 `pickaxe` 和 `warhammer` 都返回 true。这是第一人称底层动作复用的谓词，不是武器身份。

`FPSPlayerBodyActions.cpp` 的 `SampleLocalState` 与 `SampleRemoteAuthorityState` 曾按该谓词写入 `State.Weapon = pickaxe`，因此双手锤也被标为矿镐。`FPSBodyWarhammerMotion::Clip` 要求 `Family == Tool && Weapon == warhammer`，入口条件永远不成立。

| 受影响分支 | 错误身份的结果 |
| --- | --- |
| 普攻、重击、上挑、冲刺攻击、旋风、格挡、快速近战全身动画 | `HammerKey` 为空，不会选择已保存的 V5/V6/V7 动作 |
| `CaptureMotion` 的 `FullBodyWarhammer` | 为 false，继续走 `NativeMelee`，采样第一人称工具双腕并映射到第三人称 |
| 全身素材时钟 | 不会启用 `HammerDonorClock` |
| 双手锤视角俯仰屏蔽、头颈稳定 | `Weapon == warhammer` 条件不成立 |
| 服务端远端装备身份及 `SameWeapon` | 同样需要修正，否则本地改对后会与服务端比较不一致 |

这解释了为什么上一轮保存十个新动作、替换二十个 JSON 引用、修改腕部适配后，用户仍反馈几乎没有变化。磁盘上 V7 引用的存在不能证明播放路径使用了它。此前对素材适配的数值分析不等于已经定位用户实际看到的姿态来源。

## 修改

两处第三人称采样均直接使用真实工具身份 `FName(*Tool->Kind)`。保留 `UsesPickaxeMotion()` 的第一人称复用语义，不修改第一人称动画、伤害、工具玩法或现有候选资产。沿用当前 V7 的二十处引用，使这些引用先获得实际进入播放分支的条件。

素材更换作为后续风格选择：本轮已查到 wemakethegame 的 `2Handed Hammer AnimSet`、Hammerhead 的 `Hammer Animation Set` 和 9CG 的 `Hammer Animation Pack` 官方产品页，但未据此认定动态观感合格，也未购买、下载或替换它们。当前没有理由让用户为已定位的接入错误先购买新素材。

## 状态

两处源码修正已落盘。首次热编译桥连接 `127.0.0.1:8000` 被拒绝后，用户已保存并关闭 UE。本轮正式 Editor 构建成功，编译 `FPSPlayerBodyActions.cpp` 并链接 `UnrealEditor-FPSGAME.dll`，日志 `Saved/BuildEditor/build-20261017-000641.log`，结果 `Succeeded`；本批输出为 `SourceAssets/WarhammerBodyRouting20261017/build-editor.log`。

当前 V7 动画引用保持不变，修复让真实 `warhammer` 身份能够进入这些已存在的分支。没有自动打开编辑器、启动游戏、运行 PIE 或进行视觉验收；不将编译成功说成动作观感合格。

用户随后确认“成功了”，并要求加快第三人称出手、匹配实际攻击。后续为 [出手节拍调整](steel-warhammer-third-person-tempo-20261017.md)，保留本页两处身份修复。
