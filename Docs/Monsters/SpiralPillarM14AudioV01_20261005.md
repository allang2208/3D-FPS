# M-14 螺柱音效 V01（2026-10-05）

螺柱此前零音频。按"优先复用"策略全部本地解决：有机层复用 M-10 沉匣音效工作已下载的 CC0 freesound 源，金属硬件层（铆栓铿锵、接缝吱嘎、螺栓震颤）全部 numpy 程序合成，贴合"机械螺栓+湿组织"身体设定，无新增许可负担。

## 声音与动作合同

| 事件 | 资产 | 时长 | 对位 |
|---|---|---:|---|
| 待机 | —— | —— | 2026-10-06 用户反馈"嘈杂无特色"，Idle 循环整体取消（组件、属性与资产均已移除），待机保持无声 |
| 爬行/返回 | S_M14_Crawl | 2.6 s 循环 | 八趾拖行 + 接缝震颤 |
| 咬合 | S_M14_Bite | 1.15 s | 合咬峰值对位 BiteContactSeconds=0.86 |
| 吐射 | S_M14_Spit | 1.3 s | 释放对位 SpitReleaseSeconds=1.10；V03（同日二次反馈换源）：彻底弃用 squelch 水系素材——蓄力为气阀泄压嘶声 + 低频升压 + 紧固吱嘎，1.10 s 释放层换用实录酸性喷吐（freesound 568598）+ 气压爆点（138477），不再有任何咕哝/滋水质感 |
| 弹着 | S_M14_SpitImpact | 0.8 s | ShowImpact multicast 命中点 |
| 柱体砸击 | S_M14_TrunkSlam | 1.5 s | 砸地对位 SlamContactSeconds=1.20 |
| 旋扫 | S_M14_Whirlwind | 3.3 s | 0.55 蓄势 + 六圈 2.1 s 旋扫 + 0.65 收势（M14WhirlwindMotion） |
| 受击 | S_M14_Hit | 0.7 s | StartHitPresentation |
| 死亡 | S_M14_Death | 2.6 s | 软体塌落弧线：呻吟→瘫落→五金坠地 |

Sweep 左右扫为代码已弃用状态（"rejected root sweeps are no longer selected"），未做音效；转向由循环层覆盖。

## 实现

- `SpiralPillarM14`：`M14|Audio` 七属性 + Crawl 循环组件（spine_01）；`PresentState` 复制状态边沿播一次性（authority SetState 与 client OnRep 同源）；`UpdateLoopAudio` Tick 启停。
- `M14MucusProjectile`：ImpactSound ctor FObjectFinder，ShowImpact multicast 播放。
- 制作源与回执：`SourceAssets/SpiralPillarM14Meshy20261004/AudioV01/`（`prepare_audio.py`/`import_audio.py`/`finish_production.ps1`）。

## 状态

已完成：双 target 构建通过，8 个 SoundWave 落盘 `Audio/AudioV1`（Crawl 循环、FORCE_INLINE），`BP_SpiralPillarM14` CDO 写入 7 个声音引用；`S_M14_Idle` 已删除。回执在 `SourceAssets/SpiralPillarM14Meshy20261004/AudioV01/`。游戏内试听未验证，待用户确认。
