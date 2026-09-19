# ASH-12 待机持枪前移

用户反馈 ASH-12 持枪位置太靠后，要求参考其他枪械做大致匹配。

读取当前 `FPSGAMECharacter.cpp` 的持枪基准：M4／QBZ191 为相机局部 `(0, 7, -7) cm`，当前 Soviet AKM 为 `(6, 7, -7) cm`；ASH-12 原来与 M4 相同。参考既有 `Saved/ASH12SightAudit/v12/ASH12-hip.png` 和 `Saved/ForegripAudit/front-m4-vertical-final/idle.png`，ASH 的后机匣和提把占据较多近景。旧截图用于构图参考，不作为当前资产实测结果。

本次将 ASH 的腰射持枪基准改为 `M4HipViewmodelLocation + (8, 0, 0) cm`，默认位置为 `(8, 7, -7) cm`。位移作用于整套枪械和手臂，配件及双手跟随；没有缩放模型或改写骨骼动作。待机及普通腰射使用新基准，换弹沿现有权重过渡到动作位置，ADS 沿现有权重过渡到已标定的瞄准位置。战术冲刺仍继承该枪的持枪基准与原有动画。

本次只修改现有初始化函数，已通过当前编辑器的 `LiveCodingToolset.LiveCodingToolset.CompileLiveCoding` 完成编译，返回 `Result: Success` / `Live coding succeeded`。当前已装备的 ASH 需要切到另一把枪再切回来以重新初始化；同一编辑器内新开始的游戏实例直接读取新位置。未进行本次实机测试，由用户体验前移幅度。本次为当前编辑器会话的热更新，基础 Editor DLL 尚未执行常规构建，后续关闭编辑器进行普通构建时会包含此源码修改。
