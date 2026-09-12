# 使用现成抓握源：先确认内容再重定向

2026-09-12 本机案例：`SourceAssets/MannyGraspDonor20260912/README.md`。VRE GrabAnimation 已接入 M4 / AKM 垂直握把各 9 动作。用户先认可垂直握把改善方向，随后确认同法扩展成功并要求作为配件标准；已接受扩展见 [45° 握把与阻手器](grasp-canted-handstop.md)。

- 实际导出并查看原始骨骼和网格。Epic XR Grasp 与 VRE GrabAnimation 内容不同，前者未闭合食指和拇指；同类命名不能证明可直接使用。
- 静态手型只解决指骨朝向。左右手镜像基于手掌解剖方向和 rest 坐标系，保留骨长、位置、缩放。整臂、握把挂点及退握回握仍需适配，保留换弹和机械接触时钟。
- 避免叠加 FBX 对象级单位曲线。网格导入已有单位变换时只赋值骨骼动画，否则可能再缩小 100 倍。NullRHI 网格导出若出现 MeshObject 断言，用允许 commandlet 渲染的独立导出工程。
- 厚手套与源手模形状不同，可先比较原始姿态统一开合幅度。此例采用 80% 闭合和整手对齐，仍有内部表面交叠，不能把数值回归当作零穿模或用户接受。
- 交付原始抓握、当前手模、真实玩家眼睛位置近景和回握动作。并行材质改变时读取实际引用、标明图像差异，不恢复其他会话正在修改的素材。
- 示例仓库代码许可不自动覆盖第三方手模。记录具体源文件与提交，二进制留本机直到再分发许可明确。

当前引用通过 `VerticalGripAnimationFamily.h` / `AKMAttachmentVisual.h` 核实。此次 M4 为 `M4VerticalGripVRENatural/Vertical`，AKM 为 `SovietFab/GripVRENatural/vertical`。阻手器的用户许可仍按 [玩家视角握姿要求](vertical-front-grasp.md) 执行，不扩大到所有配件。
