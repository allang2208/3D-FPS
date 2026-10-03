# 快速近战：动作周期、体力成长与数值 — 2026-09-26

## 当前规则

- 快速近战取消独立技能冷却。蓄势、释放和 recover 收手全部完成后，可以再次发动；动作期间重复按键不会重启动作、重复扣费或重复获得施放修炼。
- 快捷栏沿用原 CD 遮罩与数字显示，但数据来自本次实际武器动作。剑类按当前 PommelStrike 片长、0.20 s 蓄势重映射和施放时攻速计算；手枪、双持、步枪按已选 clip 计算；ASH-12 同步其分段播放速度和实际命中停顿。
- 动作开始时统一扣一次体力。普通剑挥击消耗不再叠加到快速近战；结束或被中断后清除动作占用，已消耗体力不退还。
- 基础体力消耗 `15 × (1 − 0.02 × (等级 − 1))`。1 级为 15，20 级为 9.3；再乘装备近战体力倍率和当前临时体力倍率。该成长不会改变动作周期。
- 伤害公式各项降为原来的 20%：`(5 + 等级 + 力量 × (1 + 0.02 × 等级)) × 当前武器快速近战伤害倍率`。
- 取消技能附加眩晕，命中改用 `ReceiveMeleeKnockback`。不能继续调用秒数为零的 `ReceiveStun`，因为该函数仍会清韧性并打断攻击。
- 基础击退由 100 cm 改为 50 cm，继续乘装备快速近战击退倍率。因此例如原 1.5 倍的配重修正由 150 cm 变为 75 cm。
- 单次技能的范围与施放/击杀修炼沿用现有数据；技能详情、升级提示和快捷栏体力不足提示使用同一份实时数值。

## 运行与存档

旧 `QuickCombatCooldown` / `QuickCombatCooldownDuration` 字段名继续用于兼容已有存档，在运行中承载剩余动作时间和完整周期。加载存档时清除旧 12 秒冷却与中断动作标记。其他技能的冷却缩减、开发用无 CD 开关不会缩短快速近战的实际收手阶段。

动作时钟在内存中更新，不在每一帧或每次起手/结束时同步写盘；体力及修炼沿用现有自动保存与升级保存入口。

## 修改入口

- `Content/ColdSteelData/skills.json:quickCombat`：数值权威入口。
- `Skills/ColdSteelSkillTypes.h`、`ColdSteelSkillRules.cpp`、`ColdSteelSkillModel.cpp`：解析、成长、体力和动作占用。
- `Skills/FPSQuickCombatComponent.*`：枪械动作时钟、实际停顿、纯击退。
- `Weapons/RuneSwordComponent.*`：剑类实际周期与一次体力扣除。
- `UI/ColdSteelProfileRuntime.cpp`：旧存档清理与 CD 缩减隔离。
- `UI/ColdSteelQuickSlot.cpp`、`ColdSteelSkillPage.cpp`：快捷栏与技能说明。

以上源码路径均以 `Source/FPSGAME/` 为基准。

修改前备份：`Saved/TaskBackups/QuickCombatCycle-20260926-180810/`。

本轮后台 Game 构建完成了相关快速近战源文件的编译，但整次构建失败，未链接新运行文件：

- `Dungeons/AuthoredDungeonGenerator.cpp:530` 的 `FSocket` 名称冲突及其后续错误。
- `Dungeons/DungeonRoomEncounter.cpp` 中从 `ElementType` 推导 `auto*` 失败。
- `FPSGAMECharacter.cpp:2314` 引用弓组件尚不存在的 `ShotSpread()`。
- `Production/ProductionFallingTree.cpp:32` 在 Game 目标中调用不可用的 `USkeletalMesh::GetNaniteSettings()`。

上述错误涉及本次快速近战范围之外的并行工作，保留现场。构建日志：`Saved/BuildEditor/quick-combat-cycle-game-20260926-1812-console.log`。

## 关闭 UE 后的构建续接

用户关闭交互编辑器后，已有 Editor 全量编译包含上述快速近战修改。剩余地牢 `FSocket` 类型歧义随后由并行工作补上 `AuthoredDungeon::` 限定；复用已在进行的构建，不重复启动编译、不覆盖其修改。

最终 `FPSGAMEEditor Win64 Development` 构建成功，生成正常命名的 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。成功记录：`Saved/DungeonV4_20260926/build-editor-02.log`，`Result: Succeeded`，13.22 秒。本节更新的是 Editor 目标交付状态，上方失败记录保留为先前 Game 目标构建历史。

未自动打开编辑器、进行 Live Coding、运行游戏、回归测试或视觉验收。下次打开 UE 将加载本轮生成的 Editor 模块，运行手感交由用户测试。
