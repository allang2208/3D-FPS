# 默认白水晶 V34 已撤回

用户反馈材质效果不佳，已恢复升级前默认杖头几何、V29 透明度及 V32 照明材质。V34 内部羽片、厚度贴图和折射升级的正式引用已移除；世界、UI 预览及 Blender 对应对象和重导入口已恢复。四个元素杖头保留 V33。

历史回退在现有编辑器中保存四个网格与两个材质，没有重新运行游戏或进行视觉测试。2026-09-29 将被否决的作者脚本、导出物、Blender 源与回退回执一并归档至 `trash/staff-publication-20260929/SourceAssets/ApprenticeStaff20260927/QuartzCraftV34/`；详见 [归档清单](../AssetArchives/staff-publication-20260929.json)。UE 内部的历史备份包保留本机，不作为当前导入入口。

不要按废案目录恢复已撤回的白水晶升级。回退后的配方从 `QuartzAimV22/ue_quartz_material.py` 重建，并保留 V30 节点清理与 V32 照明曝光处理。

2026-10-03 后续：已按用户授权制作并接入 [V35 第一轮表面与透光候选](staff-quartz-surface-20261003.md)。仍使用 V22 世界与 V23 预览资产路径，重建配方在 V35 安装回执 complete 后委托 `QuartzSurfaceV35/ue_material.py` 与 `parameters.json`；四元素仍为 V33。该候选没有重启 V34 羽片／折射废案，也未获用户观感确认。
