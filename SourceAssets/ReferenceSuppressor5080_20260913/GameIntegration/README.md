# 战术消音器游戏接入 · 2026-09-13

用户要求将斜纹修整版接入游戏，命名为“战术消音器”，并调整原消音器属性。本目录记录制作和接入结果；未进行运行测试或验收。

## 配件与属性

已为 M4A1、AKM、QBZ-191、M1911 的枪匠“枪口”选项加入 `tactical_suppressor`。原消音器继续使用 `true`，既有存档无需迁移。

| 配件 | 后坐力 | 枪械稳定性 | 子弹速度 | ADS 瞄准速度 |
| --- | --- | --- | --- | --- |
| 战术消音器 | -25% | +25% | -20% | -5% |
| 原消音器 | -10% | +10% | -15% | 不变 |

`Content/ColdSteelData/gunsmith.json` 使用 recoil_mult、stability_mult、bullet_speed_mult。ADS 的现有接口按耗时累计，因此战术消音器的 ads_percent 为 `1 / 0.95 - 1`，即增加约 5.263% 瞄准耗时，以表达速度降低 5%。其他配件继续遵循现有组合规则。

稳定性为已有正向派生评分。新增倍率先作用于该评分，再同步缩小枪械摇晃幅度和恢复耗时，避免仅改变文案；无稳定性倍率的配件继续原来的计算方式。基准评分 50 的枪械使用战术消音器后为 62.5，原消音器后为 55；各枪实际结果仍包含其基础值和其他配件。

## 模型与材质

选用 `../KnurlRefinedV1/Suppressor_KnurlRefinedV1.blend`。保存原模型，另制游戏网格、烘焙法线与四枪安装坐标：

- `TacticalSuppressor_GameBase.blend`：游戏网格基础文件。
- `TacticalSuppressor_FourWeapons_Editable.blend`：四枪适配的可编辑源。
- `M4/`、`AKM/`、`QBZ191/`、`M1911/`：各自的 `SM_TacticalSuppressor.fbx`。
- 每枪导出网格为 65,343 三角形；UV0 为结构法线，UV1 为独立涂层贴图。
- `Textures/T_TacticalSuppressor_Normal.png` 为 2048px 切线法线，UE 导入时翻转绿色通道。
- M4、AKM、M1911 使用工程当前对应枪体涂层贴图；QBZ-191 使用当前保存的机匣材质烘焙涂层块。
- 枪匠图标由游戏网格制作，已保存至 `Content/ColdSteelData/AttachmentIcons20260913/muzzle_tactical_suppressor.png`，沿用界面现有 PNG 加载与 ColdSteelData 打包路径。

UE 资产位于 `/Game/Weapons/TacticalSuppressor20260913/{M4,AKM,QBZ191,M1911}/SM_TacticalSuppressor`。各目录包含 Shell、Recess、Mount 材质。烘焙、FBX 导出参数与导入回执分别保存在 `authoring.json`、`author_game.py`、`import_receipt.json` 和 `import_assets.py`。

连接面采用各枪现有游戏安装基准与组件层级。M4/AKM/QBZ 的可见筒身长 18.6cm，M1911 13.02cm；尺寸仅用于游戏资产适配，不包含制造图纸或真实内部结构。

## 运行接入

新变体接入现有组件与枪匠预览、应用、保存/恢复流程。四枪保留原有安装层级和枪口位置算法；切换网格时清除前一网格材质覆盖。新 ID 同时进入消音判定，用于现有消音音效、枪口火光削弱和噪声范围逻辑。`DefaultGame.ini` 新增本资产目录的烹饪引用。

源代码入口：`Weapons/TacticalSuppressorAssets.h`、`M4MuzzleVisual.cpp`、`AKMAttachmentVisual.h`、`QBZ191Attachments.h`、`M1911WeaponAssets.h`、`M1911AttachmentVisual.cpp`、`GunsmithSystem.h/.cpp`、`WeaponHandling.h/.cpp`、`FPSGAMECharacter.h`。

## 制作记录与未测试范围

网格和材质导入脚本完成保存并写出 `import_receipt.json`。导入命令行进程返回 1，日志报告工程缺少 `GameFeatureData` 的 Asset Manager 规则；该工程配置报错未在本任务中处理。此记录不表示运行验收通过。

必要编辑器编译由 `Tools/Build/Build-Editor.ps1` 完成，返回 `Succeeded`，最终日志为 `Saved/BuildEditor/build-20260913-220235.log`。未执行自动测试、PIE、装配验收截图或完整打包。`make_icon.py` 的渲染仅用于制作随游戏交付的枪匠图标。

未测试，由用户自行测试游戏中的装配、属性、存档和视觉效果。
