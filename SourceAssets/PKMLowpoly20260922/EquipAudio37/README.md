# PKM 装备音效：改用自身后拉摩擦（EquipAudio37）

2026-09-23。用户要求把 PKM 装备时的音效换成它自己的「拉伸音效」。已确认指 `ChargeAudio35` 的后拉摩擦 `S_PKM_ChargePullMove`——保持音高的时间伸缩（tempo 2.30）那一段，也是空仓换弹在 5.13 s 源接触播放的同一资产；装备开始时单发播放一次。

## 改动

`Source/FPSGAME/FPSGAMECharacter.cpp` 的装备分支（`BeginWeaponAction`）：

- 原路径：PKM 走到最后的 `else PlayMechanicalSound(EquipSound, AKMSource::ActionVolume)`，也就是借用 AKM 的 `S_AKM_Equip`。
- 现在在 QBZ 分支之后新增 PKM 分支：按 `PKMLowpolyWeaponAssets::ChargeSoundPath(TEXT("ChargePullMove"))` 读取 `/Game/Weapons/PKMLowpoly20260922/ChargeAudio35/S_PKM_ChargePullMove`，用同一个 `PlayMechanicalSound(..., AKMSource::ActionVolume)` 在动作开始时播一次；读不到时回退原有 `EquipSound` 并打警告，不会静默丢音。
- 不加 cue 时间轴：PKM 装备片段 `A_PKM_equip`（0.90 s）本身没有拉柄行程，本轮只换单发资产，不改动作、不加第二个接触点。音量、声部复用同一 `MechanicalVoices` 路径与既有倍率，pitch 仍为 1。

## 依据

- `../EquipCharge31/README.md`：「装备实际参考 0–0.85 秒……此段未见独立拉栓，不额外添加装备拉栓」。
- `../ChargeAudio35/audio_manifest.json`：`ChargePullMove` 取自视频 24.180–24.710 s，`tempo 2.3043478260869614`（保音高时间伸缩），`empty_source_time 5.13`，`wav_sha256 2fd0a9c2…`。
- 候选与播放形式由用户在 2026-09-23 确认（后拉摩擦单发；不是后拉＋前止两段，也不是弹链提起）。

## 状态

- 本次改动的 TU 先用 UBT 记录的编译命令独立编译通过：`cl.exe "@…/FPSGAMECharacter.cpp.obj.rsp"`（工作目录 `Engine/Source`），cl 退出码 0，obj 21:58:45 晚于源码 21:57:38。
- 首次完整构建被守卫拒绝：用户 21:49:45 启动的 `UnrealEditor.exe "D:\FPS3D\FPSGAME\FPSGAME.uproject"`（PID 103640）在运行。按项目规则没有结束该进程、也未绕过守卫，改为等待脚本 `build_when_free.ps1` 守着该进程退出。
- 用户关闭编辑器后，等待脚本自动执行完整构建：`build_editor.log`、`Saved/BuildEditor/build-20260923-220334.log`，`Result: Succeeded`，退出码 0；`[5/6] Link UnrealEditor-FPSGAME.dll`，DLL 时间戳 22:03:47 晚于本次 obj 21:58:45（该 TU 未重复编译，UBT 认为 obj 已是最新，链接仍由本轮执行）。回执见 `build_receipt.json`。
- 二进制证明：新代码里的字面量按 UTF-16LE 在 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 中命中——`PKM equip pull missing`（本轮新增的日志串）与 `/Game/Weapons/PKMLowpoly20260922/ChargeAudio35/S_PKM_%s.S_PKM_%s`（装备读取的路径格式）均为 True。
- 未运行游戏、未试听；装备音的实际音色、音量与时点由用户判断。构建完成不等于已进游戏，需重启编辑器后重新装备 PKM 才会加载新 DLL。
