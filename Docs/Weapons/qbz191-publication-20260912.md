# QBZ-191 制作资料与表面优化发布

本次发布 QBZ-191 作者脚本、参数、来源说明、表面优化导入入口和技能经验。宿主中共享 C++/库存数据存在其他任务尚未提交的改动，本提交不收录这些混合修改；本次不是完整 QBZ 运行时源码快照，也不是完整可运行资产备份。

## 本机资源恢复

遵循 [内容恢复规则](../AssetSetup.md)。源包为用户提供的 `D:/FPS3D/qbz-191-free (1).zip`，只有原始 OBJ 和 4K 材质贴图，公开再分发许可未确认，原包、OBJ、贴图及派生 Blend/FBX/uasset 不上传。

- 作者目录：`SourceAssets/QBZ19120260912`。需要本机 `Source/model/Final test.obj`、`Source/textures`、`SourceInspect.blend`、`components.json` 以及 `M4TacticalToss20260910/M4_Hand_MAT_Editable.blend` 和其引用依赖。顶点/骨骼采样 JSON 也保留本机。
- 原始接入源：`QBZ191_Editable.blend` 及七段动画 FBX，保留为表面优化输入，不属于废案。
- 新作者源：`SurfacePolish/QBZ191_SurfacePolish.blend` 与同目录网格 FBX。
- 运行网格：`/Game/Weapons/QBZ191/Calibrated/SK_QBZ191_Manny`；原七段动画继续使用。
- 新材质：`/Game/Weapons/QBZ191/SurfacePolish`，引用原 `/Game/Weapons/QBZ191/Textures`。动态物品展示复用此网格；原静态 PNG 图标没有重新渲染。

按 `SurfacePolish/build.py` 导出，随后在 UE Python commandlet 中执行 `SurfacePolish/import.py` 导入。该导入会更新上述运行网格；既有动画与骨架为必要输入。

## 状态与归档

表面修整已制作并导入；未运行游戏、渲染或新增功能测试，由用户验收。导入脚本完成，但 commandlet 因项目 GameFeatureData 配置错误返回非零；同次导入还有零时绑定姿势回退警告，不记录为验证通过。之前本机 QBZ 功能记录仅适用于优化前版本。

15 个被替代的 Blend 自动备份、中间运行日志和临时文本已移至 `trash/qbz191-surface-polish-20260912`，共 421813451 字节。精确原/目标路径、散列及保留替代物见 [归档清单](qbz191-archive-20260912.json)。保留最终运行记录、关键问题对照、正式源文件和依赖输入。
