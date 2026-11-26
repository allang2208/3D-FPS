# 龙息喷焰音效（AslakHostaker，2026-10-19）

用户试听后选择 AslakHostaker 的 `Flamethrower_Weapon_Long_Bursts.wav`。来源为 <https://freesound.org/people/AslakHostaker/sounds/395039/>，作者标注 CC0。使用与用户试听一致的官方 HQ MP3；原始 WAV 下载需要 Freesound 登录，本批没有取得原始 WAV。

## 音频制作

源文件、来源页面、配方、旧源码备份在 `SourceAssets/DragonBreathAudio20261019/`。只使用第一次长喷射，保留音高、速度及喷焰质感，不添加其他声源或 EQ。

| 角色 | 来源秒段 | 成品长度 | 播放 |
|---|---|---|---|
| Start | 2.305–2.855 | 0.55 秒 | 去掉长静音，在实际喷焰开始时播放 |
| Loop | 3.25–7.50 | 4.00 秒 | 250 ms 等功率接缝，持续喷焰循环 |
| Stop | 12.90–13.35 | 0.45 秒 | 停止喷焰时播放收尾 |

三段采用同一固定增益，样本峰值限制到 -3 dBFS 以内，48 kHz 单声道 PCM24。具体增益和 SHA256 见 `provenance.json`。资产目录为 `/Game/Skills/DragonBreath20261013/Audio20261019`，仅 Loop 开启循环及静音虚拟化，三段均为 PCM / ForceInline。

## 运行接入

- 复用 `FPSFireMagicComponent` 的现有施法状态和 Tick；`FPSDragonBreathAudio.cpp` 持有每个施法者三个可复用声音组件，不新增定时器或 RPC。
- 起喷接替旧通用 `CastSound` 在龙息中的播放；其他火系法术继续使用旧声音。
- `CastId` 去重，预测与复制回执不重复起喷。晚加载／晚相关只恢复当前剩余喷焰，不补播过期起喷；循环偏移使用实际 SoundWave 长度，避免无限循环时长哨兵影响取模。
- 本地施法者使用非空间播放，远端音源跟随实际喷口并使用距离衰减。音频组件音量为 0.85；起喷与循环以 0.4 秒淡入过渡，停止时循环用 0.12 秒淡出并播放收尾。
- 取消、持续时间结束、换武器或失控沿原龙息状态终止；死亡及 EndPlay 显式停止并销毁全部音频组件。伤害、资源、动作和流体特效规则保持现有实现。
- 三个声音加入 `PlayerSkillAssets` 的龙息准备列表及 `LoadDragonBreath` 异步请求；目录列入 `DefaultGame.ini` 的打包清单。

## 状态

三段 SoundWave 已由后台 commandlet 导入并保存，退出码 0；保存回执为 `SourceAssets/DragonBreathAudio20261019/import-receipt.json`（complete=true），日志为 `Saved/DragonBreathAudio20261019/import-commandlet-02.log`。

- `FPSGAMEEditor Win64 Development`：常规构建成功，基础 `UnrealEditor-FPSGAME.dll` 已链接落盘，577.39 秒；日志 `Saved/DragonBreathAudio20261019/FPSGAMEEditor-build-01.log`。
- `FPSGAME Win64 Development`：构建成功，`Binaries/Win64/FPSGAME.exe` 已链接落盘，98.34 秒；日志 `Saved/DragonBreathAudio20261019/FPSGAME-build-01.log`。
- 构建回执：`SourceAssets/DragonBreathAudio20261019/build-receipt.json`。

未运行游戏、试听或联机测试，最终听感及音画同步由用户确认。
