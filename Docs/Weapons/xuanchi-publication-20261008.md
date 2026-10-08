# 玄螭镇岳：源码发布与制作资料整理

2026-10-08。本次范围为镇岳武器、剑身／符文／护手／握把／配重、挂饰运动、配件详情统一规则；不包含共享工作区其他武器、怪物、场景或界面的并行开发。

## 当前入口

| 内容 | 制作源／配置 |
| --- | --- |
| 原厂剑与连续刃根 | `SourceAssets/XuanChiZhenYue20261004/BladeV3/`、`SilverCopperFinish/`；BladeV3 仍读取 ModelV1 母版，护手和挂饰读取 SurfaceV2 |
| 共用改造 | 同家族的 `CommonBlades20261005/`、`RuneGuard20261005/`、`CommonGrips20261005/` |
| 六款配重直连挂饰 | `DirectPommelTails20261005/`；保留 `PommelTails20261005/interface_inputs.json` 接口，原厂环首不变 |
| 图标 | `SourceAssets/SharedPommelIcons20261005/` 与 `FactoryIcons20261006/`；通用件共用图标 |
| 镇魔剑身纹样 | `SourceAssets/ZhenmoRune20261005/BladeTalismanV4/`；认可图片原像素直接接入，作者入口 `author_artwork.py` |
| 镇魔地面与金粒 | 同家族 `GroundVisibility20261007/`、`SoftGroundV3/`、`RisingMotes/` |
| 金刚 | `SourceAssets/JingangRune20261006/`，含 `FlamesV2/` 和 `BladeTextFlip20261006/` |
| 蟠螭展岳 | `PanChiGuard20261006/`；数值真源 `PanChiEffects20261006/effects.json`，现行表现 `PanChiUppercut20261007/` |
| 目录 | `Content/ColdSteelData/xuanchi-zhenyue-modules.json`、`melee-gunsmith.json`、`shared-sword-pommels.json` |

护手当前是格挡蓄势后的主动上挑强化：免准备，位移后身前 3 米生成金阵，直径 4.4 米，金龙持续上升 1.5 秒；释放时阵心半径 10 米内普通／已破韧怪物向阵心拉近最多 5 米，与命中独立。旧目录中的重击前射、命中后向玩家拉近及合围说明是历史记录；保留 `PanChiRelease20261007` 的金粒制作与 `PanChiFlight20261007` 的复用材质，完整制作链最终进入 Uppercut。

配件详情统一为常驻能力卡片和绿色特效说明；暴击率显示“改造暴击率（+25%）”，底层仍为百分点加法。规范见 [配件说明](../../skills/ue5-weapon-workflow/references/attachment-detail-presentation.md)，制作经验见 [东方重剑与符文](../../skills/ue5-weapon-workflow/references/eastern-sword-runes.md)。

## 归档与保留

已将 37 个确认退役文件移至本机 `trash/xuanchi-zhenyue-20261008/`：镇魔剑身 V2／V3、旧 SVG、四个有当前母版的 Blender 自动备份及两个已应用的一次性原生源码迁移脚本。共 618,688,370 字节，移动前后 SHA-256 一致；逐文件记录见 [归档清单](../Archives/xuanchi-zhenyue-20261008.json)。未删除二进制资源或其他工作的文件。

当前模型母版、认可图片、物理挂饰、材质重建输入与有用历史诊断保留。`Concept`、`V1`、`V3` 等名称不代表废案。活动回执可能是重建器的输入，例如镇魔 `import_receipt.json` 含前代材质绑定；这些文件保留本机，不当缓存清走。

## 公共仓库与恢复边界

本次发布 C++、必要数据、作者脚本、参数与文档。完整本机 Content、FBX／Blend／GLB、PNG、音效、字体、执行日志、保存回执与备份不公开提交；用户提供的模型与符箓参考尚未核准原资产再分发许可。公共源码不能单独还原完整可玩工程。

恢复时按 [资产恢复边界](../AssetSetup.md) 从许可完整工程备份恢复 `/Game/Weapons/XuanChiZhenYue20261004`、所依赖双手剑动作／手模、共享改造库、唐刀符文材质和图标目录，并恢复对应 SourceAssets 制作输入及回执。先读各家族 `production.md` 和上述现行入口，再按需制作／导入；不要批量执行历史诊断或旧版安装脚本。

作者脚本中 `D:/FPS3D/FPSGAME`、本机 UE／Blender／Node 路径是明确的开发宿主默认值，换机需调整；无需安装或发布引擎本体。图片生产提示词保留，可再制作，但重新生成不保证等同于认可原图。

最近配件格式修改已在此前完成 Editor／Game Development 构建和落盘。本次仅执行用户要求的整理、来源与推送检查；没有启动 UE、游戏、运行回归或重新做视觉验收，由用户测试。

## 发布检查

从 `18d667e6` 基线建立临时索引，按所有权逐块选取共享文件修改；没有暂存其他工作的霰弹枪、双侧战术挂件、庄家附魔、焚烧炉或怪物更新。294 个发布路径均为文本，最大单文件约 235 KB；154 个 Python／JSON 文件与 27 个 PowerShell 脚本语法检查完成。暂存差异无空白错误、敏感凭据命中或未发布的本地 C++ 头文件依赖，新入口文档链接可解析。完整检查记录留本机 `Saved/Publication/Zhenyue20261008/`。这些是推送检查，不代表游戏运行验收或独立源码快照的重新编译。
