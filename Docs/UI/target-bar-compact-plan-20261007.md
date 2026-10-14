# 怪物目标栏紧凑版（2026-10-07）

根据用户反馈减少顶部目标栏对战斗视野的遮挡。本版覆盖同日首版目标栏的纵向布局，保留冷钢配色、共享资源轨道与长度过渡。

- 面板仍居中于罗盘下方，宽度上限 440px；罗盘底部到面板由 23px 收至 6px。
- 名称／等级与命中伤害占 24px 首行；名称使用 14px，伤害数字保留 14px。
- 常规宽度下，生命和韧性各占 20px，标签、渐变轨道、实时数值横向排列；生命轨道 8px、韧性 6px，资源数字 12px。
- 2026-10-09：生命和韧性共用 144px 右侧数值列，轨道起点与长度统一。数值位数变化或破韧／回韧倒计时出现时不再各自挤压条长；长数值沿用单行省略，窄窗仍使用上下分行的全宽轨道。

2026-10-09 等长调整交付：源码与本文已保存。沿已运行编辑器，通过桥提交 `LiveCoding.CompileSync`；UBT 编译阶段成功（含 `ColdSteelCrosshair.cpp`），但补丁链接被 `BoundCongregate.cpp.obj` / `BoundCongregateTentacle.cpp.obj` 的 LNK2019／LNK2001 未解析符号及 LNK1120 阻塞。`Saved/Logs/FPSGAME.log` 于 UTC 2026-10-09 14:35:18 明确报告 Live coding failed；本次未更新基础 DLL，也未应用到当前编辑器。保留现场，未改动无关怪物模块、未启动或关闭编辑器、未运行游戏测试。调用记录：`Saved/BuildEditor/target-bars-equal-20261009-receipt.txt`。
- 窄窗不足 340px 时，资源行使用 28px 的标签／数值＋细轨道布局，优先保留可读性。
- 基础／附加伤害各占半行，共用 20px；窄窗使用两条 18px 行。保留伤害类型和实值。
- 状态区取消单独标题与大分隔留白，使用 20px 标签、22px 行距，仍显示原有最多六个效果及溢出数量，不改变效果采集。
- 常规宽度、生命＋韧性无附加内容时，面板由 128px 收至 68px；一行状态加伤害拆分时由 224px 收至 110px。以上是布局参数，不是截图测量。
- 数据、显隐、无目标／击杀状态、20Hz 数据调度与只读 NativePaint 沿用现有路径；不新增输入、资源、Tick 或存档字段。

范围：`ColdSteelCrosshair.cpp`、`ColdSteelHUDLayout.h` 及对应设计规则。未启动、关闭或重启编辑器；未运行游戏测试或截图。

首次交付：沿用现有编辑器，经 `mcp_call_codex.ps1` 批次互斥调用 `LiveCoding.CompileSync`；`Saved/Logs/FPSGAME.log` 在 `2026.10.07-14.49.52:270`（UTC）记录 `Live coding succeeded`。当时仅热补丁完成。

正式构建补齐：用户随后告知已关闭 UE。等待期间共享的 `FPSGAMEEditor Win64 Development` 常规构建完成，日志 `SourceAssets/M25VortexCoffer20261004/AudioV1/build-FPSGAMEEditor-20261007-145929.log` 明确包含 `ColdSteelHUDNavigation.cpp`、`ColdSteelCrosshair.cpp` 编译、`UnrealEditor-FPSGAME.dll` 链接及 `Result: Succeeded`。正式 DLL 于本地时间 2026-10-07 23:02:29 更新，晚于紧凑版两份源码（22:47:58／22:48:44），本版已进入基础 DLL。已取消本对话重复等待的构建；未启动编辑器、游戏或测试。
