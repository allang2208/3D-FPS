# Super90 普通空仓换弹：抓握拉机柄

用户要求不使用快速装填器时，普通空仓换弹也应有明确的拉机柄操作。旧 `A_Super90_reload_full` 只有短促枪机释放。本次保留逐发装填段，替换第 360 帧之后的收尾。

## 动作与时钟

- 第 0–360 帧保留原逐发装填；每发装填接触、跳过未使用装填循环的规则不变。
- 第 360–378 帧：右手从装填口收回后握把，使用渐入渐出的 0.3 秒过渡。
- 第 378–444 帧：接当前已保存的 R24 `A_Super90_loader_cycle`，原速完成左手抓柄、后拉、释放和回握。整枪与双手作为同一组从装填构图过渡到拉柄构图，抓柄接触前完成构图差量消退。
- 原普通空仓此时已经开栓，接入段保持开栓，避免复用 cycle 起始待机时出现先关闭再打开。
- 保留 R24 的 5 mm 额外后拉及手部接触，不复用曾导致枪机后端穿出的 24 mm 旧行程。

新源长为 7.4 秒，比旧 7.0667 秒增加 0.3333 秒；逐发推进和拉柄本身均未加速。`FullReload` 仍是原有属性换算参考，避免改变逐发速率和快速装填器属性换算；实际动作时长读取已保存序列。

源时钟：后拉音效 6.8369819 秒、释放音效 6.93970645 秒、上膛完成 6.9769231 秒。普通装填沿用自己的 `ChargePullSound` / `ChargeReleaseSound`，快速装填参考原声不改。少量补弹和提前结束逐发装填时，音效延迟计算也使用同一段尾跳转映射。

中断后只欠上膛的状态，直接使用既有 cycle 动作，不重播装填口回握，不显示装填器道具；业务、动画和音效均采用 cycle 本地时间。非空仓补弹仍使用原闭栓收尾。

## 文件与交付

制作源：`SourceAssets/Super90NativeEmptyBolt20261010/`。`inputs.json` 来自当前安装的普通空仓、idle、R24 cycle 及四份握把配置；`author_motion.py` 生成新序列和差量，`timing.json` 记录时钟，五套可编辑动作位于 `Super90_NativeEmpty_Editable.blend`。旧内容与 C++ 源备份在 `Before/`。

源码修改为 `FPSGAMECharacterSuper90.cpp`、`Weapons/Super90WeaponAssets.h`，以及 `FPSGAMECharacter.cpp` 内 Super90 机械音效时间换算。没有新增反射属性、运行时加载或逐帧资产扫描。

Editor / Game 必要构建均成功，日志为 `build-FPSGAMEEditor-20261010-191949.log`、`build-FPSGAME-20261010-192017.log`；回执 `native-build-receipt.json`。两个既有弃用警告分别位于 `ColdSteelPlayerState.cpp` 与 `M4GunsmithPreview.cpp`，本次未改动它们。

普通空仓序列和四份 Profile 共五项已后台实际保存，`save_receipt.json` 为 `completed=true`；日志 `import-commandlet-20261010-192230.log` 记录 `SUPER90_NATIVE_EMPTY_BOLT_SAVED 5 assets`。保存脚本仅覆盖普通空仓序列和四份 Profile 的对应条目，保留普通补弹、快速装填、近战和移动握姿。未运行游戏、截图、渲染或新增验收测试，最终动作由用户体验。
