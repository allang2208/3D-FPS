# 武器命中音效替换（2026-09-16）

用户指定音效源：`D:\FPS3D\资产\音效\quickhit.mp3` 与 `D:\FPS3D\资产\音效\gunhit.mp3`
（用户提供，来源与授权由其掌握；本目录只做格式转换与导入，不再分发）。

## 处理

1. 用 `imageio_ffmpeg` 转成工程惯用的 **44.1 kHz / 立体声 / 16-bit PCM WAV**：
   `S_MeleeHit_Quick.wav`（源 quickhit，0.39 s）、`S_GunHit.wav`（源 gunhit，0.30 s）。
   转换命令：`ffmpeg -i <mp3> -ar 44100 -c:a pcm_s16le <wav>`。
2. `import_hit_audio.py` 导入为 SoundWave（`LoadingBehavior = FORCE_INLINE`，短促单次音避免首击 pops）：
   - `/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick`
   - `/Game/Audio/WeaponHit20260916/S_GunHit`
3. 接线（只有柄尾这一招与枪械击中目标被改动）：
   - **第四段柄尾配重砸击**：`URuneSwordComponent` 新增 `PommelHitSound`（指向 `S_MeleeHit_Quick`），
     在砸出瞬间替换共用的剑挥动声；命中点不再叠加第二个音。斩一/斩二/突刺/蓄力重击的挥动声与命中音
     全部保持原样（物品 `hit_sound` 已回退成 `Sword_Hit`）。
   - **枪械击中目标**：`UFPSImpactFXSubsystem` 对 Flesh 表面（怪物躯体）改用 `S_GunHit`，
     替代原来的通用血肉撞击音；枪械不再叠加共用的怪物命中确认音，近战与技能保持原确认音。
   - **击杀也要出声**：`RuneSwordComponent::SweepBlade` 里近战命中音原先写在 `Applied>0` 分支内，
     改成「本次接触有效（造成伤害 **或** 目标因这一击死亡）」就播放，因此致命一击也有命中音。

入口：`import_hit_audio.py` + `run_import.ps1`（编辑器关闭时的 ImportHost 路线）；
编辑器开着且不在 PIE 时用 `python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/WeaponHitAudio20260916/import_hit_audio.py`。

状态：音频已导入，代码与物品数据已改，随本轮一起构建。未做游戏内听感验收，声压、时长与触发时机由用户试听判定。
