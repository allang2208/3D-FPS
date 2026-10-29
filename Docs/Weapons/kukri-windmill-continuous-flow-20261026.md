# 尼泊尔弯刀旋风 V9：连续蓄刀、横扫与卸力

用户反馈 V8 看起来几乎没有变化，要求继续优化。

## 落盘与加载入口

V8 六个 `.uasset` 与六项 `Kukri.FullBody.Whirlwind.*` 配置确已保存。F6 第三人称／固定第三人称均显示 `GetBodyMesh()`，使用 `FPSPlayerBodyAnimInstance` 中的 Kukri 动作库，没有单独的另一套第三人称旋风资源。

`FPSPlayerBodyComponent::BeginPlay` 读取 `player_body.json`，随后 `InitializeBody` 加载配置的序列。F6 的 `RefreshViewMode` 只处理相机及可见性，不重新读取配置。已有游戏角色不会因为磁盘配置变化或切换 F6 视角自动换序列；重新创建游戏角色（例如退出当前游玩后重新进入）才会读到新配置。本次未读取用户当时实例的内存动作引用，因此不把缓存认定为用户反馈的已证实原因。

V8 的运动主体确实偏保守：持刀臂大部分时间已展开，变化主要是外伸方向的小幅摆动；两圈共用周期曲线，起止回到同一姿态。V9 从动作编排上替换这一结构。

## V9 制作

- 旋转段采用贯穿两圈的九组关键姿态：低位后侧蓄刀、向外释放、第一圈横扫、回带、第二圈蓄力、展开、第二次横扫、向前下方卸力、收势入口。
- 持刀臂从约 76% 臂长的收蓄伸至约 94% 臂长，随后向前下方卸力；保留软肘与原有握柄手型，手腕按原生骨段支撑制作。
- 左手在胸前护势与外侧平衡之间连续收放，锁骨、肘弯面和手型共同参与；不再仅给固定左臂叠加腕点摆动。
- 重心下沉按阶段变化约 16–23 cm；脚步沿同一全局转动时钟交替换支撑，摆脚抬高目标为 7 cm，并沿外侧弧线绕开另一侧脚踝。
- 第一圈和第二圈使用不同的蓄刀、横扫与结束姿态；末帧不再重置为旋转首帧。收势直接接前下方卸力的最后姿态，再回到当前待机。
- Jason、Kaitlin 分别使用实际网格绑定。仅生成与接入这两套第三人称的 Start／Loop／End，共六段。

这些数值是制作参数，不是实际运行画面的测量或自然度验收。仍以《洛奇》风车为视觉方向，并非提取或逐帧复刻原游戏资源。

## 文件与状态

六个 V9 原生动画包已保存，后台 commandlet 退出码 0；六项 Jason／Kaitlin 第三人称旋风引用已通过配置事务切换到 V9。

- 制作源：`SourceAssets/KukriWindmillFlow20261026/author.py`
- 原生轨道：`jason-actions.json`、`kaitlin-actions.json`
- 后台保存：`save_all.py`、`save_assets.py`、`run_commandlet.ps1`
- 接入：`publish.py`，按字段事务更新六项动作引用。
- 目标资产目录：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason|Kaitlin>/Animations/WhirlwindWindmillV9/`
- 资产名称：`A_Kukri_Whirlwind_<Start|Loop|End>_WindmillFlow`
- 实际保存与接入结果：同目录 `assets-saved.json`、`save_all-commandlet.json`、`published.json`。

不修改第一人称、伤害、技能时长、两圈总转角和其他攻击。没有 C++ 修改，无需游戏模块构建。后台只创建新包，旧资源保留；没有关闭、打开或重启 GUI 编辑器。

没有运行 PIE、游戏、渲染或自动验收；当前运行实例未热更新，最终效果由用户测试。
