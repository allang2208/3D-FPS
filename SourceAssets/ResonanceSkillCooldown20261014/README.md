# 共鸣符文冷却调整

正式数据源：`Content/ColdSteelData/melee-gunsmith.json` 的 `resonance_rune.stats.skill_cooldown_mult = 0.85`。战锤继续直接引用剑类通用符文列。无模型、图标或材质变更，不需要重导入资产。

源码结算与显示说明见 `Docs/Weapons/resonance-all-skill-cooldown-20261014.md`。

本次修改全部落盘后，已有同项目 Game 构建在 2026-10-14 19:48:47 启动。首次 Game 构建被并行修改的法杖读数私有访问、地牢生成头文件不同步及临时缺失的战锤头文件阻断；随后 Editor 构建被砸地特效的 `TObjectPtr` 循环阻断。未修改这些并行文件，保留两份初次日志。等待共享构建恢复后，最终 Editor／Game 均取得 `Succeeded`，日志见 `shared-editor-build-final.log` 和 `shared-game-build-final.log`。

本任务没有关闭或启动编辑器、触发 Live Coding，也没有联系其他任务。自己的 Game 提交在资源前置条件处返回 75，未启动重复 UBT；最终采用全部源码落盘后的共享完整目标构建结果。

日后需要重建时，在 Editor 关闭且没有 UBT／cl／link 构建占用后，可在工程根目录执行正常增量构建：

```powershell
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReloadFromIDE
```

构建不等于测试；本次不运行游戏、UI／联机验收或回归。
