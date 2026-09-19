# 手枪快速进战起手音（S_QuickCombatSwing，2026-09-18）

用户指定音效源：`D:\FPS3D\资产\音效\quickhit2.mp3`（用户提供，来源与授权由其掌握；
本目录只做格式转换与导入，不再分发原始 mp3）。

用途：**手枪快速近战（握把砸击）的起手/释放音**（动作起手那一下的挥动层）。
用户 2026-09-18 澄清：quickhit2.mp3 要接的是"释放快速近战"的起手音，不是命中音；
首轮误接到命中音的部分已按本次澄清改正。

## 处理

1. `convert_source.py`（`imageio_ffmpeg`）转成工程惯用格式 **44.1 kHz / 立体声 / 16-bit PCM WAV**：
   `S_QuickCombatSwing.wav`（0.384 s，67,844 字节）。命令等价于
   `ffmpeg -i quickhit2.mp3 -ar 44100 -ac 2 -c:a pcm_s16le S_QuickCombatSwing.wav`。
2. `import_quick_combat_swing.py` 导入为 SoundWave：
   `/Game/Audio/QuickCombat20260918/S_QuickCombatSwing`，
   设 `LoadingBehavior = FORCE_INLINE`（短促单次音，首击不 pop），并写 `import_receipt.json`。
3. 入口：`run_import.ps1`（编辑器关闭时）；命令与 `SourceAssets/WeaponHitAudio20260916` 同口径。

注：目录在导入后由 `QuickCombatHitAudio20260918` 改名为 `QuickCombatSwingAudio20260918`；
`import_receipt.json` 里的 `source` 保留导入当刻的真实路径，不事后改写（回执是证据，不是文档）。

## 接线（最终状态）

`FPSQuickCombatComponent::BeginPlay()`：

- `SwingSound` = **`/Game/Audio/QuickCombat20260918/S_QuickCombatSwing`**
  （动作起手触发一次、2D、音量 0.8）。
- `ImpactSound` = **`/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick`**
  （回退到与符文剑柄尾共用的钝器音；只在确认命中——造成伤害或本次击杀——时于命中点播放，音量 0.9）。

判定日志（"声音没换"类问题先看这三行）：
`[QuickCombat] 音效资产 起手音=… 命中音=…`（BeginPlay）、`[QuickCombat] 起手音播放=…`、
`[QuickCombat] 命中音播放=… 目标=… 伤害=…`。

## 与既有近战音效的关系（2026-09-18 复核）

`quickhit2.mp3` 与既有的 `quickhit.mp3` 时长都是 **0.3840 s**、转换后 WAV 都是 **67,844 字节**，
但内容不同：两段 WAV 的 SHA-256 不同，PCM 数据 67,800 字节中有 **62,203 字节不同**（最大差值 255）。
即"同一长度、不同素材"，用户 2026-09-18 已确认。判重复要比哈希或 PCM，不能用文件大小当依据。

## 误建资产清理

首轮误接命中音时导入的 `/Game/Audio/QuickCombatHit20260918/S_QuickCombatHit`
（含目录 `Content/Audio/QuickCombatHit20260918/`）已于 2026-09-18 删除，无引用。

状态：音频已导入、代码已接线并完成编译（Game + Editor 双目标）；**未做游戏内听感验收**，
声压、触发时机与辨识度由用户试听判定。
