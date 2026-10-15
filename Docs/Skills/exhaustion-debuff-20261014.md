# 体力耗尽：力竭

用户要求：体力为 0 时进入力竭，持续 5 秒，移动速度降低 50%，整个镜头变暗并播放喘气声。

## 实现

- `FPSStaminaModel` 在消耗前后及恢复前后观察体力；`FPSExhaustionComponent` 仅在进入零体力时触发一次。持续保持 0 不会循环触发，5 秒内再次耗尽也不刷新或叠加。自然回体继续按原恢复规则执行，回体不提前结束力竭。
- `CombatStatusFormula` 拥有固定的 5 秒计时和 0.5 移速乘数，共用角色移动与其他减益结算入口。死亡／重置清理，净化沿用减益解除入口。
- `status_effects.json` 登记独立 `exhaustion` 减益，共用 HUD 状态栏、倒计时、详情与图鉴；图标复用刻线步态图案。
- 全画面暗化使用独立本地后处理层，包含画面中央与第一人称武器，淡入／淡出后移除影响，不改写相机的其他效果。
- 本地喘气音在力竭开始时启动，在整个 DEBUFF 持续期间循环播放；结束或净化时淡出停止，死亡和角色销毁时立即停止。远端角色不会给本机播放喘气声或变暗。
- 服务端状态及截止时间通过既有状态复制传递；本地结算的近战耗体以所属角色 RPC 申请同样的固定自我惩罚，客户端不能指定持续时间、倍率或其他目标。
- 之前的零体力取消重击蓄力和自然收势继续生效。
- 后续按用户要求，力竭期间禁止冲刺，即使体力提前恢复。`CanSprint`、角色移动状态、服务端压缩移动标志及 SavedMove 重放均读取同一力竭计时；状态结束后再按原有体力及输入条件恢复冲刺资格。不会重置或延长减益时间。

## 音频

采用 drewsimko 的 **Panting.wav**，Freesound CC0。源页面允许修改、分发和商用。使用公开提供的 HQ MP3 预览作为制作源，转换为 48 kHz、单声道 PCM 循环 WAV，首尾用 80 ms 交叉淡化衔接，移除原先的固定 5 秒补静音与尾部淡出；非原始无损 WAV。引擎 SoundWave 开启循环，由状态结束而非文件长度控制停止。

来源、许可、制作脚本：`SourceAssets/PlayerExhaustion20261014/`。导入脚本：`Tools/Skills/import_exhaustion_audio.py`。引擎资产：`/Game/Player/Exhaustion/S_ExhaustionPanting`。

本次按用户规则不试听、不运行游戏、不进行联机或视觉验收。实际导入／构建结果以本批回执与交付说明为准。

音频已于 2026-10-14 21:31 在无界面 commandlet 中导入并保存，进程退出码 0；`SourceAssets/PlayerExhaustion20261014/import-receipt.json` 记录实际保存的 SoundWave 路径。导入日志为同目录 `import.log`，未启动交互编辑器或播放音频。

最终 FPSGAMEEditor 全量增量构建成功（75 个构建动作，190.98 秒），已完成 `UnrealEditor-FPSGAME.dll` 链接。构建日志保存于 `Saved/BuildEditor/exhaustion-debuff-editor-20261014.log`。本次没有启动游戏、试听或进行运行验收。

冲刺限制补充已完成 Game 和 Editor 构建，分别链接 `FPSGAME.exe` 与 `UnrealEditor-FPSGAME.dll`。日志：`Saved/BuildEditor/exhaustion-sprint-lock-game-20261014-retry.log`（37.68 秒）及 `Saved/BuildEditor/exhaustion-sprint-lock-editor-20261014.log`（149.08 秒）。首轮 Game 构建遇到并行战锤上挑代码的指针类型错误，待该处已有修改落盘后重建成功；本任务没有修改上挑行为。未启动游戏或执行测试。

## 喘息循环补充

循环素材长度 4.753333 秒，48 kHz 单声道、80 ms 首尾交叉淡化，不再包含补静音或固定尾部淡出。`SoundWave.looping=true`，组件仅在状态进入时开始播放，DEBUFF 持续期间由音频引擎循环，状态退出时淡出 0.2 秒；死亡／销毁立即停止。

复用已运行编辑器的 MCP 互斥桥导入。首次保存因编辑器处于 PIE 而被拒绝；后续编辑器日志在 2026-10-14 22:05:00 记录该音效包成功写盘，记录见 `SourceAssets/PlayerExhaustion20261014/loop-import-receipt.json` 与 `loop-save-evidence.log`。导入脚本已补充 PIE 入口判断，避免后续导入在无法保存的游玩模式中修改音效。没有主动启动、停止游玩或关闭编辑器，也没有试听。

循环补充的 Game 构建成功并完成 `FPSGAME.exe` 链接（215.54 秒），包含 `FPSExhaustionComponent.cpp` 的循环起播修改。日志：`Saved/BuildEditor/exhaustion-panting-loop-game-20261014.log`。本次未重编译／重载已运行的 Editor 模块，未试听或运行测试。
