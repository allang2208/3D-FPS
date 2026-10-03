# 百目炉渣：专用骨架与基础动画 V1

2026-09-30。本次按照用户要求，在已生成的 Meshy V2 模型上完成本地专用绑骨、蒙皮和原创动画制作、导出。未启动 UE、游戏、验收渲染或导出读回测试。

## 文件

- HundredEyedSlag_RigAndAnimations.blend：可编辑网格、37 根骨骼、33 根变形骨、四影响蒙皮、16 个 Action 和已打包的 PBR 贴图。
- SK_HundredEyedSlag_V1.fbx：绑定姿态下的带骨模型。
- HundredEyedSlag_RigAndAnimations.glb：带骨、PBR 和动画的合并输出。
- Animations/：16 个独立动画 FBX，仅导出骨架动作，不重复包含网格。
- Textures/：基础色、金属度、粗糙度、法线原始 Meshy 贴图。
- animation_contract.json：动作长度、循环、攻击窗口、释放时刻和根位移约定。
- delivery_manifest.json：制作参数与已导出文件清单。
- ../AuthoringV1/：原始整备场景、绑定中间文件、蒙皮字段、骨架定义和可重建脚本。

## 骨架与模型

以实际源网格的四个足底区域拟合关节；躯干、背壳、前部器官区、大右前肢、小左前肢、后肢和趾部独立分配骨链。采用解剖区域隔离的骨段距离权重，保留每点最多四个影响并归一化。原 Meshy 三角面与 UV 没有重拓扑或减面；制作母版约 289.7 万三角面、151.5 万顶点。Blender 高度统一到 1.2 m，前方 +X，上方 +Z；实际长宽由源形体比例决定。

原图的眼球已经融入主体网格；本次随壳体蒙皮，不宣称独立眼球注视或眼睑闭合动画。ash_origin 和 attack_origin 是后续特效、攻击接口使用的非变形骨。

## 动作

帧率 30 fps，第一帧为 1，时间公式为 (frame - 1) / 30。窗口秒值为后续接入参考；Action 标记按 30 fps 四舍五入到对应帧。

| 动作 | 时长 | 循环 | 编排与窗口 |
| --- | ---: | --- | --- |
| Idle | 3.0 s | 是 | 不均匀呼吸、前部与背壳细微紧张 |
| Move | 1.6 s | 是 | 四拍错相重爬，大右前肢承重；参考速度 0.39 m/s |
| Run | 0.9 s | 是 | 低伏交替对角快爬；参考速度 0.91 m/s |
| AttackSweep_R | 1.4 s | 否 | 大右臂抬起后横扫；接触 0.54–0.73 s |
| AttackSlam_R | 1.8 s | 否 | 大右臂抬起砸地并卸力；接触 0.84–1.00 s |
| SpecialAshBurst | 2.4 s | 否 | 四足支撑、压身蓄力、前部震爆与后坐；释放 1.0 s，窗口 1.0–1.18 s |
| SpecialCharge | 2.0 s | 否 | 压身后低伏快爬冲撞；窗口 0.56–1.24 s，位移由运行端负责 |
| SpecialCharge_RM | 2.0 s | 否 | 同一冲撞编排，根骨在 0.55–1.25 s 前移 1.4 m |
| HitFront | 0.5 s | 否 | 前方受击、后缩和恢复 |
| HitLeft | 0.5 s | 否 | 左方受击、右侧卸力 |
| HitRight | 0.5 s | 否 | 右方受击、左侧卸力 |
| Stagger | 1.05 s | 否 | 强冲击、持续失力与慢恢复 |
| StunEnter | 0.6 s | 否 | 下沉到眩晕承重姿态 |
| StunLoop | 2.0 s | 是 | 壳体失稳摇晃、前部下垂与不对称趾部颤动 |
| StunExit | 0.7 s | 否 | 恢复肩部承重和中性站姿 |
| Death | 2.8 s | 否 | 最后后缩、右支撑屈折、侧塌与收势，2.2 s 起保持末姿 |

默认动作是原地编排，SpecialCharge_RM 单独提供根位移。Death 的 1.68 s 标记仅供后续选择物理交接时参考，本次没有 Physics Asset 或布娃娃接入。死亡、受击和特殊攻击均为本地原创编排，没有套用现成动捕或 Meshy 人形动画。

关键帧生成时依据源表面采样烘焙了地面约束；这属于动作制作，不是运行或视觉验收。动画质量、实际接地、形变以及导入效果仍交由用户测试。

## 打开和使用

在 Blender 打开 .blend，选择 RIG_HundredEyedSlag_V1，在 Action Editor 中选择 A_HundredEyedSlag_ 开头的动作。全部动作保存在同一骨架上。

后续 UE 先导入 SK_HundredEyedSlag_V1.fbx 建立对应 Skeleton，再把 Animations 中的文件作为该 Skeleton 的动画导入。按照合同选择循环和根位移；本次尚未创建或导入 UE .uasset，也未接入动作状态机、伤害判定、灰烬特效或运行控制逻辑。

需要重建时从 ../AuthoringV1/Rebuild.ps1 执行；它只在后台完成整备、绑定、动画制作与导出，不包含测试和渲染。

