# 符文剑转刀音效 V1

> 2026-11-07：本文保留历史方案。当前转刀只使用新导入的两款划空气声与结束入手声；用户确认后，已将无引用的旧嗡鸣及试听移入 `trash/RuneSwordInspectAudio20261107/`，仍有共用引用的落掌声、命中声与结束入手声保留，见[调整与清理结果](runesword-inspect-audio-20261107.md)。

2026-11-02。用户要求：转刀时用金属嗡鸣，回到手上时使用雷神之锤「贯雷」召回接锤音效。

## 设计

- **转刀嗡鸣**：原创程序合成，无第三方采样。低频非谐波钢体共鸣 + 1 kHz 以上金属模态，音量与高频亮度跟随实际 R6b 检视动作里剑身在画面上的转速（`speed_profile_r6b.json`，由 `motion_profile.py` 量 `Final/Standard/A_RuneSword_Inspect.fbx` 得到）。因此声音自然形成「甩出大波 → 掌心段回落 → 推剑小波」三个起伏，而不是一条平直嗡声。
- **接锤**：直接复用用户选定的贯雷召回接锤 `S_GuanLei_RecallCatch`（`RecallAudioUserV4`，来源 `接住钝器.mp3`），不重新制作、不改音高。
- **落掌轻响**：保留原来已通过的甲片轻响层，音量从 0.22 降到 0.16，避免和嗡鸣抢中频。

## 文件

- `Audio/S_RuneSword_InspectMetalWhir.wav`：标准版（0.408 s，峰值 −6 dBFS，48 kHz 立体声）。
- `Audio/S_RuneSword_InspectMetalWhir_Heavy.wav`：更低沉、低频更多的重剑变体。
- `Audio/S_RuneSword_InspectMetalWhir_Bright.wav`：更亮、金属模态更开放的变体。
- `Audition/RuneSword_Inspect_Timeline_*.wav`：按游戏内音量（嗡鸣 0.5、接锤 1.0）拼好的 0.414–0.822 s 时间轴试听；不含 0.528 s 那层音量 0.16 的甲片轻响（该层沿用库里现成 SoundWave，试听不重复叠）。
- `Audition/RuneSword_Inspect_Timeline_Catch_0p92.wav` / `_Catch_1p05.wav`：接锤降调／升调的对比试听（仅试听，未接入）。

## 时间轴

以 `RuneSwordInspectFeel::Motion` 为准：

| 时刻 | 事件 |
| --- | --- |
| 0.414 s | 松拳，嗡鸣开始（同时有一声很轻的离掌 tick） |
| 0.528 s | 剑柄落在掌心，甲片轻响 |
| 0.822 s | 握死，停止嗡鸣并播放贯雷接锤 |

## 接入

- `Source/FPSGAME/Weapons/RuneSwordInspectFeel.h`：`HumSoundPath`、`LandSoundPath`、`CatchSoundPath`、`HumCue/LandCue/CatchAt`、音量与淡出常量。
- `URuneSwordComponent`：`InspectHumSound/InspectLandSound/InspectCatchSound` 三个加载引用；`BeginInspect` 重置 cue；inspect tick 内按时间触发；`StopInspectHum` 在接锤、动作结束、`CancelAction`、`EndPlay` 时淡出或停止。两条回退：嗡鸣资产缺失时退回武器自身挥动声，接锤资产缺失时退回原配重锤命中声，避免检视变成无声。

嗡鸣使用独立 `UAudioComponent`（`CreateSound2D(..., bAutoDestroy=true)`，引擎内部已自动 `Play()`），中途被打断时 80 ms 淡出，不会压到下一个动作。

## 生成与导入

- `author_spin_audio.py`：合成三个候选、生成试听与 `audio_manifest.json`。
- `import_audio.py`：UE commandlet 导入，PCM/ForceInline、不循环、沿用近战命中声的声音类别，写来源元数据标签。
- `run_import.ps1`：等构建/编辑器空闲后跑 commandlet 导入并保存资产（另一会话的构建或 commandlet 在跑时排队等待，不停止任何进程）。

导入回执 `import_receipt.json`：三个 SoundWave 已保存到 `/Game/Weapons/AzureRunesword20260913/InspectAudioV1/`，commandlet 结果 `0 error(s)`（23:14 首导、23:45 重导为最终版）。`/Game/Weapons/AzureRunesword20260913` 已在 `DefaultGame.ini` 的 `DirectoriesToAlwaysCook` 中，打包不需要额外加目录。

**已编译进 DLL。** `FPSGAMEEditor Win64 Development` 全量后台构建成功（`Result: Succeeded`，817 个动作，1695 s，`Saved/BuildEditor/build-20261102-2316-inspect-audio.log`），`RuneSwordComponent.cpp` 编译无警告，`UnrealEditor-FPSGAME.dll` 于 23:44:35 重新链接；三个音效路径在 DLL 中以 UTF-16 字面量存在，确认接入生效。

未试听验收、未运行游戏测试；主观听感由用户判断。三个候选里目前接入的是标准版，换 `HumSoundPath` 一行即可切到 Heavy / Bright。

