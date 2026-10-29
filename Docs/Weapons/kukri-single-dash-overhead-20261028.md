# 单持冲刺攻击：举刀冲刺与过顶下劈

本轮为 Jason、Kaitlin 制作单刀第三人称冲刺攻击，动作入口为 `Kukri.FullBody.Dash`。读取项目实际安装的第一人称 `A_Kukri_SprintAttack` 作为主手轨迹与阶段时钟参考，按完整人物的肩宽、骨长和头部空间适配。

## 动作设计

- 迅速将右手持刀举到头侧上方，在约 0.17–0.33 秒保持过顶蓄势。举刀期间，移动状态继续显示原有跑步步态。
- 约 0.333 秒开始下劈，0.367–0.467 秒对应现有命中窗。右臂向前伸展，从上方向前下方劈过，前脚先落稳，后脚跟进承重。
- 劈下后保持短暂低位随挥，再沿连续路径接回当前单持待机。第一人称画外收势中的大幅转腕不直接搬到可见的第三人称模型。
- 左手在身体一侧随举刀与落脚平衡，手肘自然弯曲、手指轻微放松。第一人称参考中有左手压柄，本轮按单手持刀表现制作左手平衡动作，不建立假握柄接触。

主手通过原生两骨链联合分配肘部弯曲方向、前臂转刀与腕部小幅修正。保留当前原生握刀指形；最大肩腕距离控制在臂长约 94%，下劈经过胸前时保留前伸距离。锁骨轻度参与抬手，重建双臂 twist 辅助骨。

身体的抬升、压低节奏参考当前原生 `Melee.FullBody.DashOverhead`，去掉侧歪和过大的位移。腿部使用与上挑修订相同的原生膝关节求解方法：脚尖轻微外展、膝盖跟随各自脚尖、脚跟蹬地以前脚掌为支点，收势左右错步回位。胶囊移动仍由现有冲刺玩法控制，动画不添加根位移。

## 时钟与运行接入

动画为 120 Hz、161 帧、40/30 秒，Contact 为 0.367 秒、Release 为 0.467 秒，带 `NativeSwordGrip` 标记。命中、伤害、技能速度、第一人称动画与相机不改。

`Source/FPSGAME/Characters/FPSBodyKukriMotion.h` 的 `AttackLegWeight` 增加单持 `SprintAttack` 阶段规则：移动时举刀阶段保留步态，下劈前逐渐转入作者承重姿态，收势后再回到移动步态。规则仅在副手为空时启用；原有空中、滑铲、翻越等外层权重继续参与。

本轮未制作双持专用冲刺动画。双持或其他副手装备仍沿用现有通用 Dash 回退及副手保留逻辑，不将本轮当作双持动作验收。

## 制作文件

制作目录：`SourceAssets/KukriSingleDash20261028/`。

- `prepare.py`、`inputs.json`：当前第一人称、单持待机、旧 Dash 与原生双手剑下劈来源。
- `author.py`、`*-actions.json`、`authoring.json`：完整动作制作、原生关节求解及来源时钟。
- `build_editor.ps1`、`editor-build-resume-result.json`：必要 Editor 构建及结果。
- `save_assets.py`、`save_all.py`、`run_commandlet.ps1`、`assets-saved.json`：新动画包保存。
- `publish.py`、`published.json`、`delivery.json`：两个配置字段事务与最终交付状态。

新资产目录为 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/SingleDashV1/`，名称 `A_Kukri_Dash_SprintOverhead`。原动画保留。

两套动画已由无界面 commandlet 保存，退出码 0；两个 `Kukri.FullBody.Dash` 入口已完成字段事务切换。`FPSGAMEEditor Win64 Development` 构建最终返回 Succeeded、退出码 0。读取前原编辑器已自行退出，后续均在后台完成，没有主动打开或关闭图形编辑器。

按用户规则，完成制作、必要构建与接入，不自动运行游戏、测试、截图或渲染。最终观感、衣物与武器穿模由用户体验确认，未打包、提交或推送。
