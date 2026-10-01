# 百目炉渣 AggressionV5：攻击意愿与距离

用户反馈攻击不够积极、需要贴得过近。这次排查角色的攻击状态机、公共冷却、行为树追击停止距离和实际伤害轨迹，并作针对性调整。

## 原因

- 原公共冷却在攻击启动时设为 2.5 秒，角色同时又等待完整动作与 0.16 秒恢复。横扫长 1.4 秒，因此结束恢复后仍需空等约 0.94 秒；重击也多等约 0.54 秒。
- 原近战、喷灰和冲锋范围为 210 / 300 / 400 cm。冲锋速度仅 210 cm/s，推进阶段只有 0.55–1.25 秒，理论距离约 147 cm，实际还受加速限制，无法可靠覆盖其启动距离。
- 大右掌伤害跟随骨骼轨迹，手掌向前最大约 90 cm，不能通过增大攻击启动距离就让手掌自动触及玩家。原追击停止距离也直接跟随近战启动距离，扩大参数后会停得更远。
- 原招式选择没有在选择冲锋时再次检查冲锋范围；特殊技能范围独立调整后，可能选择不能覆盖目标的技能。

## 调整

| 项目 | 原值 | 新值 |
| --- | --- | --- |
| 追击速度 | 280 cm/s | 340 cm/s |
| 近战启动距离 | 210 cm | 300 cm |
| 喷灰半径 | 300 cm | 450 cm |
| 冲锋启动距离 | 400 cm | 600 cm |
| 冲锋速度 | 210 cm/s | 650 cm/s |
| 冲锋加速度 | 1400 cm/s² | 3200 cm/s²，仅冲锋 |
| 冲锋推进时段 | 0.55–1.25 秒 | 0.45–1.25 秒 |
| 公共启动冷却 | 2.5 秒 | 1.25 秒，完整动作仍不可打断连发 |
| 攻击后恢复 | 0.16 秒 | 0.12 秒 |
| 喷灰 / 冲锋冷却 | 8 / 10 秒 | 5 / 5 秒 |
| 追击与前摇逼近停止距离 | 近战距离减 35 cm | 限定在 80–155 cm |

普通攻击会在横扫 0.52 秒、重击 0.80 秒之前向前逼近，接近目标后停止；前摇内以最大 180°/s 转向目标，进入有效打击阶段后锁定方向。冲锋前摇只追踪至 0.40 秒，随后按锁定方向推进，靠近目标、碰到墙体或离开可推进时段便停止。

推进沿用角色移动组件的胶囊扫掠、碰撞与楼梯处理，没有直接瞬移角色。横扫和重击仍使用大右掌的 48 / 60 cm 扫掠半径及原来的 0.54–0.73 / 0.84–1.00 秒伤害窗口。恢复结束立即刷新行为树判断，目标仍在范围内时可继续出招。追击奔跑按实际速度缩放既有 HeroHandV4 动作的播放速率。

## 文件与交付

- `Source/FPSGAME/Monsters/HundredEyedSlagMonster.h/.cpp`：该怪物参数、招式选择、前摇逼近、冲锋和恢复逻辑。
- `Source/FPSGAME/Monsters/MonsterCombatComponent.cpp`：仅该怪物的停止距离分支。
- `SourceAssets/HundredEyedSlagMeshy20260930/AggressionV5/Before`：修改前源码备份。
- `apply_live_defaults.py`：热编译成功后同步当前原生默认对象和已存在游戏世界中该怪物的旧默认值，保留用户定制值；不保存地图或资产。
- `Finish-NativeBuild.ps1`：现有编辑器与编译退出后，执行一次正式后台 Editor 构建；不关闭、不打开编辑器。
- `livecoding_result_20260930.txt`、`live_defaults_applied.json`、`native_build_status.json`：以实际结果记录为准。Live Coding 补丁和正式基础 DLL 构建分开记录；正式构建未显示 complete 时不可视为已完成。

本次 UBT 编译结果为 Succeeded，已生成 `UnrealEditor-FPSGAME.patch_1.exe/.pdb`，现有编辑器记录了 FPSGAME 模块重载及 HundredEyedSlagMonster 重实例化完成。当前原生默认对象已采用新参数。

整轮 Live Coding 仍返回 CompileNotStarted：旧 `FPSGAME-mp/Plugins/AutoFootstep` 与 AutoFootstepEditor 的热补丁链接出现 LNK2011 / LNK1120，属于同一热编译批次的其他模块。不能把主体模块成功当作整轮热编译成功。MCP 长请求同时超过 HTTP 等待时限；这次没有重复提交编译，实际编译与重载证据保存在 `livecoding_ubt.log` 和 `livecoding_editor_excerpt.log`。

正式后台构建由一次性进程等待现有编辑器退出后执行，状态以 `native_build_status.json` 为准。其目的为将源码生成基础 Editor DLL，避免只保留本次编辑器会话中的补丁；不会自动启动或重启 UE。

2026-10-01 00:02，正式 `FPSGAMEEditor Win64 Development` 后台构建完成，结果 Succeeded，35 个构建动作完成，耗时约 109 秒。基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已链接落盘；AutoFootstep 与 AutoFootstepEditor 也按当前项目路径完成普通模块链接，前述热补丁失败没有阻止本次正式构建。构建日志为 `Saved/BuildEditor/build-20261001-000050.log`，后台状态为 complete，native_build_pending 为 false。

沿用 HeroHandV4 网格、材质、骨架和动画资产，本次无需模型重导。未运行游戏、PIE、性能回归或画面验收；调整后的攻击手感与命中表现由用户试玩。
