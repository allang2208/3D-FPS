# 掉落枪械读档触发 BeginPlay 崩溃

## 触发与根因

玩家存档中存在当前地图的掉落武器。角色 BeginPlay 调用 AttachPawn / RefreshDrops，BuildWeapon 在 FPreviewScene 中生成临时 AFPSGAMECharacter 来复制当前枪械装配。预期只建立静态展示，实际进入临时角色 BeginPlay，并在空 GameInstance 上调用 GetSubsystem，访问地址 0x158。用户报告模块为 2026092056。

引擎 Actor.cpp 的 PostActorConstruction 使用全局 `BeginPlayCallDepth > 0 || World->HasBegunPlay()`，所以“预览世界没有开始游戏”不能阻止嵌套生成角色进入 BeginPlay。该条件和用户栈相互印证；资产损坏或手指动画问题不能解释这次空指针调用链。

## 修复

- AFPSGAMECharacter::BeginPlay 对 GamePreview、EditorPreview 和没有 GameInstance 的世界跳过玩家初始化，并禁用角色 Tick。正常游戏仍按原路径绑定存档和装备。
- BuildWeapon 用 ON_SCOPE_EXIT 在预览世界释放前 Destroy 临时角色，包含资产校验失败的提前返回路径。
- 单独增加初始化保护还不够：第一次新进程测试发现临时组件被延迟 GC，UFPSCombatHealthComponent::EndPlay 在预览世界已销毁后访问世界（0x280）。明确销毁顺序修复了这个后续问题，未改变生命组件逻辑。

## 复现与验证

运行 `Tools/Validate-PickupBeginPlay.ps1`。脚本用独立 PickupRestoreAudit 存档启动两次：第一轮创建并保存带共振前握把、全息、弹鼓和枪口配件的 M4，以及 AKM；第二轮全新进程从这些地面物品启动，检查模型恢复和玩家 Tick，再完成掉落、拾取、背包满、保存失败、仓库交互、距离遮挡和读档回归。不会使用或删除 ColdSteelPlayer 存档。

最终运行 `PickupRestoreAudit_2993`：

- Editor Development 原生编译成功，build-verified.log。
- seed：25 检查、0 失败，正常退出；实际加载 2026092993 模块。
- restore：27 检查、0 失败，正常退出；实际加载并行构建产生的 2026093010 模块，包含本修复。
- 新进程第 0 帧记录两个 WeaponPreview 初始化跳过标记，恢复 M4（6 个附件组件）及 AKM；随后恢复检查和玩家 Tick 检查通过。
- 已查看落地 M4 的真实游戏截图，完整枪械、弹鼓和镂空前握把可见，没有携带第一人称手臂。
- 未进行打包版本验收。引擎实验 Python Toolset 插件的启动报错独立于本问题，未阻止两轮游戏验收。

证据：`Saved/PickupBeginPlayFix/PickupRestoreAudit_2993/{seed,restore}.log`；截图 `Saved/PickupBeginPlayFix/landed-model-final.png`。此前只修初始化的失败保留在 `Saved/PickupBeginPlayFix/restore.log`。一次下落检查遇到加载卡顿，已将检查改为限时等待真实物理下落；实际重力与碰撞代码未修改。原文件快照保留在同一证据目录的 `*.before.cpp`。
