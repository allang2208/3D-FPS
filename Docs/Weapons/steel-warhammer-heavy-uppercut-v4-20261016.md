# 双手锤第三人称重击、上挑与冲刺举锤 V4

本版本已被用户否定，运行引用已由 `steel-warhammer-direct-kwang-v5-20261016.md` 所述完整 Kwang 素材替换，V5 正式构建与切换均已完成。以下保留历史制作记录，不代表视觉认可。

## 本轮动作

| 动作 | 制作方式 | 既有时钟 |
| --- | --- | --- |
| Charge | Sevarog Swing3 肩髋发力；先下沉收柄，再屈肘送高，末段保持蓄满姿态 | 2.0 秒作者时钟；实际蓄力加速由工具原逻辑控制 |
| Slam | 从 Charge 末姿原样接入，前送下砸；锤头固定，胸肩向重量轻微沉降，然后抬锤收回 | 0.075 秒接触、0.7 秒落地保持、0.5 秒回收 |
| SprintLift | 从实际下拖冲刺握姿开始，收柄、屈肘、送高分阶段连续衔接，柄的转动滞后于第一段提拉 | 0.25 秒 |
| SprintSlam | 从 SprintLift 末姿原样接入；与普通重击分别保存自己的肩肘起点 | 同 Slam |
| Uppercut | 复用当前 Jason/Kwang 全身上挑作为身体基础，适配原生锤的双手握柄和由下向上的锤头轨迹 | 2.05 秒作者时钟，沿用 WarhammerUppercutMotion 的实际技能重定时 |

重击身体采用普通三连击 V3 的组件空间参考姿态校准，保留原生骨长。双掌共用同一握柄，使用连续肘部弯曲方向和前臂扭转分配。五个动作均固定颈部和头部局部姿态；沿用上一轮已编入项目的运行时头颈稳定处理。

## 运行接入

- `FPSBodyWarhammerMotion.h` 新增 `WarhammerUppercut` 到 `Warhammer.FullBody.Uppercut` 的路由；它因此使用独立全身动画和冻结的装备握姿，不再叠加第一人称攻击腕部轨迹。
- 蓄力释放和冲刺释放分别共享精确的前后端点，跳过会遮盖 75 毫秒下砸的通用 80 毫秒过渡。冲刺举锤入场使用 50 毫秒衔接。
- 上挑身体同步发布当前非线性作者速度，命中停顿时速度为零；腿部沿实际技能时钟显示已有的前冲步态，并继续服从受阻和空中限制。
- 重击蓄力的身体同步速率随实际蓄力时长变化，取消蓄力时不继续向前推演。
- 未修改第一人称动作资产、伤害、体力、范围、技能位移或冷却。普通三连击 V3 引用保留。

## 保存位置与来源

- 作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/HeavyUppercutV4/`
- 主脚本：`author_heavy.py`，结果 `adapted-actions.json`；重击来源为本工程已导入的 Epic Paragon Sevarog。
- 上挑读取入口：父目录 `prepare_heavy_uppercut.py`；只读取当时配置实际引用的 `/Game/Characters/JasonPlayer20261003/KwangSwordRecovery20261010/Animations/J_Kwang_Uppercut`，保存为 `uppercut-source.json`。
- 保存入口：父目录 `save_heavy_uppercut.py`，通过既有批次互斥和无界面 commandlet 写入新包。
- UE 目录：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/HeavyUppercutV4/Animations`。
- `assets-saved.json` 记录保存结果；`assets-published.json` 记录仅五个动作键的替换和原引用。

## 状态

五个新动作资产已由后台 commandlet 保存，并写入实际配置；上挑路由、衔接和同步时钟修改已正式编入 `UnrealEditor-FPSGAME.dll`。后台 Editor 构建成功，日志为 `Saved/BuildEditor/build-20261016-202122.log`，本批输出为作者目录 `build-editor.log`。未启动编辑器、游戏、PIE、自动测试、渲染或视觉验收，实际效果由用户体验。
