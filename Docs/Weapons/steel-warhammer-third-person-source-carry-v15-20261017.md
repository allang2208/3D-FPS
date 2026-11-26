# 双手锤第三人称：恢复源动作 V15

2026-10-17。用户否定 V14 的僵硬观感，要求修复人物歪斜后按参考源来。本轮恢复 Kwang 原始第三人称待机、持械移动表演，停止用第一人称手位或人为肘腕角度重建双臂。

## 来源与侧倾原因

Kwang 原待机的头部朝向已接近角色正前方，胸肩和骨盆保留战斗站姿的侧向转动。V10 曾把斜向肩线当作角色朝向，旋转整个源姿态，使原本接近居中的胸部轴线产生约 12° 横向偏斜。V12–V14 则重排肩肘腕，削弱了原动画的协调运动。这些适配结果不能作为已认可基线。

本轮直接读取 `/Game/ParagonKwang/Characters/Heroes/Kwang/Animations/Idle` 以及 `Jog_Fwd / Jog_Right / Jog_Bwd / Jog_Left`，沿用已有 Kwang→Jason 重定向器，将四个完整移动片段输出到独立包。保留演员原始角色朝向，不再用肩线调整全身朝向；只在 `spine_01` 对原待机测得的固定横向偏差作一次常量校正。原有随时间变化的重心、胸肩、腿部运动保留。

## 手臂、握持与头部

- 右臂的肩—肘—腕及其局部轨道保留源数据，不设胸前/腹部目标点，也不重新求解右臂。
- 左手沿实际锤柄移动/转握，靠近原始源握点。按原肘平面作解析的双骨接触适配，不用逐帧角度优化器选择新肩肘姿态。用实际骨长约束可达性，允许左手握点沿柄跟随源姿态；不再强制沿用第一人称两腕的固定高差。
- 本轮制作数据中待机左腕接触调整最大约 1.68 cm；移动片段约 1.69–4.16 cm。此数据只表明改动范围，不代表蒙皮或观感验收。
- 头颈以角色空间的稳定方向写入动画。`NativeWarhammerSourceCarry` 标记使新源动作持握跳过旧的“恢复中立局部头颈姿态”覆盖；否则原站姿的胸部侧转会把头一起带偏。攻击与其他武器保持原头部逻辑。

## 移动复用

保留四个原始方向移动循环。四个斜向采用相邻原始片段的落脚相位混合，未绘制新的手臂轨迹。读取 `LeftPlant / RightPlant` 并转为现有步态混合器使用的 `L / R`；缺少标记的 Jog_Bwd 从源脚部高度周期提取落脚时刻。

Kwang 本地素材没有独立 Walk 循环，因此步行与跑动复用相同的持械移动资源，由既有速度/步频逻辑调节播放。共保存 9 个最终资源（待机 1、方向移动 8），用于 19 项既有配置角色；普通与冲刺预备回退也复用原始待机。第一人称动作、攻击素材与时序、旋风方向均未修改。

## 制作与接入

作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/SourceCarryV15/`。

入口：`prepare_source_carry_v15.py` → `author_source_carry.py` → `save_source_carry_v15.py` → 正式 Editor 编译 → `SourceCarryV15/publish.py`。

独立最终包：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/SourceCarryV15/Animations/`。

接入代码仅涉及源持握标记与头部覆盖资格。已保存资源、commandlet 退出、正式构建与配置切换分别以 `assets-saved.json`、`save_source_carry_v15-commandlet.json`、`build-editor.log`、`assets-published.json` 为准。发布脚本要求保存与正式构建都完成，避免只换资源但头部逻辑仍旧。

未运行游戏、截图、渲染或额外测试；最终观感由用户确认。

## 已完成接入

9 个最终资源已保存，保存 commandlet 于 21:36 正常退出，退出码 0。19 项配置角色已由 FirstPersonReadyV14 切换为 SourceCarryV15。

本轮最初构建被运行中的编辑器阻止；之后正式构建遇到并行制作的 `M870QuickMeleeAudit.inl` 尚未落盘，后续等待批次又超时。没有修改这些并行文件或停止进程。

最终复用已完成的正式 Editor 构建：`Saved/BuildEditor/build-20261017-213942.log` 返回 `Result: Succeeded`（21:42）。当前 `UnrealEditor-FPSGAME.dll` 的 21:41:58 时间晚于身体动画源码的 21:23:42 修改，成功构建覆盖了本轮源持握头部接入。原始构建日志副本及源码/产物记录保存在 `build-completed-shared.log`、`completed-build.json`，不将本轮早先失败或排队超时的尝试记作成功。发布脚本已完成，`assets-published.json` 已落盘。

重新进入游玩时加载新配置；未进行实机或视觉验收。
