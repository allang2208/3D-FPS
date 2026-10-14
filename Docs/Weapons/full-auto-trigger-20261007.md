# 全自动扳机（传说级改造）

配件 ID：`legendary_full_auto_trigger`；槽位：`trigger`。

适用当前目录的半自动手枪 M1911、Pit Viper 2011。G18、Dan-Wesson 715、RSH-12 及其他枪械不提供该选项。沿用原枪扳机网格和动画，不制作或加载新扳机模型。

## 使用

- 在枪匠的扳机栏选择传说级「全自动扳机」并应用。与同槽其他扳机互斥。
- 两种射击模式均使用 `fire_interval_mult: 0.8`；不叠加旧扳机的倍率。未计技能等修正时，M1911 为 144 ms，Pit Viper 2011 为 120 ms。
- 安装后默认为全自动。V 切换主手的半自动／全自动；H 切换副手。
- 单持及双持主手使用鼠标左键；双持和法杖副手沿用鼠标右键。全自动按住连续射击，松开停止。
- 两把同型号枪也以各自 InstanceId 分开保存。只改造一把时，另一把的模式、间隔、输入和冷却均保持自己的状态。
- 模式切换后需要一次新的鼠标按压。弹药栏分别显示本手模式及切换键；物品提示显示保存的模式。
- 拆除或更换为其他扳机会清除该实例的模式记录；重新安装默认全自动。普通属性刷新、换弹及其他配件变更保留选择。

## 接入

`FullAutoTrigger.h/.cpp` 定义适用范围、实例模式解析、输入切换与提示。模式存入物品 Data 的 `pistol_fire_mode`，只有已安装改造时才可启用；安装时写入 `auto`。旧实例缺失模式字段时默认全自动，玩家明确保存的 `semi` 继续保留；未知值仍按半自动处理。

切换使用现有 `SyncRuntime → Snapshot → CommitState` 保存事务。先保存成功再发布角色状态，不直接修改只读 JSON 缓存；失败时保持原模式。主手与双持每手在档案发布时缓存模式，开火循环只读取布尔值，不读取 JSON。双持沿用每手独立的弹药、NextShot、换弹和输入门控；自动射击沿用 G18 的有界补射逻辑。

图标共享键为 `trigger_legendary_full_auto_trigger`，PNG 位于 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/`；同名 Texture2D 由作者目录 `Integration/import_icon.py` 后台导入保存。传说品质沿用枪匠现有分组和边框。

## 初次接入检查与交付记录

- 已检查单持、双持、法杖副手的输入归属、配件快照、间隔计算、模式移除和实例保存路径。
- 定向目录检查记录在 `SourceAssets/LegendaryFullAutoTrigger20261007/Integration/scope_check.json`：新选项仅进入两把适用手枪、数值／效果一致、既有选项保留、共享 PNG 与设计源一致、切换键映射唯一。
- Editor／Game 构建结果见同目录 `build_receipt.json`；Texture2D 实际保存结果见 `import_receipt.json`。执行入口为 `build_and_import.ps1`，先等待已有 UBT 结束，不打开交互编辑器。
- 未启动游戏或 PIE；未进行射击手感、画面及联机验收。源码检查和构建不代表实机测试通过。

## 默认模式调整（2026-10-07）

按用户后续要求，安装及重新安装全自动扳机时写入全自动模式；已安装但没有模式记录的旧实例也默认全自动。已有明确半自动选择继续保留，V／H 切换方式不变。对应后台编译记录为 `SourceAssets/LegendaryFullAutoTrigger20261007/Integration/default_auto_build_receipt.json`，未追加运行测试。
