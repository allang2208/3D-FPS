# 枪械检视打断与重播（2026-10-02）

当前用户要求：合理区分指令；移动镜头、移动等常规动作不打断检视，明确的武器／占手交互仍可打断，再次按检视从头播放。

## 实现

- `AFPSGAMECharacter::InterruptWeaponInspection()` 仅在共享枪械状态 `Inspecting` 时执行。退出到 Idle，停止机械声音和未播放 cue，清除作者动画、动作时间、动画图动作权重与动作构图偏移，再恢复当前待机／瞄准姿态。
- 打断不调用正常动作完成路径：该路径把下一次射击时间推到原 clip 终点，提前退出会导致看似停止但仍然无法开火。打断保留原有射击冷却，不追加检视时长。
- 玩家控制器不再对所有原始按键和鼠标事件统一取消。由实际动作入口决定是否打断，释放、Repeat、无绑定键和空快捷槽不额外取消。
- 转动镜头、前后左右移动、冲刺、蹲起、普通跳跃、滑铲与疾避均保留检视。快捷栏绑定的疾避也遵循同一身体移动规则，附近批量拾取 Z 保留检视。
- 开火、瞄准、换弹／弹种轮盘、快速近战、特殊武器功能和检视入口保留主动打断；实际换装备由已有优先级清理接管。非空技能／物品快捷槽在分派前取消，确保施法、喝药能立即取得手部动作。
- E 命中可交互目标并分派交互时取消；菜单沿用统一的 `SuspendWeaponForMenu()`，补齐建筑抽屉入口。对空按 E 且没有技能绑定不打断。
- 普通跳跃及失败的翻越尝试保留检视。翻越／攀爬先允许检视参与目标探测，只有路径和对应动画均接受后才取消，以便双手抓扶；其他武器忙状态仍阻止翻越。空中抓边使用相同规则。
- 新的检视重置 `WeaponActionStartedAt`、状态年龄和动作采样起点，动画图和 SingleNode 两种路径都从零播放。

## 范围

当前所有使用角色 `InspectPressed` 的枪械共用该状态与动作时钟，按枪型加载自己的检视 clip，覆盖现有步枪、狙击枪、机枪、单持手枪／左轮及各握把动画派生。保持枪械骨架、动作资产、弹药、伤害、射速和真实射击冷却。

当前正式枪械入口包括 M4A1、HK416、AKM、A762、LMG201、SVD、PKM、QBZ191、ASH12、M16A2、M1911、G18、Pit Viper 和 DW715。部分枪型当前未加载检视 clip，本次统一已有检视动作的打断行为，没有额外制作动作资产。

双持手枪的检视目前按用户先前选择禁用，本次没有新增双持检视动画。剑、弓、法杖与采集工具的独立动作不由此枪械取消函数清理。

## 初次交付记录（此前的任意指令策略）

源码已落盘，后台 `FPSGAMEEditor Win64 Development` 正式构建成功（145 个构建动作，212.57 秒，退出码 0），已链接保存 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 与其依赖模块。

构建日志：`Saved/BuildEditor/build-20261002-200429.log`。等待现有原生构建结束后提交，未关闭任何外部进程。未启动或重启编辑器、游戏或 PIE，未执行测试或验收，由用户测试交付行为。

## 手枪提前结束修正

用户反馈：不操作其他指令，手枪检视也会提前结束。源码定位到此前新增的 MoveForward/MoveRight/Turn/LookUp 非零轴回调打断：UE 的 PlayerInput 先执行动作绑定，随后执行 Axis 绑定，本帧已经存在的轴值会取消刚进入 Inspecting 的动作；鼠标平滑还可能在原始输入归零后输出尾值。

当时改为玩家控制器在原始按键或鼠标事件到达时取消，移除四个逐帧轴回调的取消，以避免同帧旧输入结束检视。后续用户要求常规动作不中断，因此该原始事件取消现已移除，改用本文件顶部的动作分类；检视从零重播保留。

手枪检视时钟读取实际 clip 长度，动作与状态使用同一世界时间，默认速率为 1、起点为 0。M1911／G18／Pit Viper 普通与空仓、DW715 普通检视制作记录均约 4.9667 秒；未发现缩短动画长度的代码问题，因此本次不修改动画资产。已有编辑器只读查询时无运行中的 game world，没有运行重现测试。

这次修正源码已保存。现有 UE 会话的 Live Coding 因 188 个构建动作超过上限 100 而取消（`LiveCodingLimitError`），未应用热补丁。MCP 请求记录为 `Saved/Diagnostics/PistolInspectEarlyEnd20261002/live-compile-response-1.txt`。

UE 关闭后，复用串行等待期间已经进行的 `FPSGAMEEditor Win64 Development` 正式构建：198 个构建动作，264.23 秒，`Result: Succeeded`。日志包含 `FPSGAMECharacter.cpp`（99/198）和 `FPSGAMEPlayerController.cpp`（110/198）的编译，以及 `UnrealEditor-FPSGAME.dll`（197/198）的正式链接，修正已进入 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。构建记录已保存到 `Saved/Diagnostics/PistolInspectEarlyEnd20261002/shared-editor-build.log`。

该轮构建已覆盖本次两个源码文件，因此停止本任务自己的空闲排队辅助进程，未追加重复构建。未启动、重启或结束 UE 编辑器及游戏，未运行实机测试，由用户测试。

## 常规动作分类调整交付

本轮源码已保存：控制器直接消费的交互／技能指令明确取消，角色常规移动入口不取消；翻越在实际开始时取消，建筑抽屉接入菜单动作释放。枪械动作时长、声音、射击冷却和现有动画资产沿用原实现。

用户关闭 UE 后执行后台 `FPSGAME Win64 Development` 正式构建。本轮日志包含 `FPSGAMECharacter.cpp`、`FPSTraversalAir.cpp` 的编译，但完整构建失败：共享 `ColdSteelPlayerState.cpp` 调用了尚未提供的联机技能接口，包括 `NetCommitWall`、`NetCommitZone`、`NetRelease`、`SpawnVolleyForCast`、`NetCastCancelled` 和 `NetCastRejected`。这些并行接入文件保持原状，未添加空实现或删除调用。

日志：`Saved/BuildInspectRoutineInput20261002/FPSGAME-20261002-224819.log`；结果 `Failed (OtherCompilationError)`。当前交付为已保存的源码，正式 Game／Editor 运行模块尚未完成本轮更新，需这组技能接口补齐后继续构建。未启动编辑器或运行游戏测试，由用户自行测试。

## 后续正式构建完成

共享技能接口后续补齐后，撞门停顿调整所需的后台正式构建已成功完成当前工程的 Editor 和 Game 目标，前面的检视分类修改也已进入普通运行模块。日志分别为 `Saved/BuildEditor/build-20261002-234440.log`（`UnrealEditor-FPSGAME.dll` 正式链接成功）和 `Saved/DoorPushHold250ms20261002/FPSGAME-20261002-234533.log`（`FPSGAME.exe` 正式链接成功），结果均为 `Succeeded`。上述首次失败记录保留为历史；现有模块已更新，未启动 UE 或运行游戏测试。
