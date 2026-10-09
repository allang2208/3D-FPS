# Super90 使用 gamedev 现行音效

用户指定用 E 盘 gamedev 的 Super90 音效替换 UE 当前音效。源工程为 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`，读取当前 `src/ui/equip-data-manager.js` 的 `SUPER90_ITEM`，以及 `src/config/gun-ammo.js`、`src/entities/player/subsystems.js` 的装备与逐发换弹收尾回退，采用正在使用的音源。

| 用途 | gamedev 原文件 | UE 资产 |
| --- | --- | --- |
| 开火 | `assets/sounds/weapons/gunshot_600ms_clean.wav` | `/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_Fire` |
| 逐发装填 | `assets/sounds/weapons/Super90-reload.mp3` | `/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_Reload` |
| 装备 / 枪机收尾 | `assets/sounds/weapons/bolt_pull_1s_clean.wav` | `/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_Bolt` |

两份 WAV 原样复制；MP3 浮点解码后转换为 44.1 kHz 双声道 PCM16，实际增益 1.0，没有裁切、滤波或改变音高。三份时长分别为 0.600、0.384、1.000 秒。使用 PCM / ForceInline，继承当前对应音效的音量、音高和声音类别。

`FPSGAMECharacter.cpp` 为 Super90 独立绑定这套声音，普通枪声不再被旧 Mossberg 三变体数组覆盖；逐发装填与空仓枪机释放仍使用现有连续换弹接触时钟。其他武器继续使用原音源。共用空击和命中反馈没有 gamedev Super90 专用对应文件，保持现有引用；此次没有另制消音声。

配置已加入新声音目录的 cook 根，整枪恢复入口 `SourceAssets/BenelliM4Super9020261006/import_super90.py` 同步调用本次音效导入脚本。源 WAV/MP3、本机副本、散列、转换方式和实际 UE 保存回执位于 `SourceAssets/Super90GameDevAudio20261007/`。本次复用用户指定的既有项目资产，旧 Mossberg CC0 来源声明不套用到这三份素材，未发布或分发音源。

交付状态：三份 SoundWave 已实际导入并保存；音效路由及装备单发音在现有编辑器中 Live Coding 成功，日志为 `Saved/Logs/FPSGAME.log` 的 `2026.10.07-01.53.22:998` 完成项。编辑器保持运行，未执行覆盖基础 DLL 的常规 Editor 构建；后续正常关闭编辑器后仍需常规构建以更新基础二进制。没有启动编辑器、试听或运行游戏测试。已有角色会在下一次加载/重新装备该武器时取得新声音绑定。
