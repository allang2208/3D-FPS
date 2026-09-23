# PKM 战术冲刺与快速进战动作

2026-09-23。用户要求接入战术冲刺和快速进战；后者沿用项目现有 F 键快速近战／枪托挥击合同。

## 动作

此前 PKM 已有运行入口和各握把路由，但源动作主要是整个组件的简单位移／旋转。本轮以当前 PKM 待机为基底，重制 5 组 × 4 段动作，共 20 段。

| 动作 | 源时长 | 内容 |
| --- | ---: | --- |
| sprint_enter | 0.35 秒 | 左手先脱离握点，再向外下方收回；右手承托抬枪，枪口向上 |
| sprint_loop | 0.60 秒 | 枪身与右手小幅摆动、左臂随步伐运动，首尾循环 |
| sprint_exit | 0.35 秒 | 沿起步轨迹反向回握，恢复本组 idle |
| quick_melee | 0.90 秒 | 蓄势、枪托挥击、随动、收势，命中仍为 1/6 秒 |

冲刺保持项目已有步幅相位同步；中途反向沿同一 enter 轨迹采样，开火／瞄准等动作继续使用原有 0.16 秒表现收枪和既有业务门槛。没有修改移速、冷却、伤害、命中半径或输入规则。

## 制作依据

- 默认当前待机：`../Feed13/PKM_FiringFeed_Editable.blend` 的 `PKM_Game_idle_Wrist12`。
- 四组握把：`../GripContact15/PKM_<family>_Editable.blend` 的各组 `idle_Contact15`。战术垂直握把继续共用 vertical。
- 冲刺动作参考：工程现有 `SourceAssets/ASH12TacticalSprint20260919/author_sprint.py`，以及已留存的 `Saved/RifleSprintAudit/RifleSprintAudit-final60-v2/Preview/M4-grips-transitions.jpg`。依据 PKM 的枪轴和当前腕部位置重新计算抬枪、偏移与左臂撤离轨迹。
- 枪托挥击参考：`SourceAssets/QBZ191QuickMeleeGrip20260919O/Base/QBZ191_QuickCombat_Base_Editable.blend` 的 `QBZ191_QuickCombat_O_Base`。只使用武器运动与节奏；枪托位移按 PKM 既有接触锚点重新定位，双手保持各自 PKM idle 的枪根相对握点，整组投影到双臂可达范围。
- 腕臂：复用 Reload16 的完整骨段支撑与 rest-frame 旋转解算，肩肘跟随目标手掌，手指作为整手保留。冲刺左手脱离后逐渐放松，回握时恢复原指型。
- 武器机械骨、弹箱和弹链保持当前闭合／装载关系，并随枪根整组搬运。空仓弹链显隐继续由游戏状态控制。
- 动画 120 Hz；骨架、权重、材质和原有挂接关系不变。源动作首尾使用对应 idle。

## 文件与运行接入

- `author_actions.py`：离线制作与 FBX 导出，无渲染／测试入口。
- `PKM_<family>_Combat_Editable.blend`：当前可编辑动作源。
- `Animations/<family>/`、`animations.json`：20 段导出与作者时长。
- `authoring.json`：输入来源、时钟与 PKM 枪托锚点。
- `import_actions.py`、`import_<family>.py`：通过工程 MCP 互斥桥导入，每段保存回执写入 `imported.json`。

覆写既有动作资产内容，继续使用实际运行引用：

- 默认：`/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_<clip>`。
- 握把：`/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/<family>/A_PKM_<family>_<clip>`。
- 路由：`M4TacticalSprintComponent::Configure` 的 PKM 分支，以及 `AFPSGAMECharacter::RifleQuickCombatClip` 的 PKM 分支。
- 近战：继续使用 `TriggerRifleStockMelee` 和 `QuickCombatRifleMotion::ReferenceStockPointCM` 中现有 PKM 锚点与参考时钟。

这是动画资产修订，无 C++ 修改，不需要原生构建。换弹仍以 Reload16 为准；开火仍使用现有 Feed13 / GripContact15，其他握持动作仍以 GripContact15 为准。不要用早期作者目录的旧冲刺／近战导出覆盖本轮。

## 状态

20 段动作已完成制作、导出，并保存到既有游戏资源路径。逐段保存记录见 `imported.json`。桥回执为 `Saved/pkm17-import-base-01.txt`、`Saved/pkm17-import-vertical-01.txt`、`Saved/pkm17-import-canted-01.txt`、`Saved/pkm17-import-prism-01.txt`、`Saved/pkm17-import-angled-01.txt`，五批均返回成功。
按用户规则未启动 PIE、截图、渲染或运行测试。实际观感与操作体验由用户测试。
