# M16 action mechanics source

本次公开发布仅包含 CC0 机械音及其编辑器；游戏原有开火声和本地组合模型不在本次发布范围。

## 2026-09-06 装备与换弹机械音

- 作者：wadaltmon；作品：AR15 Various Sounds；2015-02-07。
- 来源：https://freesound.org/people/wadaltmon/sounds/263513/
- 许可：CC0 1.0，https://creativecommons.org/publicdomain/zero/1.0/ 。作者明确记录使用 AR-15、Blue Snowball 和 Audacity 录制。
- 使用同平台机械录音作为 M16A2 游戏音效参考，不宣称来自 M16A2 专机实录。
- 获取：页面公开提供的 HQ MP3 试听版本 https://cdn.freesound.org/previews/263/263513_4675419-hq.mp3 ，保留在 `source/263513_4675419-hq.mp3`；115384 字节、44100 Hz、双声道、解码时长 4.85297 秒。未下载需要登录的原始 WAV。
- 页面许可摘录：“You can copy, modify, distribute and perform the sound, even for commercial purposes”。已查验日期：2026-09-06。
- 编辑器：`tools/m16/prepare_mechanics_audio.py`。从同一录音截取弹匣拔出、插入、压实、拉机柄后拉、释放和枪机释放六段；合并为单声道，80–12000 Hz 滤波，2 ms 淡入 / 15 ms 淡出，峰值 -6 至 -10.46 dBFS；输出 44100 Hz / 16-bit PCM WAV。未改变音高或整体变速。
- 游戏：`scripts/m16_action_audio.gd` 按 M16 动作时间轴触发六个短声，播放走 SFX 总线、-4 dB。详细裁切范围和响度见 `mechanics/edit-report.json`。
- `weapon_data/m16.tres` 已移除 HK416 装备和换弹音引用；开火音保留原用户素材。
- 未选用 GFL7 的 m4a1 or m16 reload sound（276964）：页面评论提出游戏素材来源疑问；未选用 maurosama 的 Cocking M16（133814）：作者说明为多种枪声拼接的舞台音效。所选 wadaltmon 录音有明确录制说明和完整分段说明。
