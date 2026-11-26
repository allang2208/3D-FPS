# 战锤快速近战复用双手剑音效

按用户要求，战锤快速近战复用双手剑柄尾快速砸击的同一音效：`/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick`，原始来源为 `quickhit.mp3`。以当前 `RuneSwordComponent.cpp` 的 `bPommelAttack` 出手分支为准：2D、音量 1、音高 1，挥空也播放。

战锤在自己的实际动作时钟跨过 `CockEnd` 时播放一次；当前 V6 为 0.22 秒，即蓄势结束、锤头开始前捅。连续时钟跨界判断支持一帧跨过出手与命中时点，取消后不留独立延迟音效。命中仍为 0.28 秒，总长仍为 0.72 秒。

移除战锤命中分支原有的重复钝器音与手枪快速近战音叠层，包括束缚脱困分支；保留共用的有效命中反馈和全部伤害、范围、体力及动作数据。其他武器音效未改。该音效已在快速近战预加载清单及组件缓存中，不复制、重新导入或在出手时同步加载资产。

代码为 `Source/FPSGAME/Skills/FPSQuickCombatComponent.cpp`、`WarhammerQuickCombat.cpp`。本轮修改前文件及构建回执位于 `SourceAssets/SteelWarhammer20261014/QuickCombatSwordAudioV1/`。默认不启动游戏或试听，实际听感由用户测试。

## 此前构建阻塞与后续完成

音效源码完成后的首次 Game 构建遇到炼金模块尚缺 `AlchemyPresentation` / `SetAlchemyPresentation` 接口；接口随后由并行开发补齐，重试则在 UHT 阶段报错：`FColdSteelAlchemyNetState.Opened` 是 RPC 参数中的 `TMap`，不受复制/RPC 支持（调用位置 `ColdSteelPlayerState.h:264`）。音效任务未修改该炼金模块，当时交付记录明确保留未完成构建状态。

后续战锤左腕 V7 修正任务完成了正式 Game 和 Editor 构建，两目标均 exit 0、当前目标已是最新状态。本次音效接线随之进入正式产物，`delivery.json` 已更新为 `formal_build_complete=true`，构建日志引用 `QuickCombatLeftWristV7/`；本目录旧 `build_receipt.json` 保留首次阻塞证据。未进行游戏或听感验收。
