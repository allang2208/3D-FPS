# 矿镐视模骨架恢复（2026-10-22）

修复打包阻塞 P0：`SK_Harvest_Pickaxe_Skeleton` 自 2026-09-13 首次导入起从未保存到磁盘，导致 Cook 断言崩溃。

**本轮只新建了一个 Skeleton 包。** 未改动矿镐网格、五条动画、任何 C++、任何配置或存档；未启动 UE 编辑器；未运行 Cook 或打包；未做游戏内验收。

## 根因

2026-09-13 的握持动作导入（`SourceAssets/ProductionToolGrip20260913/`）保存了 15 个包，`import_receipt.json` 的 `saved` 数组里**没有任何 Skeleton 包**。导入器只在内存里建了骨架，从未落盘。

后果：`SK_Harvest_Pickaxe` 与五条 `A_Harvest_Pickaxe_*` 一直引用一个不存在的包。编辑器里不会立刻报错，所以潜伏了六周；第一次真 Cook 才变成硬失败——`AnimSequence.cpp:2172` 的 `!Hash.IsZero()` 断言，`Error_UnknownCookFailure`，退出码 25。

这不是新缺陷。2026-09-19 修斧头时已经在 [战锤/斧头替换记录](../../Docs/Weapons/battle-axe-replacement-20260919.md#L44) 里写明"未改动的矿镐同样如此"，当时只修了斧头那半边。

## 为什么是复制而不是重导

重导网格会连带改动绑定姿势、材质槽、权重和五条动画的压缩数据。本轮按用户要求**不动现有动作机构**，所以先证明"两个骨架是同一个骨架"，再复制。

`compare_rest_pose.py` 用 Blender 5.1 分别导入两个视模 FBX 导出，比对全部骨骼的静置变换：

| 指标 | 结果 |
| --- | --- |
| 共有骨骼 | 100 |
| 只在斧头 | 0 |
| 只在矿镐 | 0 |
| 静置变换不同 | 0 |
| 父级关系不同 | 0 |
| **完全相同** | **是** |

原始日志：`rest_pose_compare.json`。

两个 FBX 也确实都含完整的 UE5 Manny 骨骼名集合（`VM_Root`、`WPN_root`、`pelvis`、`spine_01`–`05`、`clavicle`、`upperarm`、`lowerarm`、`hand`、五指三节、`ik_hand_*`、各 `*_twist_*`），逐名核对零缺失。

结论：矿镐的五条动画就是照着这套骨架制作的，复制斧头骨架到缺失路径可以无损恢复引用。

## 执行

`Tools/ProductionTools/restore_pickaxe_skeleton.py`（后台 Python commandlet）：

1. 前置检查：源骨架存在、目标**必须不存在**（脚本从不覆盖）。
2. 复制 `/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe_Skeleton` 到 `SK_Harvest_Pickaxe_Skeleton`。
3. 显式保存。
4. 卸载内存副本后重新加载，比对骨骼名集合。

`Tools/ProductionTools/run_restore_pickaxe_skeleton.ps1` 负责批次互斥（`Local\CodexUeMcp-Port-8000`）、编辑器占用检查、目标已存在检查，并在保存后**另起一个进程**做二次验收。

## 结果

新包：`Content/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton.uasset`，22,813 字节，SHA-256 `D984F33722251A190689153F32B3CAF14E23F62D8033791EEE23CA7F0E0FEE7D`。

新进程读回（`fresh_readback.json`，`stage: verified`，`errors: []`）：

| 检查 | 结果 |
| --- | --- |
| 包在磁盘上 | 是，22,813 字节 |
| 加载为 Skeleton | 是 |
| 骨骼数 | **101**，与斧头骨架 101 **一致** |
| 骨骼名集合 | 98 个可识别 token，与斧头**完全一致** |
| `SK_Harvest_Pickaxe` 骨架引用 | 已解析到新包（修复前为 `None`） |
| `A_Harvest_Pickaxe_Idle` | 已解析，1.6 s |
| `A_Harvest_Pickaxe_Walk` | 已解析，0.8 s |
| `A_Harvest_Pickaxe_Equip` | 已解析，0.32 s |
| `A_Harvest_Pickaxe_Swing` | 已解析，0.68 s |
| `A_Harvest_Pickaxe_HitRecover` | 已解析，0.44 s |

五个时长与 `authoring.json` 里登记的 clip 时长逐项吻合。

## 未改动证明

目录内 16 个原有包的 SHA-256 在修复前后**逐字节一致**：

| 包 | SHA-256 |
| --- | --- |
| A_Harvest_Axe_Equip | A561AC08…6237C42 |
| A_Harvest_Axe_HitRecover | 74C52B3E…E1760C |
| A_Harvest_Axe_Idle | 88F26677…E68D17E |
| A_Harvest_Axe_Swing | 291A211A…EEEEFD13 |
| A_Harvest_Axe_Walk | E93C1CE9…343124C |
| A_Harvest_Pickaxe_Equip | 8AF5B5B1…F855F13 |
| A_Harvest_Pickaxe_HitRecover | 6F0C6958…B66E664B |
| A_Harvest_Pickaxe_Idle | 1F21B529…2F35DDF0 |
| A_Harvest_Pickaxe_Swing | C9D238FF…1FE097FED |
| A_Harvest_Pickaxe_Walk | 9AD65601…C2C4BD1 |
| M_Harvest_Axe | 54BF8DA3…AA6F7898 |
| M_Harvest_Pickaxe | 42F9CEA6…B27AB2 |
| SK_Harvest_Axe | B856D945…CA9801 |
| SK_Harvest_Axe_Skeleton | D1CC9BA3…4F2F1BD0 |
| SK_Harvest_Pickaxe | B2DDC8C5…B24095338 |
| S_Harvest_Swing | 3954F92C…6CE9C0E7 |

完整散列见各回执与 `restore.log`。C++、`.ini`、`production_tools.json` 与所有其它内容零改动。

## Cook 复验（2026-10-22，用户关闭 UE 后执行）

编译：`Tools/Build/Build-Editor.ps1` → `Result: Succeeded`（7.64 s，`Target is up to date`）。

Cook：`Tools/Build/Build-Package.ps1 -Configuration Development -Profile core-measurement`，
四次地图全量。**本次 Cook 未跑完** —— 在 5420/16635 处内存耗尽退出：

```
LogWindows: Error: appError called: Fatal error: Ran out of memory allocating
4194306 (4.0 MiB) bytes ... Last error msg: 页面文件太小，无法完成操作。
```

本机 31.7 GB 物理内存、提交上限 63.5 GB，执行时 Apex 占 8.8 GB、并行会话另有编译器占用约 3 GB，
Cook 峰值约 8.24 GB 时触发。**这是运行环境的内存限制，不是本次资产改动引起的**，也没有证据显示与矿镐有关。

### 修复前后逐项对照（同一份 Cook 日志口径）

| 失败信号 | 9/23 基线 | 10/22 修复后 |
| --- | --- | --- |
| `has a dependency on package`（ProductionTools） | **6** | **0** |
| `Animation Compression request for A_Harvest_Pickaxe` | **9** | **0** |
| `Skeleton == nullptr` | **9** | **0** |
| `Zero key hash compressed animation data` | **5** | **0** |
| `Assertion failed: !Hash.IsZero`（`AnimSequence.cpp:2172`） | **2** | **0** |

四类失败信号合计 **25 条全部归零**。

### Cook 产物直接证据

修复后的 Cook 在磁盘上真正产出了骨架包：

```
Saved/Cooked/Windows/FPSGAME/Content/Items/ProductionTools/GripMotion20260913/
    SK_Harvest_Pickaxe_Skeleton.uasset     3132 bytes
    SK_Harvest_Pickaxe_Skeleton.uexp      10871 bytes
    SK_Harvest_Axe_Skeleton.uexp          10871 bytes   ← 对照
```

两个骨架的 Cook 载荷**长度完全相同**；逐字节比对仅有末尾 **16 字节**不同，
位置在包尾的 GUID／随机盐区，属 UE 每包独立生成的正常差异。骨骼数据本体一致。

这比"日志里没有报错"更强：它证明这个包真的被 Cook 处理并写入了产物。

### 仍未完成

- **整次 Cook 没有跑完。** 上述对照只覆盖到内存耗尽为止的进度，**不能声称"Cook 通过"**。
  要拿到完整的 `ExitCode=0`，需要在空闲机器上重跑，或提高页面文件上限（当前自动管理，改它需重启系统，本轮未动）。
- 未曾出现的 8 条 `Wolf/Textures` 缺失与本修复无关：9/23 基线里就有同样的 8 条，是既有问题。
- 没有进游戏看镐的挥动观感。

### 补充：这批旧矿镐资产当前不在运行路径上

`Content/ColdSteelData/production_tools.json` 里 `tool_pickaxe` 实际使用
`RusticPickaxe20260919` 的视模与动作前缀（`A_RusticPickaxe_`），
`GripMotion20260913` 的 `SK_Harvest_Pickaxe` 与五条 `A_Harvest_Pickaxe_*` 目前不是运行时取材对象。

但该目录仍在 `+DirectoriesToAlwaysCook` 内，缺失依赖照样会让整次 Cook 断言失败，
所以这次修复对打包仍然必要；它修的是打包阻塞，不是游戏内表现。

## 建议的后续确认

1. 在内存空闲时重跑完整 Cook，确认 `ExitCode=0`。
2. 若仍内存不足，可临时提高页面文件上限（需重启）或关闭占用大户后重试。
3. 进游戏装备矿镐，确认当前实际使用的 `RusticPickaxe` 动作表现不受影响（本修复未触碰它）。

## 复跑与回退

- 重跑必须先删除新包，脚本检测到目标存在会主动拒绝。
- 回退：删除 `SK_Harvest_Pickaxe_Skeleton.uasset` 即回到修复前状态；该包是唯一新增文件，不牵动其它资产。
