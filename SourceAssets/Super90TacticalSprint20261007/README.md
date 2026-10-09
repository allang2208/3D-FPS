# Super90 战术冲刺

当前作者版本为 **NativeHingeR2**：按 AKM 冲刺及 PKM / 201 肘铰链案例，修复左臂弯曲轴反转、前握把作者姿态的根缩放转换，以及前臂辅助骨分站。根因、针对性排查数据和本轮实际保存状态见 `../Super90SprintArmRepair20261007/README.md`；初版不再作为成熟动作基准。

原生 V7 骨架新增 `sprint_enter` / `sprint_loop` / `sprint_exit`，时长 0.30 / 0.60 / 0.30 秒，按 120 Hz 制作和导入。沿用现有步枪战术冲刺行为：右手保持握柄、枪口抬高到约 76°；左手先松握后沿肩部弧线下摆，腕部相对前臂放松；反向播放同一入场轨迹完成可中断回握，动作请求使用原有 0.16 秒表现退出。

原厂共用三段基础动画，四类前握把在既有 `WeaponGripProfile` 中分别追加三段差量。现有 12 段原动作和 15 段装填器动作均保留，战术直握把继续共用垂直握把家族。前握把重导入入口同步保留冲刺条目。

`M4TacticalSprintComponent` 新增 Super90 类型与资产分支；角色初始化启用该类型。跑步速度、体力及开火间隔仍使用现有业务逻辑，换弹、瞄准、开火、滑铲、翻越、闪避和左手施法沿用既有动作仲裁。

制作源：`Super90_TacticalSprint_Editable.blend`、`Exports/`、四份 `*_profiles.json`。制作脚本 `author_sprint.py`，保存脚本 `import_sprint.py`。正式资源目录 `/Game/Weapons/Super90/TacticalSprint20261007/Animations`；保存结果以 `import_receipt.json` 为准。

本批不覆盖整枪网格、材质、装填器动作或玩家存档；装填器返工计划见 `../Super90MotionRevision20261007/PLAN.md`。未运行游戏、自动测试、截图或验收渲染，由用户体验确认。

## 资产落盘

无界面 `Run-Authoring.ps1` 已完成 NativeHingeR2 导入，实际保存三份动画及四份前握把配置，共 7 份资产。每份握把配置当前 30 条动作，另外 27 条保留。当前保存回执 `import_receipt.json`，本轮日志 `../Super90SprintArmRepair20261007/import_commandlet.log`；未打开 UE 编辑器或运行游戏。

## 原生构建已完成

用户在继续任务中关闭已有编辑器后，已执行 `Tools/Build/Build-Editor.ps1`。结果 Succeeded / Target is up to date，当前完整 Editor 目标无需额外编译或重链；日志 `Saved/BuildEditor/build-20261007-205111.log`。随后导入新版装填器时保留了本批冲刺的三段动画和四份配置中的对应条目。源码、实际资产与原生构建接入均已完成；未运行游戏，表现由用户体验确认。
