# 枪口烟雾与火光表现修正

> 当前运行与重建入口为 V5；下文 V2–V4 为历史验证记录。旧候选和生成脚本已按 [归档清单](gunplay-archive-20260911.json) 移入 trash。


## 实际发现

现有 V2 的 Muzzle_Smoke 初始化颜色固定为 (0.5, 0.5, 0.5, 1)，没有读取 C++ 设置的 User.Smoke Color，因此旧代码的透明度调整没有作用。每发的烟与 0.11 秒周期的热排烟叠加，形成白色烟团。烟、中央火光另有 Niagara 内部 Position Offset；新版本禁用该额外偏移，直接使用组件对应的实际枪口出口。烟本身使用世界空间，离开枪口后不会随枪瞬移。

逐帧检查第一轮候选还发现火光末尾有暗斑：ScaleColor 仅启用 RGB 缩放，未启用已有的 Alpha 淡出曲线。最终候选启用 Alpha 淡出。

## 已有资产与采用范围

- NiagaraExamples/FX_Weapons/MuzzleFlashes/NS_MuzzleFlash：沿用官方前向和侧向火舌、中央闪光，制作独立 V4 副本。
- 原包的 MI_Flipbook_Pyro_Muzzle 与 MI_Flipbook_Smoke_Muzzle：继续使用已有动画贴图及材质；缩小中央球形闪光、缩短时长、随机每发尺寸。
- 包内 T_Smoke_Wispy、MI_SmokePuffLight、NS_Smoke_Plume，以及 MilitaryTrench/P_Smoke 系列已盘点。大烟柱/场景烟不是本轮步枪枪口所需，没有直接塞入开火流程。
- 本轮未新增下载，也没有接入命中墙面/血液资产。

## 正式引用和参数

资产路径：/Game/Weapons/GunplayFX/NS_FPS_MuzzleEpicV4 和 NS_FPS_BarrelSmokeEpicV4。

烟雾 Color 绑定 User.Smoke Color；腰射 alpha 0.20，ADS 0.12；RGB (0.30,0.32,0.34)。每发烟寿命 0.28–0.50 秒；热烟 0.40–0.65 秒。热排烟只在最后一发后超过 0.14 秒、热量超过 0.35 时出现。

火光寿命 20–38 ms，中央初始尺寸参数由 65–85 降为 25–38（再乘系统全局比例）；全局比例 0.19，每发乘 0.82–1.12；消音器比例 0.07。火舌长度随机量 0.55。

构建脚本：Tools/AssetPipeline/build_muzzle_presentation_v4.py；读回报告：Saved/EpicGunFX/v4-presentation.json。原始 Epic 包未改动。V3 为迭代候选，运行引用使用 V4。

Editor Development 模块 UnrealEditor-FPSGAME-9111814.dll 编译成功。资产构建两项 valid=1、保存及参数断言完成；commandlet 退出 1 来自项目已有 GameFeatureData 规则缺失和 8000 端口占用日志，不把它报告为整个 commandlet 零错误。

最终实机：Saved/BallisticPresentationAudit-20260911155001.log，67 项通过、0 失败。新旧对照 Saved/EpicGunFX/muzzle-before-after.gif；横移录屏 muzzle-v4-strafe.mp4。


## 用户反馈后 V5 烟量调整

V4 同时降低透明度、尺寸和寿命，实机烟量过低。V5 保留出生位置及火光淡出修复，重新提高烟的可读性：腰射 alpha 0.55、ADS 0.40；烟初始尺寸参数 38–55；每发寿命 0.50–0.80 秒，停火热烟 0.60–0.90 秒；热烟 alpha 系数由 0.28 提高到 0.70。烟颜色 RGB 0.42/0.44/0.46。

当前正式引用替换为 NS_FPS_MuzzleEpicV5 和 NS_FPS_BarrelSmokeEpicV5；可编辑生成脚本 build_muzzle_presentation_v5.py，参数读回 v5-presentation.json。Editor 模块 UnrealEditor-FPSGAME-9111841.dll 编译成功。

V5 新进程实机通过 67 项、0 失败：Saved/BallisticPresentationAudit-20260911155712.log。预览 Saved/EpicGunFX/muzzle-v5-smoke.gif 与同名 mp4。
