# 双手锤第三人称：分开持握与移动普攻 V16

2026-10-17。用户要求持握双手适当分开，并使普通攻击时的腿部继续衔接移动。

## 持握

以 SourceCarryV15 的 Kwang 原始待机、四方向移动及落脚相位匹配的斜向移动为基础。保留原角色朝向、常量躯干侧偏校正、稳定头部，以及右臂的源轨道。

V15 将支撑腕投影到锤柄附近，但没有沿锤柄分开两只闭合的手，造成握持重叠。V16 从已装备握持的拇指及四指骨节读取轴向范围，加上单侧 0.9 cm 的外形余量和 2 cm 的间隔，确定左侧支撑手的最低握点。支撑手放在右手上方、朝锤头方向，保留源肘平面，用实际骨长解算肘腕；不再向柄尾拉直左臂。此间隔是制作约束，不是蒙皮穿模或实机观感验收。

九个新的独立动画包保存到 `/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/SourceGripV16/Animations/`，供原有十九项待机/走跑配置引用。步态与头部标记沿用 V15。

## 移动普通攻击

既有 `CommittedSword` 将使用原素材时钟的双手锤攻击视为全身动作，把腿部权重拉到 1，盖住持续推进的移动步态。现在仅对 `Warhammer.FullBody.Slash1/2/3` 的下半身权重乘以 `1 - Movement.Alpha`：站定保留原攻击重心，移动逐渐交回实际方向步态，移动层完全进入后由步态接管腿部。

匹配保留的片段键，使同片段命中回收和淡出尾段也保留迈步；不在攻击开始时重置步态相位。上半身继续播放原攻击，现有胸部锚定负责把攻击胸肩连接到移动骨盆。没有修改第一人称、攻击判定时间、伤害、重击或旋风的腿部策略。

## 制作与接入记录

作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/SourceGripV16/`。

流程：`author_source_grip.py` → `save_source_grip_v16.py` → 正式 Editor 构建 → `publish.py`。

保存完成与配置发布分别以 `assets-saved.json`、`assets-published.json` 为准。构建以本轮 `build-editor.log` 或记录了当前源码与正式 DLL 的 `completed-build.json` 为准。

按用户规则不运行游戏、额外测试、截图或渲染，最终效果由用户自行测试。

## 已完成

9 个新动画已保存，保存 commandlet 于 23:18 正常退出（退出码 0）。发布脚本已将 19 项持握/走跑引用从 SourceCarryV15 切换到 SourceGripV16，记录于 `assets-published.json`。

复用 23:16 完成的正式 Editor 构建 `Saved/BuildEditor/build-20261017-231607.log`（`Result: Succeeded`）。身体动画源码于 23:12 修改，正式 DLL 于 23:16:40 生成；本轮源码摘要、时间及构建日志副本已记录于 `completed-build.json` 与 `build-completed-shared.log`。没有把旧的构建产物算作本轮完成，也没有为此启动编辑器或运行游戏。
