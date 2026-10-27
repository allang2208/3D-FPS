# 穿心箭正式选定出箭声 H

**2026-10-27 23:32 更新：BalancedV4 已通过最小声音宿主的后台 commandlet 实际保存，退出码 0，import-receipt.json 为 H / BalancedV4。** 源 SHA-256：0e839fe2900c76c0161558165451adb3d32efc6ffc60a7814dfb1a2f7525c959。未播放、未重新打包；听感仍由用户确认。此前的等待超时段落为历史记录。CombinedV3 作者/试听与本目录 History 已归档至 trash/bow-skills-retired-20261027/ 下同名原路径；当前 E/F/G 输入和 BalancedV4 仍保留。

导入注意：先拒绝正在 Play 或同资产未保存的交互编辑器；commandlet 不能调用 LevelEditorSubsystem.is_in_play_in_editor()，即使返回的子系统对象非空，也可能因交互模块未初始化而崩溃。脚本按 -run=pythonscript 区分该模式。正式后台入口仍可使用 reimport_when_idle.ps1；最小宿主恢复只需 PythonScriptPlugin、EditorScriptingUtilities 和指向正式 Content 的联接，再运行本目录 import_audio.py。共享 Content 操作持有现有 UE 批次互斥，不打开第二个交互编辑器。

用户在试听 E+F+G 三合一版本后明确要求接入游戏，随后反馈 G 的末段过大，要求平衡并加入 E/F 细节。当前 S_HeartPiercingArrow_Release.wav 为 BalancedV4：48 kHz、24 bit、双声道、0.86 秒，不包含试听版的二次重复或间隔。selection.json 保存修改要求及源散列，听感尚未获用户认可。

BalancedV4 恢复 E/F 更完整的频段，G 权重从 1.30 降为 0.38，并在 65–240 ms 淡出。原 1.03 秒 CombinedV3 单发、选择与保存回执保留在 History/CombinedV3。重导入时沿用相同资产路径，当前实际保存版本以 import-receipt.json 的 candidate 为准。reimport_when_idle.ps1 等待运行中的编辑器、Cook 或构建结束后，仅重导入该声音；不运行测试或重新编译 C++。

## 播放接入

目标 SoundWave：/Game/Skills/HeartPiercingArrow/Audio20261026/S_HeartPiercingArrow_Release。

BowWeaponComponent 沿现有装备资源批次异步加载并通过 LoadHandle 保留。LooseArrow 经过现有资源检查且完成箭支生成／网络射击请求后，以本箭的 bPiercing 选择专属声音。穿心箭固定音高 1，播放乘数沿用普通出箭的 0.6，不再叠播普通箭声；普通箭原声音及音高逻辑保留。取消拉弓、未实际发射的失败路径不播放出箭音，红色就绪本身不触发声音。音效缺失沿用原普通释放声，不在射击时同步加载。

联机沿用既有本地拥有者预测出箭反馈；没有新增远端声音广播或改变服务端伤害判定。客户端仍可能在服务器拒绝前已播放一次预测音，与既有普通箭反馈合同一致。

Config/DefaultGame.ini 加入该音频目录的 AlwaysCook。import_audio.py 导入并保存单个 SoundWave，固定 PCM、ForceInline、volume=1、pitch=1、非循环；保存结果记录在 import-receipt.json。必要的 Editor / Game 构建使用 build.ps1，日志位于 Saved/HeartPiercingArrowAudio20261026。

## 来源与恢复

沿用 StrongV2/README.md 的 CC0 源：artisticdude 的 Battle Sound Effects 弓／风切声，与 Ben Jaszczak、Brian Nelson / Still North Media 的 English Longbow Shoot；低频与压力层为作者脚本合成。https://creativecommons.org/publicdomain/zero/1.0/

当前作者链：StrongV2/author_strong_candidates.py → StrongV2/BalancedV4/rebalance_efg.py → 本目录选定 WAV → import_audio.py。首版 CombinedV3/combine_efg.py 与原始文件、配方、源散列和许可均保留。恢复当前资产优先直接导入本目录 WAV。

未运行游戏、试听验收、自动测试或截图。资产保存及原生构建状态以各自回执为准。

## 本次交付结果

CombinedV3 首版于 2026-10-26 无界面导入完成，保存回执返回 saved=true；该历史 WAV 的 SHA-256 为 72c3ee4d164e78e77f3ffad1eb9423102d6ce4d82cb187d29b13970c94707ad3。FPSGAMEEditor Win64 Development 构建成功（466.01 秒），FPSGAME Win64 Development 构建成功（50.48 秒）。未启动交互编辑器或游戏，实际游戏听感未测试。BalancedV4 沿用这份播放代码，音色调整不需要额外构建。

BalancedV4 音源与导入脚本已保存，但本次重导入等待 1200 秒后超时退出；随后仍有 FPSGAME BuildCookRun / Cook 进程占用项目。没有终止或干扰该打包，也没有启动第二个 UE 进程覆盖资产。当前 import-receipt.json 仍为 H / CombinedV3，游戏资产尚未更新至 BalancedV4。等待脚本现已停止；占用释放后需要重新执行 reimport_when_idle.ps1，完成保存后才算本版接入。未运行游戏测试。
