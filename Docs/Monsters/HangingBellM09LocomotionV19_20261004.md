# M09 V19：转身、移动及对应动画两倍速

用户要求转身速度翻倍、同步动画播放，移动速度也翻倍。本次沿用怪物工作流和 UE C++ 玩法流程，仅修改 `Source/FPSGAME/Monsters/HangingBellM09.cpp`。

- 原地转身和边走边转的角速度由 30°/s 改为 60°/s。
- 天花板实际移动使用现有 `CeilingSpeed` 的两倍：默认基准 55 cm/s 对应 110 cm/s。保留已有蓝图/实例的基准值，统一在实际平移与换手落点预测处应用倍率，避免已保存的覆盖值抵消本次加速。
- 单手换抓时间由 0.60 s 减为 0.30 s；两手完整交替周期由 1.20 s 减为 0.60 s。落点预测同时使用新速度和新换手时长，保留原步幅。转向预测角用新转速乘换手时长计算，保留原领先量。
- Travel 和 Returning 的动画初始播放率均为 2.0，包含原地转身使用的 Travel 动画。复用 `FMonsterClipTransition.InitialPlayRate`，进入状态即按两倍速播放；其进入混合由 0.14 s 减到 0.07 s。
- 待机、护冠双爪 V18、群眼凝视、三叠鸣震、受击和死亡沿用原时序；没有通过全局时间缩放改变战斗。
- 服务端仍控制真实位移、转向与抓点；客户端在已有状态复制触发的 PresentState 中使用相同播放倍率。没有新增反射成员或网络字段，也不需要重新导入动画资产。

统一倍率位于 M09 cpp 内的 `CeilingLocomotionRate=2.f`。`CeilingSpeed` 仍是原制作基准，不要再次把它手动翻倍，否则会在两倍倍率之上继续加速。

后台构建入口：`Tools/HangingBellM09/Build-LocomotionV19.ps1`。
构建记录：`SourceAssets/HangingBellM09Meshy20261003/LocomotionV19/Records/`。
该目录保留修改前 cpp 副本。实际构建状态随后记录；未运行游戏测试、预览或验收。

实际交付：FPSGAMEEditor 和 FPSGAME 两个目标均后台构建成功（退出码 0），正式二进制已落盘。未打开 UE、未运行游戏测试；由用户自行体验。
