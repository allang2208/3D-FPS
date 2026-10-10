# 持魔法书快速近战的第三人称左臂修正

本次按用户要求排查并修复：法杖主手、魔法书副手执行 `SpellbookPush` 时，第三人称左臂扭曲。普通持书和右手持杖使用当前已接入的基线。

## 原因与修正

原路径把第一人称相机空间的手腕目标交给第三人称双骨 IK，并最后强制覆盖手腕方向；肩部支撑与肘部平面没有随整条动作链一起迁移。普通持书层又会在 `GunBash` 时让出控制，因此持书待机的正确姿态无法约束推击。

- 新增 `Staff.BookPush`，从当前 `Staff.BookCarry` 的原生 Jason 左臂制作 0.43 秒推击，沿用原来的 0.14 秒接触和 0.185 秒释放时刻。动作只修改上臂、前臂旋转；手腕局部姿态、手指、骨长、辅助骨局部绑定和书本挂接保持原基线。
- 播放时肩、肘、腕及加权辅助骨由同一条原生动作链接管；左侧第一人称手腕 IK 和通用快速近战手臂叠加退出该动作。右手继续持杖，身体与腿部仍由原步态控制。
- 起手用逐渐消失的当前持书偏差衔接动作，避免从冻结姿态向正在运动的目标反复混合。减小最初的肘部折叠幅度，让前推由肩部带动。
- 收势在动作末段接回实时持书步态；中断后从已显示的整臂姿态恢复，不重新吸附第一人称手腕目标。

正式动画：`/Game/Characters/JasonPlayer20261003/BookPush20261010/Animations/J_BookPush_NativeArm`。`Content/ColdSteelData/player_body.json` 已注册。命中、伤害、体力及第一人称动作未在本次修改。

## 本次定向排查

`fps.body.DiagnoseBookPush <输出 JSON>` 仅在明确执行时，创建无渲染的临时动画预览世界，使用正式 `UFPSPlayerBodyAnimInstance` 比较旧路径与新路径。旧路径只从临时动画实例中移除 `Staff.BookPush`，不改正式配置。

覆盖静止、180 cm/s 前进行走，以及 0.20 秒中断动作后的收势；每组按 120 Hz 采样。旧路径的第一人称目标使用模板站立相机高度作为复现条件，不是用户当前画面的逐帧捕获。

结果见 `SourceAssets/ThirdPersonBookPush20261010/diagnosis-summary-final.json`；原始逐帧骨骼变换见同目录 `proxy-diagnosis-final.json`。腕部偏转统计为相对已采用持书姿态的局部旋转差，不代表皮肤渲染或轴向扭转的单独测量。

游戏版和编辑器基础 DLL 构建日志分别为 `build-game-final.log`、`build-editor-final.log`。正式资产保存日志为 `save-commandlet-final.log`；最终定向复现日志为 `diagnosis-final-02-commandlet.log`。

本次没有启动交互编辑器、游戏或渲染验收。骨骼复现与必要构建已完成，实际服装变形、穿模和动作观感仍由用户在游戏中确认。
