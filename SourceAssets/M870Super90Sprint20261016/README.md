# M870 战术冲刺：直接复用 SUPER90 参考

**三条动画已通过后台 commandlet 导入并保存，退出码 0。** `install_receipt.json` 为 `completed=true`，保存时长为 0.30／0.60／0.30 秒；未运行测试。

用户指定参考 SUPER90。采用其实际生产入口 `Super90TacticalSprint20261007/Super90_TacticalSprint_Editable.blend` 的 **ShoulderReturnR3-20261007**，对应当前游戏 `/Game/Weapons/Super90/TacticalSprint20261007/Animations/A_Super90_sprint_enter/loop/exit` 三条序列。

## 动作适配

- 进入 0.30 秒、循环 0.60 秒、退出 0.30 秒，按参考的 120 Hz 制作和导入。
- 使用 SUPER90 已有抬枪与步频摆动轨迹。按 M870 的枪轴和右手握点配准，保持传统枪托上的右手完整抓握，目标延续参考约 76° 的抬枪表现。
- 起始与退出终点采用当前 M870 待机。左手先按参考的释放动作离开本枪护木，之后接入 SUPER90 肩、肘、腕、辅助骨和手指的整链收回，避免把本枪原来的肩位再叠加一遍参考后撤量。
- 入场前段保留 M870 当前 AKM 左手抓握；松手后再平滑接向参考的放松姿态。骨段使用本枪原生长度，模型、绑定、权重、衣袖和手套不变。

只导入 M870 `sprint_enter`、`sprint_loop`、`sprint_exit`。刚修复的普通／空仓装填，以及待机、ADS、射击与检视均不覆盖。

## 运行接入

既有 `M4TacticalSprintComponent` 的 M870 分支已加载这三个路径，所有握把索引共用本枪基础序列。共享组件以 Enter 进度双向采样，Loop 跟随步频；Exit 时长负责常规回握，动作请求仍使用既有 0.16 秒表现退出和 0.18 秒冲刺转射击约定。没有新增 C++、Tick、网络状态或独立推进时钟，不需要编译。

## 制作与保存

```powershell
& SourceAssets/M870Super90Sprint20261016/rebuild.ps1
```

- `Inputs/super90_reference.json.gz`：从参考 Blend 实际采样并冻结的三段姿态。
- `Inputs/super90_author_sprint.py`：本轮参考的生产函数副本，用于初始松握和原生腕肘衔接；没有修改 SUPER90 资源。
- `author_sprint.py`、`authoring.json`：适配入口、参考来源、时长、采样数与配准关系。
- `M870_Super90Sprint_Editable.blend`、`Exports/Animations`：本轮可编辑源与三份 FBX。
- `install.ps1`、`install_receipt.json`：既有桥互斥或后台 commandlet 的实际导入保存记录；旧包在 `Before/Animations`。

全套入口 `M870AKMArmSupport20261016/rebuild.ps1` 按基础动作 → 装填右手修复 → 本冲刺修订执行，防止重制时覆盖新的装填或冲刺。

本轮只后台制作、导出、导入和保存。没有启动游戏、图形编辑器、测试、截图或渲染；动作和衣袖的实机效果由用户确认。参考本身的历史导入记录不作为 M870 的验收结论。
