# 悬钟死亡重力接触修复 V26

2026-10-07。用户反馈悬钟死亡后向天花板内收缩，没有自然掉落到地面。

## 归因与修改

当前连续软体入口已停用悬挂角色 Tick、角色移动、活体动画和刚体模拟；尸体独立求解，重力沿世界 -Z。没有发现死亡后仍由倒挂移动持续拉回的代码路径。

`UM14SoftBodyDeathComponent::RefreshContact` 原先从每个节点上方 35 cm 向下找地面。贴近薄天花板时，起点可能越过板顶，命中向上的天花板上表面。随后 `ProjectContacts` 把下方节点向上推到这个错误“地面”，可把相邻组织牵拉进天花板。这是源码中与反馈相符的接触判定问题，未进行游戏复现测试。

- 探地射线改为从当前节点位置向下，保持原 650 cm 查询范围。
- 排除射线起点穿透和节点上方的命中，只接受节点下方的朝上支撑面。
- 保留原球扫掠处理实际墙面、天花板和初始穿透接触。
- 0.12 秒的初始支撑固定现在还要求真实接地；倒挂角色的低位节点不会仅因参考模型高度低而被固定在空中。

修改位于共享求解器 `Source/FPSGAME/Monsters/M14SoftBodyDeath.cpp`，不新增类或属性，不改代理、模型、减面、动画、音效、攻击及掉落奖励。已有并行尸体 LOD 修改原样保留。前版本源码备份在 `SourceAssets/HangingBellM09Meshy20261003/DeathGravityV26/Before/`。

## 接入状态

源码及常规 Editor/Game 构建已完成落盘，两个目标最终退出码均为 0。`Binaries/Win64/UnrealEditor-FPSGAME.dll` 和 `Binaries/Win64/FPSGAME.exe` 已更新。用户保存并关闭 UE 后使用 `Tools/HangingBellM09/Build-DeathGravityV26.ps1` 完成构建，未重新打开编辑器。之前 `CompileLiveCoding` 返回 `CompileNotStarted / Live coding canceled`，该未生效的热编译已由本次常规构建替代。

首轮 Editor 构建遇到现有 `MonsterAIController.cpp` 的 C4456：内层 `M27` 局部变量遮蔽外层同名变量。仅将该内层变量重命名为 `EncounterMantis`，保留原行为与其他并行改动，然后完成两个目标构建。构建入口沿用 UE 批次互斥，等待已有后台 commandlet 自行结束，没有结束其他进程。

编译及保存回执放在 `SourceAssets/HangingBellM09Meshy20261003/DeathGravityV26/Records/`。未启动游戏，未追加测试、截图或渲染，实际死亡表现交由用户体验。
