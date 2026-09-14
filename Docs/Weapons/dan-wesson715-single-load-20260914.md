# Dan-Wesson 715 默认逐发装填与速装器升级

后续动作修正见 [左开弹巢、甩腕与取弹手型](dan-wesson715-reload-flick-20260914.md)。选择方式、弹药结算和下列源时间继续生效；当前动作作者源转到 ReloadFlick20260914。

用户指定：逐发装填作为默认，速装器换弹作为改造升级。此次继续使用已升级的 715 模型、材质、轴线与 Manny 手模，不替换其他武器。

## 游戏行为

- 未安装装填装置的 715（包括旧存档）默认逐发装填。枪匠 → 装填装置 → 六发速装器 → 应用，切换为现有整组速装动作；选回逐发装填并应用即可恢复。
- 每段动作按开始时的实弹数及可用备弹选取：`StartLive=0..5`，`Count=1..6-StartLive`，共 21 个完整片段。弹药不足则只播放实际可补入的轮数。
- 单发循环：保留未发射弹药，开巢后逐孔取壳、放开空壳、取新弹、压入该孔。速装器在所有逐发片段中隐藏。左手捏持以拇指／食指接触目标求解，右手保持枪握把约束。
- 每次压入时扣除一发背包弹药并增加一发膛内弹药，沿用现有保存事务；最后一发仅发放一次巧手换弹经验。靶场无限备弹按每发装入处理，不生成物品堆叠。逐发结束不再执行整组补满。
- 时长、手部动作、机械音和弹药结算共用原动作源时间。动作开始时冻结长度，装填中保存导致技能／数值刷新不会改变当前动作时钟。
- 枪匠草稿只做配置和属性对比；实际已应用的 `gunsmith_parts.reload_device` 决定换弹方式，旧保存结构无此键即原厂逐发。应用、撤销与忙碌拒绝沿用既有系统。

## 源时间（秒，应用巧手／配件倍率前）

| 事件 | 时间 |
| --- | --- |
| 开巢到位 | 0.48 |
| 第一个单发循环开始 | 0.55 |
| 单发循环 | 1.15 |
| 取壳／新弹出现／压入，循环内 | 0.23 / 0.56 / 0.91 |
| 闭巢到位 | 0.55 + 1.15 × 装填数 + 0.37 |
| 回握完成 | 1.25 + 1.15 × 装填数 |

补 1 / 2 / 3 / 4 / 5 / 6 发分别为 **2.40 / 3.55 / 4.70 / 5.85 / 7.00 / 8.15 秒**。面板普通换弹基准为补 5 发（留有 1 发），空仓为补 6 发；单发少量补弹可能快于速装器。速装器普通 **3.60 秒**、空仓 **3.85 秒**；巧手及换弹加成继续作用。

## 作者资产和接入

- 可编辑源：`SourceAssets/DanWesson715SingleLoad20260914/DanWesson715_SingleLoad_Editable.blend`。包含当前模型、原始参考、逐发片段及上一轮升级动作。
- FBX：同目录 `Animations/A_DW715_single_<StartLive>_<Count>.fbx`，120 Hz 烘焙。
- 引擎片段：`/Game/Weapons/DanWesson715/SingleLoad20260914/Animations`，保留原 715 Skeleton 与 M4Viewmodel 压缩设置。
- 枪匠分类 Texture：`/Game/UI/GunsmithWorkbench/ColdGlass/T_Category_reload_device`；两张选项 RGBA 图标在 `Content/ColdSteelData/AttachmentIcons20260913`。
- 数据与代码：`gunsmith.json`、`DanWesson715WeaponAssets.h`、`GunsmithSystem.cpp`、`FPSGAMECharacter.h/.cpp`、`FPSGAMECharacterProfile.cpp`、`ColdSteelStatusModel.h`、`ColdSteelProfileRuntime.cpp`。
- 现有 DanWesson715、GunsmithWorkbench 和配件图标目录打包规则已覆盖新增资源。

参考动作继续使用 [ZenXChaos/ThirdPersonShooter-AnimationSets](https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets) 的 `RevolverReloadInit / RevolverReloadLoop / RevolverReloadEnd / RevolverSearchAmmo`，固定提交 `f19adc2ece4cab0f89c9236223abb97d4d2badea`，Unlicense；原始 FBX、许可证和解析姿态保存在上一轮 `Upgrade20260914/Reference`。取其手部路径和手指变化作为制作参考，715 的机械与接触动作另行编排。Fab 枪体、Manny／P9 衍生素材的许可和本机保存范围沿用上一轮记录。新增图标为程序原创。

本轮只执行作者导出、必要构建与资源导入；未启动游戏、运行测试、试听、截图或制作验收渲染，由用户测试。
