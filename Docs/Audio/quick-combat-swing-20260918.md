# 手枪快速进战 · 起手音（S_QuickCombatSwing，2026-09-18）

用户 2026-09-18 指定：`D:\FPS3D\资产\音效\quickhit2.mp3` 用作**手枪快速近战（握把砸击）的起手/释放音**。
首轮曾误接为命中音，经用户澄清后改正：本轮只换起手音，命中音回退到原来的共用钝器音。

## 资源与口径

- 源：用户提供的 mp3（授权与来源由用户掌握，仓库只做转换与导入，不再分发）。
- 转换：`imageio_ffmpeg` → 44.1 kHz / 立体声 / 16-bit PCM WAV（工程惯用格式）。
- 导入：`/Game/Audio/QuickCombat20260918/S_QuickCombatSwing`（0.3840 s），`LoadingBehavior = FORCE_INLINE`
  （短促单次音避免首击 pop）。
- 入口：`SourceAssets/QuickCombatSwingAudio20260918/`（`convert_source.py`、`import_quick_combat_swing.py`、
  `run_import.ps1`、`import_receipt.json`、README）。

## 接线（最终状态）

| 场景 | 之前 | 现在 |
| --- | --- | --- |
| 手枪快速进战 · 起手（释放那一下） | 复用剑的挥动层 `S_Sword_Attack` | **`S_QuickCombatSwing`**（起手触发一次、2D、音量 0.8） |
| 手枪快速进战 · 确认命中 | 复用符文剑柄尾的 `S_MeleeHit_Quick` | 不变（**回退**到 `S_MeleeHit_Quick`，命中点 3D、音量 0.9） |
| 手枪快速进战 · 挥空 | 无命中音 | 不变（只有起手音） |

播放条件与剑版一致：命中音只在**本次接触有效**（造成伤害或本次击杀）时播放。
枪械命中的落点确认音走另一条通道，不在本页范围内。

## 与既有近战音效的区分（2026-09-18 复核）

`quickhit2.mp3` 与既有 `quickhit.mp3`（符文剑柄尾）时长同为 0.3840 s、转换后 WAV 同为 67,844 字节，
但 SHA-256 不同、PCM 数据有 62,203/67,800 字节不同（最大差值 255）——是**两段不同素材**，
不存在"手枪与剑共用同一个音"的问题（此前按体积推断为副本的判断已更正）。
教训：音频"同长度同体积"不等于同一素材，判重复要比哈希或比 PCM。

## 误建资产清理

首轮误接命中音时导入的 `/Game/Audio/QuickCombatHit20260918/S_QuickCombatHit`
（含目录 `Content/Audio/QuickCombatHit20260918/`）已于 2026-09-18 删除，全工程文本面无引用。

状态：音频已导入、代码已接线并完成编译（Game + Editor 双目标）；**未做游戏内听感验收**，
起手音响度与触发手感由用户试听判定。
