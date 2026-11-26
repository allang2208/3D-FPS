# M16 消音开火声修订

用户要求按此前枪械音效经验重新处理 M16 装消音器后的开火声。

## 当前版本：V2（根据“太尖锐、没有消音特征”反馈重做）

用户试听 V1 后否定其消音音色。V2 保持四个既有资产路径与声音绑定，直接更新 SoundWave 内容，不改 C++ 或普通 M16 开火声。

- 撤掉 V1 的 2200–8000 Hz 高频旁路，主体由约 3.3–3.5 kHz 二阶低通改为 1420–1580 Hz 四阶低通，只留下少量 750–1400 Hz 机械质感。
- 软化前 6 ms 尖峰，保留低中频主体；30 ms 后以 50 ms 时间常数收尾，文件由 525.167 ms 收至 320 ms，适配现有三连发间隔。
- 撤掉“消音声必须补齐普通声 K 加权能量”的目标。前 100 ms RMS 设为普通声低 1.5 dB，K 加权能量仅记录，最终约低 2.87–2.91 dB；运行时声音音量和音高设置仍保持原值。
- 主处理后增加 1800 Hz 四阶低通，避免软限幅产生的高频重新露出；采样峰值保持 −2 dBFS。指标仅用于音频制作，不代替试听结论。
- 源仍是用户的 M16 MP3，保持浮点解码、原音高、双声道、26.833 ms 预卷裁切及原来源权利。本版仍是衍生设计音色，不是实录消音 M16。

V1 的脚本、来源记录、WAV、四个 SoundWave 及原交付记录已完整复制到 `SourceAssets/M16SuppressedAudio20261015/History/V1`，没有回退或删除其他任务文件。

V2 四个声音已通过现有编辑器桥导入并保存：`Saved/M16SuppressedAudio20261015/import-v2-02.json` 返回 `success=True`，保存回执为 `revision=M16SuppressedV2_20261015`、`complete=true`，包含四个正式 SoundWave，volume=1、pitch=1、PCM/ForceInline。首轮仅因互斥窗口忙而排队超时，未发送写入；第二轮成功完成，没有启动或关闭编辑器。

本轮只更新既有声音内容和制作配方，没有 C++ 变化，不需要为这次音色修订重新编译原生代码。没有试听或运行游戏；由用户确认实际消音特征。

以下记录为 V1 的历史制作与接入经过，**不代表 V2 听感已经通过**。

## V1 历史播放来源与修改

此前普通开火走用户选定的 `S_M16_OriginalFire`，消音四变体却走 `FreeFirearmAudio20260913/S_M4_Suppressed_01..04`，没有使用 M16 原声。射击逻辑优先选择变体数组，所以仅替换 `SuppressedFireSound` 单发引用不能完成修改。

本轮从用户的 M16 MP3 原声加工四份独立消音版本，输出到 `/Game/Weapons/M16A2/SuppressedAudio20261015/S_M16_Suppressed_01..04`。

- 使用浮点解码输入；原 MP3 峰值约 1.434，旧 PCM16 转换已将超过上限的采样削平，本轮避免继承该转换损失。
- 移除约 26.833 ms 空白预卷，四份均为 48 kHz 双声道、525.167 ms，保留音高。
- 收敛尖锐爆音、减弱 320～850 Hz 箱体感，保留原音低频主体及高频机械纹理。尾部按现有 80 ms 三连发间隔收敛，不新增规则音调或长回声。
- 按原普通声前 100 ms 的能量补偿滤波；输出加权能量与参考相同，RMS 约高 0.62～0.69 dB，源峰值约 −1 dBFS。这是制作参数，不是试听或实机响度结论。
- SoundWave 沿用正常 M16 的音量、音高和 SoundClass，运行时播放增益不变；PCM/ForceInline 避免短起音依赖流送。

`M16WeaponAssets.h` 集中维护专属声音路径，装备初始化同时更新单发和四变体，枪口刷新在共享消音器提前返回前明确绑定 M16 声音。普通消音器、战术消音器及共享多口径消音器均沿用该分支。保留既有六声部尾音重叠、相邻变体不重复及原三连发时钟。

第三人称/远端表现已有 `GunSounds` 收集和 Shot 音源事件，包含本轮四变体；本轮沿用此路径，没有新增网络消息。`/Game/Weapons/M16A2` 已在 cook 根中，未改并行工作中的打包配置。

M16 普通开火、换弹和其他枪型声音均保留。制作和导入脚本位于 `SourceAssets/M16SuppressedAudio20261015`，来源、散列、参数在 `provenance.json`。原音源授权沿用用户提供素材的本机使用范围，不公开再分发音频。

## 接入记录

首次在已有编辑器内导入时正处于 PIE，第一份 SoundWave 创建后被 UE 拒绝保存，未将此记为接入完成。随后编辑器已自行退出，本任务转为后台常规构建和无界面导入，没有启动交互编辑器或游戏。后台操作先完成该新包的元数据与保存，再导入全部四份正式声音。

- 四份 SoundWave 已实际保存，`SourceAssets/M16SuppressedAudio20261015/import-receipt.json` 的 `complete=true`，每份记录 volume=1、pitch=1、PCM/ForceInline。
- 导入 commandlet 退出码 0，日志记录 `Python script executed successfully`、`Success - 0 error(s), 5 warning(s)`；五条为已有 Python 工具命名警告。日志位于 `Saved/M16SuppressedAudio20261015/import-commandlet.log`。
- 常规 `FPSGAMEEditor` Win64 Development 构建成功，96.13 秒，已链接基础 DLL；`FPSGAME` Win64 Development 构建成功，97.92 秒。日志分别为同目录 `build-editor.log`、`build-game.log`。
- 本轮原生修改限于 `FPSGAMECharacter.cpp`、`M4MuzzleVisual.cpp` 和 `M16WeaponAssets.h`。修改前文件已保存在同目录 `Before`；共享工程其他在途修改保留。基础产物已更新，本轮不依赖 Live Coding 补丁生效。

未试听、未启动游戏、未做运行或联机测试，最终听感由用户确认。
