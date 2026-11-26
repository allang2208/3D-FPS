# 魔晶双手剑「星髓长锋」充能音效

2026-11-04。用户提供 `D:/FPS3D/资产/音效/魔晶充能.mp3`，要求导入对应位置，作为魔晶双手剑充能技能释放时的音效。

## 素材与处理

- 原文件保留在 `Source/StarMarrow_Charge.mp3`，浮点解码源同目录，`Source/` 仅本机保留。
- 处理：48 kHz 立体声，保持原音高、原速度、原声道与音色；只裁去首尾近静音（前 23.0 ms、后 35.7 ms），加 1 ms 边缘淡入淡出。峰值 −5.62 dBFS 未触发削波，增益 1.0，未做均衡。
- 成品：`Audio/S_StarMarrow_Charge.wav`，0.973 s。

## 接入

- 资产：`/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeAudio20261104/S_StarMarrow_Charge`，PCM / ForceInline、不循环，声音类别沿用近战挥砍声（`S_Sword_Attack`）。
- 播放点：`UStarMarrowComponent::PresentChargeMotion()` 里动作真正开始的那一帧，本地预测与迟到/重复的权威确认共用 `bChargeSoundPlayed` 只响一次；专用服务器不创建音频。
- 预载：随 `LoadFlames()` / `LoadHUD()` 的同一批装备时机异步请求，G 键触发时不读盘。
- 清理：`Clear()`、充能结束 `OnRep_State` 尾段与 `EndPlay` 都走 `StopChargeSound()`；用独立 `UAudioComponent` 以便取消时 80 ms 淡出，不会盖到下一动作。
- 音量/音高：1.0 / 1.0，与素材原样一致。

## 时间关系

| 时刻 | 事件 |
| --- | --- |
| 0 s | G 键释放，充能动作起手，音效同时起音（素材起音在 67 ms 处，属素材自身包络） |
| 0.35 s | 素材内部峰值 |
| 0.97 s | 素材结束 |
| 1.64 s | 动作的 `StarMarrowChargeMotion::Release` 释放拍（本音效不覆盖该拍） |
| 2.2 s | 动作结束回待机 |

如后续需要「释放拍」另配一声，那是独立需求，本轮没有加。

## 生成与导入

- `prepare_audio.py`：裁切、边缘淡入淡出、防削波、生成试听与 `audio_manifest.json`。
- `import_audio.py` / `run_import.ps1`：commandlet 导入保存；导入前会等其它会话的构建与 commandlet 结束，不停止任何进程。

回执：`import_receipt.json`（资产已保存）。UE 资产在 `F:/FPSGAMEData/Content/Weapons/FrostCrystalSword20260915/StarMarrowChargeAudio20261104/S_StarMarrow_Charge.uasset`。

## 构建状态

- `StarMarrowComponent.cpp` 的改动本身没有编译错误；但 2026-11-04 23:22 那一轮 `FPSGAMEEditor` 构建被同一工作区里其他会话的未完成改动拦下：`Dungeons/FacilityFreightEncounter.cpp`／`FacilityHallPreparation.cpp`／`UI/ColdSteelCrosshair.cpp`／`UI/ColdSteelPanelNavigation.cpp` 报 C4459（局部变量遮蔽）、项目开启 `/WX`。这些文件与本批音效无关，本轮没有修改它们，也没有替其他会话修补半成品。
- 已确认二进制侧：23:19:20 链接的 `UnrealEditor-FPSGAME.dll` 中已有 `S_StarMarrow_Charge`、`StarMarrowChargeAudio20261104`、`LoadChargeSound`、`StopChargeSound`；但 23:21 追加的「异步未加载完时下一 tick 重试」是小改动，尚未进入任何成功链接。等其它会话的编译错误消除后需再跑一次 `FPSGAMEEditor`。

## 试听

- `Audition/StarMarrow_Charge_Only.wav`：处理后的单发本体。
- `Audition/StarMarrow_Charge_OnMotion.wav`：放在 2.2 s 充能动作时间轴上的位置（0 起音），用于核对与起手是否对齐。

未试听验收、未运行游戏测试；实际听感与音量平衡由用户判断。
