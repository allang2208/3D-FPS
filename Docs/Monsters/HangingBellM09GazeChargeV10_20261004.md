# 悬钟群眼凝视：粒子蓄能 V10

2026-10-04。按用户要求，参考百目炉渣眼部积蓄特效，为悬钟增加真正的 Niagara 粒子汇聚。V08 凝视的3秒动作、0.9秒锁向、1.25–1.85秒放射、14米射程、三次命中及伤害不变；V09背膜分层展开和1.5倍开膜速度保留。

## 表现

- 五颗主眼分别附着一个局部空间粒子系统。主眼采用0.90倍尺寸，四颗副眼为0.38倍，随实际眼骨位置和朝向移动。
- 每眼包含柔光粒、弯曲短光丝、细小光尘三层。粒子从眼周向瞳孔旋入，生命周期内向内加速；蓄力末段全体轨迹同时收缩，形成吸入眼睛的汇聚感。
- 主眼约0.08秒开始，副眼每颗错开0.035秒；全部在1.25秒放射前完成收束。各眼的 `User.Charge` 按同一攻击时钟推进，没有另建伤害或施法计时器。
- 使用灰紫、淡冷灰配色及透明软边，保持正常深度遮挡。原百目缩圈层改为微粒，不增加硬边圆环。
- 眼内微光在最后蓄力阶段增强，释放时保留约0.10秒的短亮度衰减。V08固定连接光丝在蓄力期降至原强度的32%，让移动粒子更清楚，发射时恢复。

## 复用与预算

源系统为 `/Game/Monsters/HundredEyedSlag/EyeChargeV14/NS_EyeConvergence`，其基础来自本地 ElectricMagic 蓄能栈。复制到悬钟独立目录后重写三层轨迹、颜色、粒子形状和收束过程，不改写百目或素材源包。

三层最大生成率分别为64、18、28每秒，寿命0.38、0.24、0.30秒。按持续生成率估算满强度约37个存活粒子/眼，五眼约185个；这是作者预算，未测游戏帧率。CPU解析轨迹、局部固定包围盒，无碰撞、力求解、附加灯光或新粒子Actor。

沿原怪物 Tick 更新五个复用组件。放射、打断、死亡、切换状态和退场时立即停止并清空，停用组件 Tick；距离本地视点30米外关闭蓄能组件。伤害继续只由一束主射线计算。

## 交付

- UE已保存：`/Game/Monsters/HangingBellM09/V10/NS_M09_EyeGather_V10`、`M_M09_GatherSpeck_V10`、`M_M09_GatherStreak_V10`。
- 作者脚本：`Tools/HangingBellM09/author_gaze_charge_v10.py`；后台入口：`author_gaze_charge_headless_v10.py`。
- 源码：`Source/FPSGAME/Monsters/M09Gaze.cpp`、`HangingBellM09.h`；烘焙目录在 `Config/DefaultGame.ini` 追加V10。
- 修改前源码、资产保存回执和构建日志：`SourceAssets/HangingBellM09Meshy20261003/GazeChargeV10/Records/`。最终状态见 `delivery.json`。
- 入口仍为原F6悬钟生成；单招触发为 `m09.Attack Gaze`。原生新增组件需要正式构建后的新实例。

为保存资产已通过现有桥结束当时的PIE，未主动启动编辑器、游戏、PIE、截图、渲染或测试。编译与资产保存不代表视觉效果已验收，由用户体验。

本轮常规构建遇到 `SpiralPillarM14.cpp` 的 UE API 拼写错误。仅将 `SetUpdateNavAgentWithOwnersCollision(false)` 修正为本机引擎声明的 `SetUpdateNavAgentWithOwnersCollisions(false)`，保留导航配置意图及其余并行修改；首次失败日志保存在 `build_FPSGAME_attempt01*`。

用户关闭 UE 后，等待占用编译器的已有构建结束，`FPSGAME Win64 Development` 和 `FPSGAMEEditor Win64 Development` 均返回 `Result: Succeeded`。本次最终增量构建为0项待执行，复用了共享工程中已生成的最新产物；没有启动编辑器或游戏，也没有执行运行时测试。
