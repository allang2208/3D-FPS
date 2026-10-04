# M09 V20：120°/s 转身与独立转身节奏

用户要求把转身调整到 120°/s 并同步动画。保留 V19 的实际移动速度（默认 110 cm/s），仅进一步加快转向及其对应的换手/动画节奏。

- `TurnDegreesPerSecond=120.f`，仍通过 FixedTurn 按帧时间推进，原地和行进中转向共用。
- 方向差大于原有 4° 阈值时，使用 `CeilingTurnAnimationRate=4`；对齐后使用 V19 的移动倍率 2。
- 每次换手开始选定本次倍率，进行中的换手保持同一倍率直到落手。单手换抓在转向中为 0.15 s，在直行中为 0.30 s。预测落点使用本次时长及保持不变的实际移速，预测朝向使用 120°/s。
- 进入 Travel/Returning 时按当前倍率初始化动画；行进期间通过既有 `SetLocomotionRate` 平滑跟随该倍率，在同一移动状态内从转身切回直行也会恢复。
- 新增的 `CeilingAnimationRate` 只在换手边界变化，作为复制属性追加在类末尾，客户端使用服务器选择的动画倍率。继续复用已有状态复制、位置复制和抓顶 IK；没有增加 Tick、定时器或资产加载。
- 待机、三个攻击动作、命中/冷却和死亡时序保持现状。没有对整只怪物使用全局时间缩放，也没有再次加快平移。

修改：`Source/FPSGAME/Monsters/HangingBellM09.h` 与 `.cpp`。
制作前源文件备份及构建记录：`SourceAssets/HangingBellM09Meshy20261003/TurnRateV20/Records/`。
后台构建入口：`Tools/HangingBellM09/Build-TurnRateV20.ps1`，沿用完整依赖构建，未使用 Live Coding 或 NoUBTMakefiles。

未运行游戏测试、截图或渲染。无需重新导入动画资产；实际构建状态另记。

实际交付：用户保存关闭 UE 后，FPSGAMEEditor 与 FPSGAME 两个目标均后台构建成功，退出码均为 0，正式二进制已落盘。未重新打开编辑器，未运行游戏测试，交由用户体验。
