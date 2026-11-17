# 陨石爆燃：火球命中效果放大替换

用户反馈上一轮火团仍僵硬，本轮以实际火球运行资产 `Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic` 为供体，将其中 `ContactIgnition` 和 `OutwardCombustion` 两个完整发射器复制进当前陨石撞击系统。保留供体的 8×8 连续爆燃图集、法线／遮蔽材质、向外展开减速、粒子差异及冷却动画。源火球及其材质不修改、不保存。

移除陨石旧的 `RefWhiteHotCore`、`RefPressureFireCrown` 和三个 `RefVolume*` 火团，仅以新 `FireballMeteorContact`、`FireballMeteorCombustion` 替换爆燃主体。现有 85 ms 接触闪光、径向放射、冲击波、火星、扬尘、余烟、下落包覆焰、尾迹、低矮残火、岩体与碎片、音效、镜头和玩法时钟均保留。

以陨石一级半径 652.5 cm 为基准，火球主体水平尺寸放大 3.25 倍，垂直放大 3.05 倍；位置仍按火球运行时的 0.765 校准因子换算，避免把组件位置缩放当成 Sprite 尺寸缩放。后续半径增长受到已有撞击边界限制。新增模块位于复制来的绝对位置与尺寸写入之后，逐帧不累积缩放。

## 翻滚延长修订 2

用户查看初版 GIF 后要求延长火团翻滚和扩散。接触爆燃仍使用 1.08 倍寿命，短闪与其他冲击层不变；仅将向外火团寿命从供体的 1.18 倍改为 2.05 倍，即 0.984–1.476 秒，含原有 22 ms 起燃延迟，上限约 1.50 秒。复制的位移表达式使用原来的 `1.18/2.05` 倍年龄，保持原轨迹与终点，把外扩及上升过程分摊到更长时间；不缩放系统时钟或 ParticleState 年龄。

火团图集独立重映射：前 75 ms 快速播放到第 14 帧；剩余寿命用 1.35 次幂曲线播放第 14–62.95 帧，让橙红翻滚段停留更久，再完整进入冷却帧。粒子继续连续扩散和生长，不循环或定格贴图。材质、数量、大小、接触爆燃、余烟及用户要求保护的表现均沿用初版。本次只保存撞击 Niagara 系统，仍无新增粒子、贴图、灯光、组件或原生改动。

增量入口为 `Tools/Skills/author_meteor_longer_roll_20261115.py`，备份及编译保存回执位于 `SourceAssets/MeteorFireballImpact20261115/LongerRoll`。共享配方同步升为修订 2，因此完整 V7 重建及火球替换入口也会保留延长后的时序。本修订不主动录制 GIF、渲染或测试，交由用户查看。

向外火团从火球的 6 个增加至 8 个，按 `User.DetailReduction` 可降至 4 个；接触爆燃 1 个。整个陨石撞击总发射上限 88 个，烟尘仍为 16。采用原火球母材质与实例的独立副本 `MeteorFireballImpactV8/M_MeteorFireballCombustion`、`MI_MeteorFireballCombustion`，发光增益 1.6→1.85，接触淡化距离 10→24 cm，其余材质参数随供体复制。不新增贴图、灯光、组件、碰撞或运行时流体模拟。

制作源：`Tools/Skills/meteor_fireball_impact_recipe.py`。增量接入：`author_meteor_fireball_impact_20261115.py`。完整 `build_meteor_reference_v7.py` 已改为在径向层之后应用火球配方，不再恢复上一轮火冠方案。运行路径继续使用 `MeteorAssets.h` 原有 `MeteorImpactReferenceV7/NS_MeteorPressureV7`，无需原生代码变更。

实际保存与编译记录：`SourceAssets/MeteorFireballImpact20261115/assets-saved.json`；替换前撞击资产保留在同目录 `BeforeAssets`。编辑器运行时通过现有桥的批次互斥接入；编辑器关闭时使用 `run_meteor_visibility_background.ps1 -MainProject` 的 `NullRHI` 无界面制作进程。PIE 运行时不复制或保存，等用户结束试玩。不启动或重启交互编辑器，不触发 PIE、预览、渲染或测试，最终效果由用户查看。
