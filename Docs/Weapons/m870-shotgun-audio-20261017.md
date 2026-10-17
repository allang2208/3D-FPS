# M870 普通开火与霰弹枪共用消音声

2026-10-17 用户选定 SoundMorph / Charles Maynes 的 `Remington 870 Single Shot Exterior Open 02`（候选 B）作为 M870 普通开火，同时指定此前 M870 的开火声用于霰弹枪消音器，包含 Super90。

## 最终资源选择

| 用途 | 保留的运行路径 | 内容 |
| --- | --- | --- |
| M870 普通开火 | `/Game/Weapons/M870/Tactical20261015/Audio/S_M870_Fire` | 用户选定的候选 B |
| 霰弹枪共用消音声 | `/Game/Weapons/CommonShotgun/Suppressor20261015/Audio/S_Super90_Suppressed` | 替换前 M870 SoundWave 导出的原始音频，独立冻结 |
| Super90 普通开火 | 原 `Super90/GameDevAudio20261007/S_Super90_Fire` | 保持原内容 |

旧 M870 的来源记录是工程保留的 CC0 Mossberg 录音。本次按用户指定直接复用声音，不额外滤波、降低音量、改变音高或裁切，也不称其为实录消音 M870。以实际加载的旧 SoundWave 导出结果作为冻结输入，避免今后修改 M870 普通声时连带改变消音声。

B 的来源为 [Pro Sound Effects 上的 SoundMorph / Charles Maynes 音效页面](https://www.prosoundeffects.com/sound-effects/PSE_SMPH-INTR/Syi45/Remington-870-Single-Shot-Exterior-Open-02)。当前本机输入是用户试听并选定的官网 OGG 预览，尚未取得授权原版 WAV；按用户选择接入本机迭代，不能标记为已授权生产素材或继承旧源的 CC0。保留全段和原音高，仅从浮点解码重采样为 48 kHz PCM24，并用双声道统一增益避免整数转换削波。无 EQ、额外压缩或时间伸缩。具体源散列、增益和输出信息见制作配方。

## 播放路径与范围

- `LoadAKMSound` 对 M870 的 Fire 角色解析到上述普通声；Super90 保留自己的普通声。
- `IsTubeShotgunWeapon()` 初始化将本枪普通声放入普通数组，将共用消音声同时赋给 `SuppressedFireSound` 与消音数组。每次装备/切枪重置数组，不让旧枪覆盖新引用。
- Super90 消音器装配同样读取该共用声音。当前枪匠数据中可装该霰弹枪消音器的是 Super90，M870 的枪口选项仍仅为 `false`；本次替换共用声音，不新增 M870 配件或改变其外观/装配能力。
- 第三人称/远端 `DescribeGun` 登记普通/消音指针和变体数组，管式霰弹枪开火表现按 `bSuppressed` 选择相应指针。复用既有网络协议。
- 现有 cook 根覆盖两个包。未改枪械数值、开火/泵动/换弹时钟或普通 Super90 音效。

## 制作与恢复

目录：`SourceAssets/ShotgunAudioSwap20261017/`。

- `Before/`：修改前两份 SoundWave、旧作者/导入脚本、WAV 和来源记录。
- `snapshot_audio.py`：只执行一次，导出替换前实际 M870 音频和播放设置，然后在同一 UE 接入批次中制作、导入两份声音。
- `Frozen/S_M870_PreSwapFire.wav` 与 `snapshot.json`：不可用新 M870 音效覆盖的固定消音输入。
- `prepare_audio.py`：从冻结输入和候选 B 重建，并同步旧整枪/消音器制作目录。
- `import_audio.py`：按先消音、后普通的顺序导入保存；也可仅更新指定角色。
- `provenance.json`、`import-receipt.json`：制作参数、权利区分和实际保存回执。

M870 整枪作者入口已改读新普通声；Super90 消音作者入口改为复制冻结旧 M870，消音导入入口委托当前配方，避免旧滤波脚本把声音改回去。

本次只有音频资产和 Python 制作配方变化，运行路径与 C++ 不变，无需为声音替换重新编译原生模块。

## 实际保存结果

两份 SoundWave 均已实际导入并保存。`import-receipt.json` 为 `revision=ShotgunAudioSwap_20261017`、`complete=true`，先保存共用消音声，再保存 M870 普通声；两者 volume=1、pitch=1、PCM/ForceInline，沿用原 M870 播放设置。

最后一轮无界面 commandlet 退出码 0，日志为 `Saved/ShotgunAudioSwap20261017/snapshot-install-commandlet-05.log`。早期编辑器排队没有完成写入；首次后台导出后，元数据的 Name 键不能直接 JSON 序列化，修正为字符串后从未被覆盖的旧 M870 重新导出并完成全部步骤。其他正在运行的后台任务经限定范围读取确认仅采样动画骨骼、不读写声音，实际音频保存与其资源范围无冲突；没有关闭编辑器或中止其他任务。

未主动试听、运行游戏或进行联机验收。用户选定的 B 仍是官方试听压缩源，正式发布前需取得授权原版。
