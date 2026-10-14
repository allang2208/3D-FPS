# 第三人称旋风：分段动作与换脚

用户于 2026-10-06 确认开始制作。只调整第三人称表现，采用本地 KayKit Character Animations 1.1 的 CC0 全身动作；不使用第一人称手模曲线作为全身母版。

## 动作制作

- `Melee_2H_Attack_Spin` 提供起势和收势参考；`Melee_2H_Attack_Spinning` 经已有 KayKit → Jason IK Retargeter 重定向，提供循环横扫的上半身参考。
- 导出源根朝向及 Jason 本地骨轨道，离线只剥离原始根的整体旋转，保留骨盆与胸廓的相对蓄力。生成资产的 root 恒定，由技能控制角色的两圈转向。
- 重做腿部：每半圈交替承重，前脚掌支撑时抬起脚跟，另一脚向外绕行并抬高约 8 cm。换脚处保留鞋间距，膝盖使用朝前并略向外的弯曲平面；脚尖随脚掌方向，避免固定膝盖与转动脚尖相互拧扭。
- 两段腿链使用 Jason 原生骨长的两骨求解；所有非根骨、非骨盆平移以及缩放采用 Jason 参考尺寸。头颈、脊柱和手臂不靠伸长骨段完成动作。
- 起势末帧、循环首尾、收势首帧相同。收势先落下抬起的脚，再沉髋回到稳定站姿。双手握柄和手指继续使用现有实际武器握持关系。

作者及许可：[KayKit Character Animations](https://kaylousberg.itch.io/kaykit-character-animations)。本地许可为 `SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/License.txt`。

## 运行接入

新资产目录：`/Game/Characters/JasonPlayer20261003/Whirlwind20261006/Animations/`。

| 动作键 | 资产 | 采样方式 |
| --- | --- | --- |
| `Melee.FullBody.Whirlwind.Start` | `J_Whirlwind_Start` | 起势阶段的归一化进度 |
| `Melee.FullBody.Whirlwind.Loop` | `J_Whirlwind_Loop` | 技能累计转角取一圈内的相位 |
| `Melee.FullBody.Whirlwind.End` | `J_Whirlwind_End` | 收势阶段的归一化进度 |

默认时序仍为 0.5 s 起势、0.8 s 两圈横扫、0.52 s 收势。循环资产用 1 s 表示一圈，实际播放由 `WhirlwindFeel::NormalizedPhase` 与技能转圈数共同决定；技能执行器也调用同一个相位函数。攻速、加速、刹停和命中停帧不另设动画时钟。

资产采用工程默认的 30 Hz 制作及压缩帧率，起势/循环/收势分别为 16/31/17 个键。收势源长度为 16/30 s，运行时归一化映射到技能的 0.52 s，不改技能时序。首次 120 Hz 数据与工厂默认压缩率不整除的失败候选已移至制作目录 `failed-save-02/`，不在 Content 下，也没有发布。

三段交接不再叠加普通换动作的 0.08 s 延迟混合；进入/退出整个旋风仍使用现有全身动作权重。原有近战地面处理已经释放普通站立的脚锁定和鞋底压平，新动作继续使用既有地形高度与倾斜修正。没有新增逐帧地面探测。

普通近战第二、三击仍映射为第一击。伤害、冷却、体力、命中去重、控制器旋转及第一人称旋风保持原契约。

## 制作文件

按次序执行以下脚本：

1. UE Python `Tools/PlayerBody/prepare_whirlwind_jason.py`：保存独立 Spinning 重定向源，导出 `authoring-input.json`。
2. 普通 Python `Tools/PlayerBody/author_whirlwind_jason.py`：生成 `authored-phases.json`。不运行 UE 或渲染。
3. UE Python `Tools/PlayerBody/save_whirlwind_jason.py`：创建并保存三段 AnimSequence，输出 `assets-saved.json`；拒绝覆盖同名候选。
4. 普通 Python `Tools/PlayerBody/publish_whirlwind_jason.py`：只更新三个已保存资产的配置键。

制作源及本次构建日志在 `SourceAssets/ThirdPersonWhirlwind20261006/`。旧单段旋风源保留，可供比较和回退。

## 交付状态

三段 UE 动画已由后台命令行实际保存，`save-cmd-04.log` 记录批次成功；`assets-saved.json` 记录保存路径，三个动作键已发布到 `player_body.json`。Game Development 与 Editor Development 构建均成功（`build-game.log`、`build-editor-console.log`）。等待共享构建及后台游戏实例自然结束后完成 Editor 构建，没有关闭其他进程或打开编辑器。未执行运行测试、截图或视觉验收，由用户自行体验。
