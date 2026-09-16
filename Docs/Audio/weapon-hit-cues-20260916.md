# 武器命中音效：近战与枪械区分（2026-09-16）

用户指定替换：近战攻击的命中音用 `D:\FPS3D\资产\音效\quickhit.mp3`，枪械击中目标的音效用同目录
`gunhit.mp3`，并要求近战武器的命中音在**本次攻击击杀怪物时也照常播放**。

## 资源

- 源：用户提供的两个 mp3（授权与来源由用户掌握，本仓库只做转换与导入，不再分发）。
- 转换：`imageio_ffmpeg` → 44.1 kHz / 立体声 / 16-bit PCM WAV（工程惯用格式）。
- 导入：`/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick`（0.384 s）与 `S_GunHit`（0.288 s），
  均设 `LoadingBehavior = FORCE_INLINE`（短促单次音，避免首击 pop）。
- 入口：`SourceAssets/WeaponHitAudio20260916/`（转换脚本用法、`import_hit_audio.py`、`run_import.ps1`、回执）。

## 接线

| 场景 | 时机 | 之前 | 现在 |
| --- | --- | --- | --- |
| 第四段「柄尾配重砸击」 | 砸出瞬间（0.84 s） | 共用 `Sword_Swing` + `S_Sword_Attack` 挥动声 | **`S_MeleeHit_Quick`**，且这一招不再在命中点叠加第二个音 |
| 斩一 / 斩二 / 突刺 / 蓄力重击 | 起手 | `Sword_Swing` + `S_Sword_Attack` | **不变** |
| 斩一 / 斩二 / 突刺 / 蓄力重击 | 命中点 | 物品 `hit_sound` = `Sword_Hit` | **不变**（击杀也播；判定已从伤害返回值里拆出） |
| 枪械击中目标（子弹落在怪物身上） | 命中点 | 该物体表面的 `S_Impact_Flesh_*`（通用血肉撞击音） | **`S_GunHit`**（`UFPSImpactFXSubsystem` 对 Flesh 表面改用枪械命中音） |
| 近战与冷钢技能击中确认 | 命中瞬间 2D | `S_Player_MonsterHit` | **不变**；枪械不再叠加这条确认音（避免同一个 gunhit 播两次） |

实现位置：

- `URuneSwordComponent` 新增 `PommelHitSound`（`/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick`）。
  挥动/砸出提示（`bSwingCuePlayed` 分支）在 `bPommelAttack` 时播它、不再播共用的剑挥动声；
  `SweepBlade` 里第四段也不再单独播命中点音（否则同一下会响两次）。其它近战完全不变。
  近战命中音判定同时从伤害返回值里拆出来，改为 `(Applied>0.f || Combat->IsDead())`，致命一击同样出声。
- `UFPSImpactFXSubsystem` 对 `EFPSImpactSurface::Flesh` 改用 `S_GunHit`（音量 0.85，仍走限频与声部池，
  连发不会叠爆）；`AFPSGAMECharacter::NotifyConfirmedWeaponHit` 增加 `bFirearmHit`，
  枪械不再叠加共用确认音，近战与技能保持原样。

武器原有的挥砍声（`Sword_Swing` + `S_Sword_Attack`）三类近战共用，本轮没有改动；
第四段已单独使用 quickhit。若更希望 quickhit 挂在「命中点」而不是「砸出瞬间」，
把 `PommelHitSound` 从挥动分支移回 `SweepBlade` 即可（两处都在同一文件里）。

本轮未做游戏内听感验收：声压、时长、触发时机与枪/近战区分度由用户试听判定。
