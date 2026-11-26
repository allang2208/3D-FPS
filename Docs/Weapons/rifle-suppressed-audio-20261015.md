# M4、AKM、A762 消音开火调整（2026-10-15）

用户要求继续逐枪检查并优化三把枪的消音开火。按现用源制作独立消音版本，后台接入、构建与保存；不启动编辑器界面或游戏，不自动试听。

## 检查发现与处理

| 枪械 | 原路径问题 | 本次处理 |
| --- | --- | --- |
| M4 | 旧四变体继承约 40 ms 起音预卷、低频比例较重；声库同时供其他枪使用 | 独立新库，裁掉 38.292 ms 预卷，500 ms 输出，减轻闷响并收尾；保留旧库供其他枪使用 |
| AKM | 只有一份消音单发；装备和枪口装配分别写入旧指针，未接入四变体播放 | 本枪视频源浮点重制四变体，395 ms；保留主体并减少箱体感，装备与枪口均绑定新库 |
| A762 | 普通声共用当前 AKM 视频单发，消音却用旧 `M4MuzzlesV1`；装配会无条件覆盖指针 | 按现用普通源独立制作四变体，395 ms、更短衰减；移除该枪装配分支的旧 M4 覆盖 |

M4 普通四变体、AKM/A762 普通单发均保持原引用。三枪各四个消音声音，运行时音量和音高不变；补偿依据为起音对齐的 100 ms RMS 与 K 加权能量，不是主观等响验收。A762 音色仍源自现有 AKM 共用普通声，不是独立录音。

## 路径覆盖

- 装备/切枪：`FPSGAMECharacter.cpp` 重置变体数组并按武器定义加载独立库，单发指针同步设置，M4 的旧通用数组不再覆盖新库。
- 枪口：`M4MuzzleVisual.cpp` 在普通、战术、多口径分支及“已安装”提前返回之前绑定本枪单发；A762/AKM 后续分支不再覆盖成旧声音。
- 开火：沿用 `IsMuzzleSuppressed()` 选择普通或消音库，四变体不相邻重复，最多六声部并保留短尾，20 ms 抢占淡出；不更改射击时钟。
- 第三人称与远端：现有 `FPSPlayerBodyGunEffects.cpp` 的 `DescribeGun` 登记普通/消音指针和两个变体数组，`ReportGunShot` 传递选中声音；本次无需改变网络数据结构。仅完成代码路径检查，未运行联机验收。
- 烹饪：`DefaultGame.ini` 包含 `/Game/Weapons/RifleSuppressedAudio20261015`。未运行打包。

## 文件与生产记录

- 可复现制作/导入：`SourceAssets/RifleSuppressedAudio20261015/author_audio.py`、`import_audio.py`。
- 源、精确片段、版权继承、处理参数、输入/输出 SHA-256：同目录 `provenance.json`。
- SoundWave 保存回执：同目录 `import-receipt.json`。
- 独立路径映射：`Source/FPSGAME/Weapons/RifleSuppressedAudioAssets.h`。
- 后台构建与导入日志：`Saved/RifleSuppressedAudio20261015/`。

## 实际交付状态

- **已制作并保存：** 12 份 PCM24 WAV 和来源配方；后台 Python commandlet 退出码 0，`import-receipt.json` 为 `complete: true`，M4 / AKM / A762 各保存四个 SoundWave。三组资产音量、音高均为 1，继承各自普通声设置。
- **源码已接入：** 独立路径映射、装备单发/数组选择、枪口装配绑定与 cook 包含项均已落盘。
- **整体构建未完成：** 本轮 Editor 首次构建（108.64 s）报 `HeQueMonster` 生成反射代码与当前声明不一致；强制重新生成反射后的重试（6.35 s）报 `M66IncineratorMonster.h:107` 找不到 `UM66FurnaceVisualComponent`。后续 Game 构建（220.42 s）越过反射阶段，但仍失败于下列其他模块的当前编译错误。没有修改这些任务的源文件，也没有关闭外部打开的编辑器。

| 本轮 Game 构建阻塞 | 日志位置及错误 |
| --- | --- |
| `Monsters/HeQueRiftPresentation.cpp` | 第 45 行，C4458：局部 `Mesh` 隐藏类成员 |
| `Production/ProductionBluntAuthority.cpp` | 第 172 行起，C2039：`ClientBluntStaminaSpent_Implementation` 与组件声明不匹配，并产生后续成员查找错误 |
| `Production/WarhammerModificationAuditCommandlet.cpp` | 第 170 行，C2039 / C2672：对 `TSharedRef` 调用 `ToSharedRef`，序列化重载不匹配 |

构建日志反映各次执行当时的共享源码状态，其他任务后续可能已继续修改。新资产已经存在于 Content，但本轮没有完成包含新声音路由的 Editor DLL / Game EXE 链接，不能声称当前游戏已经切换至新声库。待这些阻塞处理后，需要正常完成 Editor/Game 构建。

未试听、未运行游戏或联机，也未做打包验收。完整构建完成后，由用户体验实际听感。
