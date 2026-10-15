# 法杖魔法与魔法书专注状态栏

## 范围与布局

补全 `ColdSteelAmmoReadout` 的法杖分支，沿用右下锚点、360px 外壳、共享字体、分隔线和 HUD 避让。第一行左列为“魔法”及当前／上限，右列为“每秒恢复”及数值；第二行左列为“魔法技能冷却缩减”及百分比，右列为“魔法回满时间”及秒数。标签保持 12px 单行，数字沿用 24px，状态文字为 16px；外壳随内容增高。

单杖、法杖＋手枪和法杖＋书共用主手展示。副手手枪仍使用原弹药栏。副手书显示书名、右键专注状态和进入专注后的施法速度、魔法消耗、移动速度及受击代价；未生效时用次级色，进入完成后按真实专注状态强调。换出法杖时整行魔法数据折叠，换出书时整组书效果折叠。

## 数据与状态

- `UColdSteelStatusModel::StaffManaReadout` 提供只读快照：魔法当前／上限、实际每秒恢复、当前装备提供的通用法术冷却缩减及回满时间。复用现有 Derived、CraftEffect、SetEffect 和符文倍率，不计算整套法术伤害。
- 回满时间按当前缺额估算，包含尚未结清的击杀恢复滴灌，滴灌结束后按常规恢复速度继续。满值或无限魔法为 0.0s，死亡为暂停恢复，恢复率不足以回满时显示“不恢复”。估算不预支未来药水、击杀或其他事件。
- 冷却缩减表示装备／套装的通用比例，保留现有最低 20% 冷却倍率；技能自身等级冷却不混入。无冷却开发选项显示 100%。
- 魔法书使用当前武器组的 `ActiveSpellbook`、物品缓存中的 `focusEffects` 和 `USpellbookComponent` 状态。效果为进入专注后的预览，开书完成才显示生效，收书／打断立即退出生效显示。
- 沿用 HUD 的现有刷新，复用控件，只在文字变化时更新；无新 Tick、输入、计时器、事件绑定或存档写入。菜单让位与销毁沿用原 HUD。

## 交付

仅源码和必要后台构建，无新增美术或 UE 资产。未要求预览、检查或测试，由用户测试。

### 本轮落盘与构建结果

- 已落盘：`ColdSteelAmmoReadout.h/.cpp`、`ColdSteelStaffReadout.cpp`、`ColdSteelMagicReadout.h`、`ColdSteelMagicReadoutModel.cpp`、状态模型接口，以及正式 UI 规则和个人／工程 SKILL 镜像。
- 初次 Game 构建未完成；本次组件访问问题已修正，另遇共享地牢头文件变化及制作工具缺失头文件。新数据文件补充直接依赖的 `Engine/HitResult.h`，不依赖预编译头偶然提供声明。
- 随后已有的完整 Editor 构建纳入本次修改：`Saved/BuildEditor/build-20261014-195719.log` 的第 12、37、57 个编译动作分别完成 `ColdSteelAmmoReadout.cpp`、`ColdSteelMagicReadoutModel.cpp`、`ColdSteelStaffReadout.cpp`，这些文件无编译错误。
- 整轮 Editor 构建最终为 `Failed (OtherCompilationError)`：`Production/WarhammerSlamFXSubsystem.cpp:191-193` 出现 `TObjectPtr` 到 `auto*` 的类型推导／转换错误。本轮未修改该制作工具文件，未完成完整 DLL 链接；源代码完成不代表正在使用的编辑器已加载此改动。
- 只取消了本任务重复排队的 Game 构建，未中止其他构建或编辑器。未启动游戏、截图、测试或验收。
