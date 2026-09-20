# 战术垂直握把、大弹鼓与 AKM 托底抓握

本次将战术垂直握把作为独立前握把接入 M4A1、AKM、QBZ-191、ASH-12，属性仅为开镜耗时 −25%。升级三枪现有大弹鼓外壳并去除供弹颈左右各两根突出竖条。AKM 弹鼓改成自然掉落，装入时掌心托底、四指并拢弯曲、拇指对握；普通及空仓覆盖五种握把，共十条动画。

## 当前来源与运行入口

- [战术垂直握把](../../SourceAssets/TacticalVerticalForegrip20260919/Integration/README.md)：`tactical_vertical_foregrip`，`ads_percent=-0.25`；`M4HandstopVisual.cpp` 复用既有垂直动作族并选择每枪网格，`M4VerticalForegrip.cpp` 负责切回原件时恢复模型和材质。
- [大弹鼓模型](../../SourceAssets/LargeDrumUpgrade20260920/README.md)：保留原配件 ID、容量与每枪安装接口，使用新鼓壳、PBR、LOD、碰撞和正式图标；四根竖条已从源到导出同步删除。
- [AKM 换弹](../../SourceAssets/AKMDrumFreeDrop20260920/README.md)：当前 `PalmGripV3`。`FPSGAMECharacter.cpp`、`AKMAttachmentVisual.h` 指向 `AKMDrumFreeDrop20260920` 动画目录；`M4DrumVisual.cpp` 保留 AKM 本枪网格，源时间 0.3 秒自然释放，装入轨迹和补弹时钟沿用原动作。

## 归档与继续制作

本次废案及被替代备份移至本机 `trash/attachments-grip-drum-20260920/`。包括中止的远程生成任务、带四根竖条的旧鼓壳、AKM 旧侧握/张掌源及中间姿态预览。逐文件原路径、归档路径、大小、SHA-256 与替代说明见 [归档清单](attachments-grip-drum-archive-20260920.json)；移动后已核对归档文件散列，未删除它们。

保留当前正式 Blend/FBX、材质、图标、最终预览及当前制作链依赖：战术握把的本机建模母版、每枪原接口、`OriginalDrumInterfaces.blend`，以及从旧 V2 参数独立出来的 `AKMDrumFreeDrop20260920/Inputs/palm_support_anchor.json`。作者脚本不会从 trash 读取当前输入。

可复用方法同步至个人技能和工程镜像：[托底抓握与连续指节屈曲](../../skills/ue5-fps-arms-animation/references/pose-contact.md)、[配件切换与局部修形](../../skills/ue5-weapon-workflow/references/attachment-standard.md)。不把某一手模的角度或历史检查结论作为通用常量。

## 公开仓库与本机依赖

本次发布源码、作者脚本、说明、来源记录和归档清单；不发布用户参考图、模型/动画源、PBR、图标、UE 二进制包、密集姿态数据、日志及 trash。公开仓库不是完整的素材备份。

按 [AssetSetup](../AssetSetup.md) 恢复合法取得的本机素材，并保留原相对路径：

- `Content/Weapons/TacticalVerticalForegrip20260919/`：四枪网格、干湿材质与贴图。
- `Content/Weapons/LargeDrumUpgrade20260920/`，以及 `AttachmentFinish20260913` 下 M4/AKM 原运行网格和 `QBZ191/Attachments20260913/SM_QBZ191_drum`：鼓壳与各枪材质；`Weather/RainVisibility/DA_WeatherPresentation` 保存湿润映射。
- `Content/Weapons/AKMDrumFreeDrop20260920/`：十条最终动画；它们依赖现有 M4HK416Replica 骨架和 Manny 手模。
- `Content/ColdSteelData/Icons/`、对应 UE 图标资产，以及三个本机 SourceAssets 目录中的参考、接口、贴图、JSON 输入/回执和 Blend/FBX。

源动画依赖 `source_manifest.json` 指向的既有五个动作家族；`build_receipt.json` 和 `contact_fit.json` 是本机导出/导入链输入。脚本需在具备这些合法来源的宿主运行。本机编辑器调用使用已支持 `-PythonScript` 的项目批次互斥桥；本次提交不夹带其他任务正在修改的公共桥工具。许可边界和内容恢复仍以 AssetSetup 为准。

## 已有证据与本次整理范围

握把接入阶段完成过必要常规 Editor 构建和用户要求的材质预览；弹鼓升级通过打开的编辑器保存资源。AKM PalmGripV3 按用户要求检查了实际蒙皮模型与接触帧的 SOURCE/COMPRESSED 手指姿态，十条动作读回的最大旋转差约 0.0293°；这不代表完整实机回归或用户最终认可。

本次只做归档与发布所需的散列、暂存差异、大小、敏感信息、许可和远端分支检查，不重新构建、启动游戏或运行玩法测试。其他任务的未提交修改保留在工作区。
