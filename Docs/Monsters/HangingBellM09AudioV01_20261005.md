# M-09 悬钟音效 AudioV01（2026-10-05）

按"优先复用本地"策略补齐悬钟声库：V04 的 7 条占位音为正弦+噪声极简合成，Resonance V07 与 Gaze V08 已获认可保留；本轮沿用 V07 的膜片钟声配方补全缺失状态并升级薄弱项，全部本地程序合成、无新增许可负担。

## 覆盖与替换

| 状态 | 处理 |
|---|---|
| Idle | 新增 3.6 s 循环：钟体低泛音微光 + 膜片呼吸 |
| Travel / Returning | 新增 2.4 s 循环：天花板手交替爬行（抓点闷击+刮擦） |
| Dying / Corpse | 新 Death 2.4 s：失谐→膜裂→坠空→1.48 s 落地钟响（替换 1 s 占位） |
| SwingLeft/Right | 膜片划空 + 爪击钟鸣（替换占位） |
| Claw | 膜片切入 + 金属扣响（替换占位） |
| Stagger | 闷钟敲击 + 膜片受惊（替换占位） |
| Resonance | 2026-10-06 V09 重做（用户反馈 V07 像敲钟）：低频压力蓄力 + 每脉冲 sub 重击/裂响/暗调失谐钟体/扩散环呼啸，基频 62→98 Hz 逐脉冲递进；资产 `/Game/Monsters/HangingBellM09/V09/Audio/S_M09_Resonance_V09`，V07 保留作恢复 |
| Gaze | 保留 V08 已认可版本 |
| 警觉（非状态） | S_M09_Alert 1.2 s（2026-10-07 新增）：进入首个攻击状态的边沿在眼位播放——低音钟醒 + 膜片惊缩 + 压力闷升，是"它看见你了"的前兆音 |
| 共鸣余韵（非状态） | S_M09_RingDown 4.0 s（2026-10-07 新增）：共鸣状态退出时在锁定原点播放——最后一发基频 98 Hz 的失谐泛音列缓慢衰减 + 高频残响滑落 + 膜片松弛吱嘎，盖住 Voice 硬切 |

## 实现

- `HangingBellM09.cpp` ctor 末尾按角色名加载 `/Game/Monsters/HangingBellM09/Audio/AudioV1/S_M09_*`，`Sounds` TMap 覆盖同名键；`PresentState` 的 Voice 组件路径零改动。Alert/RingDown 为非状态键，由 `PresentState` 的状态边沿（`PresentedState` 本地追踪）经 `SpawnSoundAttached`/`PlaySoundAtLocation` 播放，authority 与客户端各自本地播放，不走复制字段。
- 制作：`Tools/HangingBellM09/author_audio_v01.py`；导入：`import_audio_v01.py`；编排：`Build-AudioV01.ps1`。
- 制作源与回执：`SourceAssets/HangingBellM09Meshy20261003/AudioV01/`。

## 状态

双 target 构建通过、9 个 SoundWave 落盘（`delivery.json`/`import_saved.json`）。落地钟响按典型顶棚高度烘于 1.48 s（布娃娃路径无落地回调，极端高度有偏差）。未做运行验收，游戏内试听待用户确认。
