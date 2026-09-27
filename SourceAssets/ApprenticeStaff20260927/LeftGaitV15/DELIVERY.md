# 单手持杖：空闲左臂步频摆动 V15

本次接入当前长杖的空闲左臂。右手握点、手腕方向及 V14 整组右移 4 cm 的参数继续沿用。

- 行走：左手随右脚落地节拍向前摆，从画面左下方进入、回摆退出。
- 奔跑：独立的前送、抬高手腕及屈肘轨迹，手指比行走略收拢。
- 27 根左臂骨骼采用完整局部姿态，肩点保持在相机后方，肘部向左下支撑；不以整条手臂的刚性上移制造入镜。
- 复用 `GetStridePhaseRadians()`，右脚接触为 PI，左臂延迟 0.18 rad。每个完整步态周期 32 个姿态，循环插值。
- 行走/奔跑按既有 RunBlend 混合，起停按 MoveBlend 淡入淡出；蹲行幅度 60%。沿用动作占用、离地及攀爬等移动抑制条件。共享施法、药水等后续姿态层保持原顺序。
- 左臂手指采用松弛、逐指不同幅度的屈曲；手腕保留原生相对前臂关系。

## 已保存内容

- `author_gait.py`：完整左臂步态制作与 C++ 姿态表导出。
- `left-gait.json`：Walk/Run 两套循环，各 32 个左臂姿态，UE 厘米坐标。
- `Staff_FreeLeftGait_V15.blend`：保留 V14 手模、右臂与法杖，新增可编辑 `A_Staff_Walk_V15_FreeLeft` 和 `A_Staff_Run_V15_FreeLeft`，120 fps。
- `Source/FPSGAME/Weapons/Staff/StaffAuthoredLeftGaitV15.h`：运行时姿态表。
- `StaffFreeHandPose.cpp/.h`：骨骼映射缓存及循环局部姿态混合；`StaffArmsMeshComponent.cpp` 接入。

本次由原生姿态表驱动已有 V7 手模，不新增或导入 UE 动画资产。已有 UE 会话的 Live Coding 返回 Success，源码和热补丁已落盘；基础 DLL 未常规重编译。详情见 `build-receipt.json` 和 `live-coding-result.json`。本任务未启动或关闭 UE。

未运行游戏、截图、渲染或测试；入镜幅度、手臂观感及手感交由用户测试。
