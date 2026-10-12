# 第三人称竖劈：握腕与扭转骨修正

后续反馈：用户已确认本版手臂正确，要求继续调整两手穿叠。后续手部修订完整保留本版肩肘腕轨道，仅调整左拇指及其运行时写入，见 [双手握姿间隙](third-person-sword-hand-clearance-20261010.md)。

状态：普通竖劈、冲刺竖劈两段资产已保存并接入；原生模块已完成后台编译。未启动游戏或 PIE，最终实机效果由用户确认。本记录替代上一轮恢复记录中这两个动作的当前资产与修复结论。

## 原因与改动

上一轮恢复 Kwang V2 消除了 V3 自由选肘平面造成的回归，但没有解决竖劈本身的折腕。针对性诊断中，实际原生动画图与已压缩动画的肩臂、腕部及辅助骨局部旋转在九个攻击进度点一致；因此继续调整通用运行时 IK 不能修好这段已经写入源动画的姿态。

旧适配在保持肘位的同时，将主要旋前角施加到前臂主骨，再用固定握柄框架强制对齐手腕。源姿态的腕部 swing 最大值右侧约 177.07°、左侧约 173.62°，原辅助骨旋转也未随新握持重建。只恢复肘位或只处理辅助骨均不足以解决问题。

本次重新拟合两手握柄转角，保留原剑轴、身体运动和双手握点关系。肘平面只允许相对恢复源在 ±60° 内调整，并约束相邻帧变化；按明确的肘目标重新生成上臂、前臂和 Jason 扭转／修正辅助骨，未调用 V3 的自由肘极优化。源 60 Hz 关键姿态的最大腕部 swing 降至右侧约 65.05°、左侧约 56.28°；该数值是制作坐标系中的姿态指标，不是人体关节验收结论。

绕柄角允许跨过 ±180° 连续旋转。一圈后的 365° 与 5° 是同一个握姿，但若运行时将 365° 标量直接乘回位权重，会让剑在收势时倒转。因此新增 `SwordGripRollSin`／`SwordGripRollCos` 曲线，在 `FPSBodySwordPose.inl` 中以 `atan2` 恢复等价转角；未含这两条曲线的现有动作继续使用原 `SwordGripRoll` 路径。

两段动画增加接触中间帧，按 120 Hz、193 帧、1.6 秒保存。保留 `NativeSwordGrip`、`Contact`、`Release` 和现有玩法时钟。仅替换 `player_body.json` 中 `Melee.FullBody.Overhead`、`Melee.FullBody.DashOverhead` 两项，当前目录为：

`/Game/Characters/JasonPlayer20261003/KwangSwordWrist20261010/Animations`

上挑、旋风三段仍使用上一轮 Recovery 资产。第一人称动画、攻击数值、身体和衣物资产没有纳入这次修改。

## 制作与落盘

- 制作源：`SourceAssets/ThirdPersonDashArm20261010/repair_forearm.py`、`candidate-actions.json`。
- 保存／接入：`Tools/PlayerBody/save_dash_arm20261010.py`、`publish_dash_arm20261010.py`；回执为同源目录下 `assets-saved.json`、`assets-published.json`，包含旧引用和制作散列。
- 后台正式编译：`Saved/BuildEditor/build-20261010-173636.log`，`Result: Succeeded`，已链接普通 Editor DLL。
- 原生定向诊断：`fps.body.DiagnoseSwordPose <输出路径> dash-arm`，仅编辑器构建可用；本轮通过无界面 commandlet 执行，不启动游戏。

## 已有排查结果与边界

最终资产读回的骨架、源散列和三个标记匹配；每段读取 49 个源对应采样，手臂局部旋转最大压缩差约 0.14974°，位置差小于 0.00004 cm，曲线值差小于 0.000953。见 `asset-readback.json`。

最终配置下，原生图的九个冲刺攻击进度点读取了新资产；手臂主骨及辅助骨与该资产的局部旋转最大差约 0.000003°，绕柄输出为周期解码后的等价角。见 `graph-after.json`。这只是完整动作权重下的定向姿态诊断，不覆盖实机输入、中断、移动叠加或淡出全过程。

`candidate-skin.png` 与 `candidate-phases.png` 为同一 Jason 源网格的离线蒙皮对比，用于观察折腕和肘位；不是游戏截图。压缩读回与原生图一致，也不等于视觉验收完成。未启动或重启 UE 界面，未运行游戏；实机冲刺竖劈、普通竖劈及收势表现仍由用户测试。
