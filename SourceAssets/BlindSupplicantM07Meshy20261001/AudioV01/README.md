# 盲祷者 M-07 音效 AudioV01（2026-10-06）

为盲祷者补齐本体声音体系。沿用复用优先策略：肉身层复用 M-10 已下载的 freesound CC0 预览源；念咒低语、袍料拖曳、法术辉光、鳃膜颤动全部由 `prepare_audio.py` 用 numpy 程序合成，无新增外部素材。法术命中音沿用玩家技能资产，墙拟态身份音（SW_M07_WallMimic）保留原定时器，均不在本批重做。

## 输出（`Audio/`，48 kHz 单声道）

| 资产 | 时长 | 内容与对位 |
|---|---:|---|
| S_M07_Idle | 3.4 s 循环 | 巨躯腹鸣 + 低语诵经（合成音节门控）+ 鳃膜 8 Hz 颤动 |
| S_M07_Chase | 2.3 s 循环 | 袍料拖曳 + 赤足踱步 + 庞大身位移动 |
| S_M07_Melee | 0.9 s | 爪臂挥啸 → 血肉击中（峰值 0.40 s，对位 `LeftContactTime=.47`/`RightContactTime=.50` 经 `MeleePlaybackRate=1.30` 折算 ≈0.36–0.38 s） |
| S_M07_MagicGather | 2.2 s | 诵经渐强 + 蓄能辉光，自蓄力起手播到释放被切 |
| S_M07_MagicRelease | 1.0 s | 呼气爆发 + 元素嘶啸，对位 `MagicReleaseContactTime=.30` 释放点 |
| S_M07_Hit | 0.65 s | 袍裹钝击 + 腹鸣呛声（受击表现入口同沿） |
| S_M07_Death | 2.2 s | 诵经哽断 → 低吟下沉 → 0.9 s 躯体袍料坠落 |

## 接入

- `BlindSupplicantMonster.h`：`M07|Audio` 7 个声音属性 + `IdleVoice`（挂 `head` 骨）/`ChaseVoice`（根）循环组件 + 复制的 `AudioAttackKind`（0 未定/1 近战/2 法术）与 `AudioMagicReleased`。
- 新增 `BlindSupplicantM07Audio.cpp`：`UpdateM07Audio` 在 `Tick` 轮询 `ENurseState` 边沿——Attack 边沿按 kind 分流：authority 直接读 `IsMagicAttack`，专用服客户端读复制 kind；kind 未到先挂起 0.6 s 等待。法术蓄力音挂掌位随动，释放翻边（`bMagicReleaseStarted||AudioMagicReleased`）切放 Release 并停蓄力。Stagger→Hit、Dead→Death。Idle 仅 Idle 状态、Chase 按速度门控。专用服务器全跳过；`EndPlay` 停全部。
- 复制补洞：`PrepareAttack` 写 `AudioAttackKind`，释放翻转点写 `AudioMagicReleased`，`GetLifetimeReplicatedProps` 注册——法术分流在专用服客户端同样成立。

## 管线

1. `python prepare_audio.py` — 生成 WAV + `Records/audio_source.json`（逐源 freesound 链接与 CC0 声明）。
2. `finish_production.ps1` — 互斥等待 → 双 target 构建 → `import_audio.py` 导入 `Audio/AudioV1`（Idle/Chase 置 looping、FORCE_INLINE）→ 写 `BP_BlindSupplicantM07` CDO 七引用 → 回执。

## 状态

C++ 与脚本已完成，制作/导入状态见 `delivery.json`。未做运行或验收测试，游戏内试听从用户处确认。
