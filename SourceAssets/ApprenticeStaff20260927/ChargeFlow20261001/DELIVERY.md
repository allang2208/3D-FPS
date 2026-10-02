# 法杖积蓄腕臂修订 2026100102

初版已被用户指出肘关节和上臂扭曲。当前作者脚本重新制作四握柄、五个完整右臂控制姿态，保留原手掌和杖握点、手指抓握、技能时钟及原生绑定长度。

肩根抬杖时保留在镜头后方，末键肩位置为相机厘米 `(-9,16,-14)`。以实际手掌与原 carry 腕姿反推期望前臂方向，形成每控制点的肘部 pole，再解算原生长度肘圆。上臂按 rest 弯曲平面建立框架；前臂绕固定肘铰链屈伸，围绕自身轴的 pronation 从实际掌宽求得并限制为45度。四根上下臂 twist 保持完整 rest-local 随段运动，取消旧的肩侧/腕侧端点固定及反向补偿。

`StaffGripPose` 在积蓄分支按 spline 权重混合屈伸/转向标量后组装下臂旋转，实际入场再进行一次整体局部混合。可编辑 Blender take 使用完全相同的方法；`StaffArmsMeshComponent` 的积蓄阶段不再额外叠 carry 肘扰动。

`author_motion.py` 写入完整 `full-pose.json` 和编入运行的 `StaffAuthoredChargeFlow20261001.h`；`save_editable.py` 后台保存四个120Hz、0.95秒参考 take 至 `Staff_ChargeFlow20261001.blend`。不需要导入 UE 动画 uasset。

`BeforeElbowRepair/full-pose.json` 是不可变的旧试作握点地标输入，同时保留旧作者脚本、Blender 源和运行源码。它是当前制作依赖，不能作为无用备份清理。

当前构建、产物及生效边界见 `ElbowRepair/integration-completion.json`；旧根目录同名回执仅对应初版。未启动 UE、游戏、PIE、渲染或测试，最终观感由用户体验。
