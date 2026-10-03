# PKM 用户录屏换弹音替换 — 2026-09-28

来源：用户提供的 `C:/Users/allan/Videos/NVIDIA/Delta Force/Delta Force 2026.09.28 - 22.35.40.01.mp4`，15.15 秒，三角洲行动游戏录屏。录制来源不等于游戏音频的公开再分发许可；本轮仅接入本机工程，未发布资源。

按画面动作与音频瞬态定位截取 10 段，精确区间见 cuts.json。前段开火不纳入切片。输出 48 kHz、16-bit PCM、双声道；保留源电平和音高，仅 3 ms 淡入、12 ms 淡出，没有追加降噪或音色重建。

实际替换并保存 ReloadAudio22 的 CoverOpen、BeltLift、BoxOut、BoxInsert、BeltSeat、CoverClose，以及 ChargeAudio35 的 ChargePullMove、ChargeRearStop、ChargePushMove、ChargeFrontStop。保留原 SoundWave 设置与 C++ 动画触发时刻。LMG201 已共享这些 PKM 资产，其换弹声音会一并变化；PKM 装备时复用的拉栓声也随原有引用更新。

导入通过 UnrealEditor-Cmd 后台执行完成，10 个资产保存记录见 import_receipt.json。旧资产备份在 backup/。重做本次导入使用 import_ue.py；旧 BeltAudio22 / ChargeAudio35 的制作脚本仍代表旧音源，不要用来恢复本轮结果。

未启动图形编辑器或游戏，未做运行测试或主观试听验收，由用户测试。
