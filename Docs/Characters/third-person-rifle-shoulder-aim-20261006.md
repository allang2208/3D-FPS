# 第三人称长枪靠肩与移动瞄准调整

用户截图中的待机枪托进入胸肩；步行举枪时，激光向准星收敛，但枪身仍保留全身动作里的握手朝向。

## 原因与实现

- 原有掌心映射解决了手与握把的接触，却没有定义枪管前向及枪托靠肩点。现根据当前枪械的瞄具轴、原生握持、掌心映射和实际枪托表面，计算枪体到第三人称右手的刚性关系。
- 保留 Jason 的全身待机、八方向步行和奔跑动作。普通持枪改为略低的持枪位，举枪连续过渡到肩前；枪管由完整瞄准俯仰与相对转向驱动，双手共同跟随枪体。肩部位置仍来自当前全身动作，因此随步行、下蹲及楼梯移动。
- 躯干分担 35% 的俯仰，腕部按枪管目标朝向求解剩余角度；不再将通用动作的手腕朝向当作实际枪口方向。保留射击短促抬枪、动作切换和原有肘部弯曲参考，不拉长骨段。
- 两手可达范围拟合增加肩前平面约束。可达区域与肩前平面相交时，沿平面调整整组握持，避免向胸口平移；极端长枪/握点组合若不存在交集，仍优先保留原有双手可达解，需实际姿态反馈后再调整握点或全身动作。
- 换弹、装备与检视仍使用原生动作相对握持的运动，但衔接到本次校准的持枪位置；弹匣及机械部件原有时钟保持。
- 第三人称长枪激光沿可见枪管发射，停止单独折向相机准星。近距离保留发射器相对枪管/视线的物理偏移。第一人称与手枪原有激光收敛保持。

## 模型数据

读取已保存的 AKM、M4、HK416、QBZ191、ASH12、M16A2、A762、SVD、LMG201、PKM 模型。按枪托材质区提取最后 4 cm 的接触区域；ASH12 无独立枪托材质，使用去除手臂后的枪械后端。记录 `WPN_root` 坐标及其原生 FBX 比例，不改变枪械大小。

改装枪托使用当前可见配件的局部包围盒经实际挂载变换后的后端与截面中心；这是配件边界估计，未逐款制作枪托接触插座。

- 制作脚本、提取记录：`SourceAssets/ThirdPersonRifleShoulder20261006/`
- 编译使用的接触表：`Source/FPSGAME/Characters/FPSBodyRifleStockContacts.h`
- 握持校准：`Source/FPSGAME/Characters/FPSBodyRifleHold.cpp`

只读 commandlet 停留在启动阶段，已停止本次自建的读取进程；随后通过现有编辑器 MCP 批次互斥完成模型读取和接触表落盘，未保存或覆盖编辑器资产，未启动新编辑器。

## 参考方案与交付边界

参考 Epic 的 [Aim Offset](https://dev.epicgames.com/documentation/unreal-engine/aim-offset-in-unreal-engine?lang=en-US) 与 [IK Rig](https://dev.epicgames.com/documentation/unreal-engine/ik-rig-in-unreal-engine?lang=en-US)：全身移动提供基础动作，上半身瞄准和手部 IK 共同完成朝向与接触。本次在既有 C++ 动画图中实现校准和双臂 IK，没有新导入动画包，也没有新增 Aim Offset 资产。

源码和接触表已落盘。`FPSGAME Win64 Development` 构建成功，日志为 `SourceAssets/ThirdPersonRifleShoulder20261006/build-game.log`。交付时 FPSGAME 编辑器仍在运行，完整 Editor 构建待保存关闭编辑器后继续，未覆盖已加载 DLL。

未运行游戏、截图、回归或视觉验收，由用户体验确认。
