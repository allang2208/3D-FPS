# 螺柱 M-14 — V07 移动细节

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。用户要求移动时各个有骨骼的部位适当摇动、抖动。

## 动作调整

- 直行、左转、右转各新增一段 2.4 秒循环。复用原动作的根节点、基底和八组根裙推进轨迹，身体附属部位增加离线烘焙的跟随运动。
- 五段肉柱增加向上传递的侧摆、前后起伏和轻微扭动；按相邻体节的差值分配新增转角，限制长链累计倾斜。顶部新增侧倾约 5 度，转向另带轻微偏置。
- 薄膜由连接处到末端逐渐增加摆幅和滞后，末端叠加小幅颤动；左右囊体错拍晃动，增加前后、侧向和少量扭转。
- 链条与相邻薄膜共用主要摆动，再叠加幅度较小的金属颤动；束带只有很小的局部松动。原权重和连接方式不变。
- 下腹口器增加轻微悬垂摆动和毫米级起伏，八段口缘加入错时微动；口部出口随原父骨链自然跟随。
- 所有新增频率都是循环整数倍，采用 30 fps 采样，不添加逐帧随机噪声或骨骼缩放。当前 56 cm/s 移速、28 cm/s 动画基准速度保持原配置，满速播放仍为 2 倍，循环约 1.2 秒。
- 本轮只绑定移动和左右转向三个动画。V06 软组织死亡、原网格和碰撞，以及咬击、喷吐、横扫继续使用当前版本；没有新增 Tick 或实时物理解算。

## 制作文件

- [制作母版](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV07/Authoring/M14_Rigged_Locomotion_v07.blend)
- [动作制作](../../Tools/SpiralPillarM14/author_locomotion_v07.py)
- [导入与绑定](../../Tools/SpiralPillarM14/import_locomotion_v07.py)

## 状态

`A_M14_Move_v07`、`A_M14_TurnLeft_v07`、`A_M14_TurnRight_v07` 已导入保存，并绑定到原 `BP_SpiralPillarM14`。继续从 F6「螺柱 M-14」生成。本轮没有原生源码变动，不需要重新构建 C++。

未启动游戏、PIE、渲染或测试。摆动幅度、接缝和接地观感由用户体验确认。

落盘回执：[UE 保存](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV07/Records/ue_revision.json)、[动作制作](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV07/Records/authoring.json)。
