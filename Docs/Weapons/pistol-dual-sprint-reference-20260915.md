# 双持手枪奔跑动作：SprintReferenceV4

本次按用户指定的 [BV1PExtzNEBS](https://www.bilibili.com/video/BV1PExtzNEBS/) 优化 M1911 与 Dan Wesson 715 的双持奔跑。握姿、枪口汇聚继续使用 [NaturalAimV3](pistol-dual-natural-aim-20260915.md)，本次单独替换奔跑动作。

## 参考与动作设计

制作前查看本机已保存的视频帧：12.75–13.25 秒、32.75–33.5 秒的抬枪奔跑，以及 32–32.5 秒的低位持枪衔接。参考中两把枪都抬起，右枪略高；手、腕和少量前臂由下方进入画面，肘部基本在画面之外。两侧动作存在高低与前后差别，但不会轮流把一把枪完全放回腰射位置。

旧动作以腕部附近为旋转中心，基础抬枪 27°、正弦摆动幅度 14°。本次改为：

- M1911 右／左枪的基础抬角为 55°／50°，715 各降低 2°。在高位持枪基础上加入约 5° 的错相摆动和小幅横向摆动。
- 肘部带动前后行程，前臂与枪的转动稍晚于位移；抬起、回摆和两端缓冲由非均匀关键段控制。715 使用略小的角度变化与略长的跟随延迟。
- 枪、手掌和前臂成组运动，保留 NaturalAimV3 的枪柄握点、手指姿态和腕部关系。肩部从实际肘位反向支撑，保持原上臂、前臂长度及完整扭转辅助骨。
- 每次落脚加入轻微下沉与回弹，肩部跟随；肩肘向后下方安排，以参考的画面构图为制作目标。没有修改手臂网格、蒙皮、手套材质或枪械模型。

这是基于参考画面的三维适配，未提取原游戏动画数据。构图、幅度与最终握姿效果尚未在游戏内测试。

## 运行衔接

- 一条 1 秒源循环代表完整左右步周期，以现有脚步组件的行进距离相位求值；左右手共享周期、错开半周期。实际播放节奏随行进变化。
- 起跑使用 0.24 秒缓入；停跑使用最多 0.16 秒缓出，并受现有奔跑转射击时间限制。过渡曲线两端速度与加速度归零，恢复时回到 NaturalAimV3。
- 停跑／离地后保留最后一个奔跑相位，用该姿态回落；脚步组件停止时重置的剩余步长不再让枪突然切换到另一摆动位置。
- 完整奔跑时退出待机呼吸偏移，避免与落脚下沉叠加。换弹、射击、左手施法和闪避仍由原有动作控制，双持开火操作与弹药规则不变。

## 源资产与接入

- 作者脚本：`SourceAssets/PistolDualWield20260914/author_dual.py`，参数 `-- M1911 --sprint-reference` 或 `-- DW715 --sprint-reference`。
- 参数：`SourceAssets/PistolDualWield20260914/SprintReferenceV4/sprint_profile.json`。自然握姿参数继续读 `NaturalAimV3/pose_profile.json`。
- 编辑源与导出：`SprintReferenceV4/{M1911,DW715}/{r,l}/*_Dual_Editable.blend` 和 `Animations/*.fbx`；60 fps 编辑时间轴、120 Hz 烘焙，仅生产奔跑动作。
- 共 6 条动画：M1911 左右各普通／空仓奔跑，715 左右各奔跑。复用已接入的左右臂骨架网格。
- 导入：`import_dual.py -DualSprintUpdate`；资源路径 `/Game/Weapons/PistolDualWield20260914/{M1911,DW715}/{r,l}/SprintReferenceV4/Animations/`。
- `PistolDualWieldComponent` 仅将 `sprint`、`sprint_empty` 加载到新目录，其余动作仍从 NaturalAimV3 加载。

## 交付记录

- M1911／715 左右手共 4 份可编辑 Blend、6 条 FBX 已导出，两个作者进程退出码均为 0。
- `-DualSprintUpdate` 导入与保存完成，命令行进程退出码 0。导入日志包含纯动画 FBX 的绑定姿势回退提示，未据此宣称视觉结果通过。
- `Tools/Build/Build-Editor.ps1` 完成 `FPSGAMEEditor Win64 Development` 构建，结果 `Succeeded`。没有启动游戏或编辑器界面。
- 制作日志与导入记录位于 `SourceAssets/PistolDualWield20260914/SprintReferenceV4/`：`author-M1911.log`、`author-DW715.log`、`import.json`、`import-ue.log`、`build.log`。

遵照用户规则，未运行自测、PIE、截图或验收渲染；游戏内效果由用户测试。
