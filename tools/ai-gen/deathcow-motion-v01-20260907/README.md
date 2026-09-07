# 胖僵尸 Run / Attack V01 — 2026-09-07

阶段：用户授权按既有技能经验修改奔跑和攻击动作，交付独立动作候选。沿用 deathcow-appearance-v01-20260907 的外观，不切换正式游戏引用。

## 参考与动作意图

制作前逐帧查看了原项目 walking 的全部 11 帧和 attacking 的全部 14 帧，证据为本目录 walking-reference.jpg / attacking-reference.jpg；读取胖僵尸 source-config.json 与参考合同。技能使用 godot-monster-workflow 及 references/humanoid-motion.md：先支撑与承重，再胸/头/手臂错峰；中间关键姿势使用连续三次曲线，避免每帧 smoothstep 停顿。

- 原移动 11 fps、1 秒循环：前倾、屈膝、双臂低垂、左右脚交替前送承重。它不是现成冲刺。新 Run 是在这个意图上的沉重小跑重建；单视图不能确定左右遮挡细节，三维固定左脚抬得略高。
- 原攻击 14 帧、1 秒单播：起始屈肘外展，双手向前，0.2142857 秒接触，之后前压下收，约 0.57 秒手臂低垂，再收肘归位。三维保留双臂参与，右臂仅短暂落后 12 ms，接触姿态仍对齐原时刻。
- 当前模型没有手指骨，保留现有开掌手型；没有制作握拳指部动画。厚躯干、肩部和衣服比例不同于原图，姿态是三维适配，不宣称精确捕捉。

## 时间与移动合同

- Run：60/84 = 0.7142857 秒循环，原地动画。左右错开半周期；支撑占比 0.52，脚在支撑期间匀速向后。每脚支撑行程 0.38 源单位，匹配水平速度 1.0230769 源单位/秒；若整体模型缩放，速度同步乘缩放。不要叠加 root motion。
- Attack：1 秒单播，84 fps 作者采样，接触第 18 帧（零基）= 3/14 秒。业务有效窗口 [2/14,6/14) 秒，原冷却 2 秒。此轮只制作动画，未新增伤害结算。
- 攻击脚固定，骨盆前移下沉，胸部带肩和双臂前推；膝部通过两节 IK 维持支撑。
- 原 Idle 8 秒保留，关键帧仅随场景 fps 从 24 到 84 等比换算。
- Run 首尾循环；Attack 收势返回其预备姿态，正式切换到 Idle/Run 时还需在业务控制器内做短混合。本轮未改状态机。

## 检查与局限

- GLB 导出后重新导入，核对 Idle 8 秒、Run 0.7142857 秒、Attack 1 秒，并实际渲染正斜侧及侧面完整动作。
- support-validation.json 记录导出后脚骨的支撑速度补偿误差、攻击固定脚误差；这是脚骨采样，不是脚底每个网格顶点或游戏地形的碰撞验收。
- validation.json 记录首尾所有网格顶点最大位置差及动作时长。没有修改网格/权重，极限姿态仍需要用户视觉反馈，尤其厚袖口和腋下。
- Run GIF 连续展示 7 个周期，总长 5 秒，避免 GIF 10ms 时间精度使单周期速度漂移；Attack GIF 1 秒，重复仅便于观看，不代表游戏循环攻击。每周期预览采样 24 帧，完整动画为 84 fps。
- 预览为 Blender Cycles CPU 渲染，未做 Godot 默认渲染、实战或伤害验收。

## 使用

fat-zombie-motion-v01.blend：可编辑骨骼动画，打开显示攻击接触第 18 帧。NLA 已静音便于编辑；通过 Action Editor 选择 Idle、Run 或 Attack，并选对应 action slot。保存源不会自动替换游戏。

fat-zombie-motion-v01.glb：三段动作的独立导出。Run.gif / Attack.gif 为实际导出模型预览。build_motion.py、preview.py、check_support.py、package.py 可重建制作、检查及打包流程。

## 来源署名

原模型 fat zombie idle (animated)，vicente betoret ferrero（deathcow）：
https://sketchfab.com/3d-models/fat-zombie-idle-animated-ab45b1f5bf0947fa8a3f2d349f47e0ba

CC BY 4.0：https://creativecommons.org/licenses/by/4.0/ 。此版本修改了外观并新增 Run / Attack，使用需保留作者、来源、许可并注明修改。

## 本次归档范围
本目录作为相邻 backfall V02 的直接重建与对比输入，保留 .blend、.glb、原动作参考及关键帧。完整早期制作脚本与 GIF 仍在本地同名目录，未重复上传；不将本目录称为独立完整制作管线。
