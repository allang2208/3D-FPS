# 201 直接复用当前 PKM 换弹声音

2026-09-28。按用户反馈排查换弹旧音源及尾音，后台修改并常规构建，不启动交互编辑器或游戏。

## 排查结果

- 弹箱换弹此前已使用 PKM 的 ReloadAudio22 六个接触音和 ChargeAudio35 四个拉栓接触音。不能把文件夹名 Audio22 当作音频仍是旧版的证据。
- 通过后台 commandlet 读取现用 SoundWave 并导出其 PCM：CoverOpen、CoverClose 的采样内容与 `BeltAudio22/rebuild/*_rebuilt_delivered.wav` 一致，与原始未修尾音 WAV 不同。这确认的是保存资产内容，不是用户听到的具体尾音来源。
- PKM 与 201 的两条弹箱换弹动画均没有额外 AnimNotify。`current_audio.json` 保留时长、通知、SoundWave 设置和导入来源；`CurrentPKM/` 是现用资产导出的 PCM，仅用于本次定位。
- 确认存在的引用差异：201 普通弹匣、装备拉栓的通用音效仍来自 AKM/VideoAudio20260921；弹箱接触音加载失败也会使用这些 AKM 音源。现有日志没有发现 PKM 接触音加载失败，不能断言用户本次听到了回退声音。
- 201 弹箱空仓换弹最后一个接触原先没有 PKM 的 1.25 倍接触音量。

## 已修改

仅修改 `Source/FPSGAME/FPSGAMECharacter.cpp` 的声音引用与接触音量。

- PKM 与 201 弹箱使用同一个 `PKMReloadAudio::LoadContact`，直接加载现用 PKM SoundWave。缺失时记录具体路径，不再播放 AKM 回退声音。
- 201 普通弹匣换弹：拆卸、插入、到位分别直接引用 PKM 当前 BoxOut、BoxInsert、BeltSeat；保留 201 自己的动作接触时刻。
- 201 普通空仓与装备拉栓直接引用当前 ChargeRearStop、ChargeFrontStop。弹箱仍使用完整四段拉栓声音及 PKM 时钟。
- 201 最后到位声与 PKM 使用同一 1.25 倍接触增益；现有播放组件保持 pitch 1.0。
- 直接引用共享资产，没有复制、重新裁切、重制或覆盖已认可的 PKM 音频。开盖和合盖采样本轮没有修改。

## 落盘状态

`Before/FPSGAMECharacter.cpp` 保存本轮修改前源码。`build_console.log` 记录常规后台构建，退出码 0，`Result: Succeeded`；正式 `UnrealEditor-FPSGAME.dll` 已重新链接，构建日志为 `Saved/BuildEditor/build-20260928-135427.log`。

没有运行 PIE、游戏回归或试听验收。旧音源入口和音量差异已修改；用户描述的弹箱尾音是否仍存在，仍需用户试听确认。本轮不把资产采样比对或编译成功表述为听感验收通过。
