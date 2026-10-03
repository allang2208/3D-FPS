# 符文剑初始化崩溃：Live Coding 补丁地址错误（2026-09-22）

## 现场与定位

用户报告进入游戏时崩溃。调用路径为角色 BeginPlay → RuneSwordComponent 装备刷新 → ModularSwordVisual::Apply → MeleeRuneVisual::Apply 第 61 行的 IsNativeGold 调用。

读取了现有三份 minidump，没有重新启动游戏复现：

| 进程 | 异常执行地址 | patch_0 加载基址 | 有效目标地址 |
| --- | --- | --- | --- |
| 44816 | `0x13598e95db0` | `0x13698e90000` | `0x13698e95db0` |
| 44672 | `0x23d7ffc5db0` | `0x23e7ffc0000` | `0x23e7ffc5db0` |
| 37100 | `0x26c25355db0` | `0x26d25350000` | `0x26d25355db0` |

三次异常均为 `0xc0000005`，ExceptionInformation[0] 为 8，即执行访问违例。异常地址均不在已加载的三个项目补丁内，且都比 patch_0 基址加 `0x5db0` 少 `0x100000000`（4 GiB）。通过 Windows DbgHelp 与 patch_0 的 PDB 解析，RVA `0x5db0` 正好是匿名命名空间内的 `IsNativeGold`，符号偏移为 0。

这定位到 Live Coding 补丁间的无效代码跳转。位移截断是与证据吻合的机制解释；转储没有保留该函数的运行时补丁字节，因此没有声称已逐条还原引擎内部补丁写入过程。现有证据不支持将此崩溃归为材质空指针或巫婆网格/蒙皮问题。

LiveCodingConsole 日志显示，每次启动上述子进程都会重新安装 patch_0、patch_1、patch_2。仅重新启动游戏窗口仍会继承这一补丁链。

## 本任务操作的归因

- 10:13 的巫婆任务热更新生成 patch_1，UBT 实际编译了 MeleeRuneVisual、ModularSwordVisual、WitchRebuiltAuthoring 三个源文件。该次热更新影响并不限于巫婆。
- 10:25 的后续热更新生成 patch_2，不由本对话调用；它再次包含上述源文件，并编译 M4MeleePreview。
- 基础 UnrealEditor-FPSGAME.dll 仍为 09:29:25 版本。
- 不能仅凭调用栈中的 patch_2 判定早先热更新完全无关；可确认的直接故障是组合补丁中的无效函数跳转。

## 修复范围

保持当前符文金色效果、护手遮罩、装备数据与巫婆修改。此故障无需通过删除 IsNativeGold 或增加材质空指针判断来掩盖。

恢复方式：正常退出编辑器与其 Live Coding 会话，保留故障证据并移出本次故障补丁，运行 Tools/Build/Build-Editor.ps1 的常规 FPSGAMEEditor 构建，使当前源码进入基础 DLL，再正常打开项目。必要构建会包含该目标的所有待编译改动，不将其描述为只编译一个功能。

关闭前有 6 个手枪弹药图标和 3 个 5.8 mm 弹药图标未保存。用户明确批准保存全部弹药图标后，已保存这 9 项，并正常退出编辑器。没有丢弃脏包或强制结束进程。

## 证据与状态

本机证据目录：`Saved/Diagnostics/MeleeRuneCrash20260922/`。

- diagnosis.json：转储异常及补丁模块地址。
- evidence_manifest.json、Before/：原始转储、补丁、相关源码和日志的备份与 SHA-256。
- editor_state.json：关闭前的编辑器状态。
- close_for_cold_build.py：仅保存用户已批准的弹药图标，其他脏包或活动游戏会话会阻止退出。
- build_result.json、restart_result.json：常规构建和重新加载记录。

## 完成结果

- 已将本次故障链的 21 个补丁产物移至 `trash/melee-rune-livecoding-crash-20260922/patches-105502/`，该目录的 manifest.json 保留原路径、目标路径、大小和 SHA-256。
- `Tools/Build/Build-Editor.ps1` 常规构建成功；日志为 `Saved/BuildEditor/build-20260922-105502.log`。
- 本次构建编译 MeleeRuneVisual.cpp、ModularSwordVisual.cpp、M4MeleePreview.cpp、WitchRebuiltAuthoring.cpp，并链接正式 UnrealEditor-FPSGAME.dll，合计 7 个构建动作。
- 已重新打开 `/Game/GameMaps/L_Dungeon_Prototype`。本次启动参数 `-LiveCoding=false` 关闭自动开启 Live Coding，未改永久项目设置。
- 没有修改武器玩法源码或替换模型资产；修复的是故障补丁链及过期基础 DLL 的构建/加载状态。
- 没有运行 PIE 或游戏回归；构建成功与编辑器重新加载不等于游戏运行已验证，仍由用户测试。
