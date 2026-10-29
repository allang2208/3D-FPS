# 冲刺下劈：单持左臂与双持举刀（2026-10-28）

本轮制作 Jason、Kaitlin 各一条单持、一条双持第三人称冲刺攻击。第一人称、命中窗、伤害与位移数值沿用现有版本。

## 动作

单持以已保存的 `SingleDashImpactV2` 为底稿，保持主手下劈、身体和腿部承重。左臂由此前较宽的侧展改为更靠近身体的前后摆动：举刀时略向前平衡，劈出时自然向侧后方摆，随后回摆收势。肩胛、肘和手腕采用错峰曲线；肘部维持自然弯曲，手腕只有小幅随动，空手指略放松。

双持新增完整的 `Kukri.FullBody.Dual.Dash` 动作。两把刀从头部两侧举起，按同一发力节奏从上向下劈砍，低位随挥后返回现有双持待机。副手基于主手轨迹的胸部空间几何关系适配，使用左侧原生关节轴和连续肘部解算，不直接拷贝右手骨骼四元数。左手保留当前双持的握刀指形与刀柄挂点；左右各自保持一条持刀路径。

两套动作均使用原有 120 Hz、161 帧、1.333333 秒时长；命中窗 0.367–0.467 秒。双持复用本轮之前已制作的前脚落地承重、后脚跟进与骨盆下沉，动作根不增加位移。

## 运行接入

之前双持冲刺没有专用动作入口，且通用副手保留规则会丢弃攻击序列中的左臂动作。现在：

- `FPSPlayerBodyAnimInstance.cpp` 为双刀装备选择 `Kukri.FullBody.Dual.Dash`，该序列存在时让它负责完整双臂。
- 双持专用动作使用和单持一致的实际速度、跑步制动与落脚权重。
- `FPSBodyKukriMotion.h` 只对已选中的双持专用冲刺开放同一支撑窗口。其他副手仍沿用原有规则。
- `player_body.json` 通过事务修改两套身体各自的 `Kukri.FullBody.Dash` 和 `Kukri.FullBody.Dual.Dash`，共四个叶字段。

## 文件

- 制作源：`SourceAssets/KukriDashHands20261028/author.py`。
- 单持源：`SourceAssets/KukriSingleDashImpact20261028/{jason,kaitlin}-actions.json`，按保存回执与当前入口匹配。
- 双持待机源：`SourceAssets/KukriDualIdleThirdPerson20261027/{jason,kaitlin}-actions.json`，使用已保存的 `Dual.Idle`。
- 目标目录：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason,Kaitlin}/Animations/DashHandsV3/`。
- 单持资产：`A_Kukri_Dash_Hands`；双持资产：`A_Kukri_Dual_Dash_Hands`。

## 交付记录

`FPSGAMEEditor Win64 Development` 正式构建成功；Jason、Kaitlin 各两条动画已通过无界面 commandlet 保存，四个动作入口已通过配置事务接入。保存、配置接入与正式构建的记录位于 `SourceAssets/KukriDashHands20261028/` 下的 `assets-saved.json`、`published.json`、`editor-build-resume-result.json`、`delivery.json`。

保存脚本在交互编辑器内保留 PIE 保护；无界面 commandlet 跳过不可用的 LevelEditor 游玩状态接口。首次后台保存因此中断，修正后重新保存成功，失败日志单独保留。

用户自行保存并关闭 UE 后完成后台构建与落盘，没有重开编辑器或启动游戏。本轮没有主动运行测试、截图或验收渲染。此前为保存资产请求结束过一次正在运行的 PIE，之后用户重新开始游玩，后续改为等用户关闭编辑器完成。动作自然度、服装与武器的实际画面由用户实测。没有 Git 提交或推送。
