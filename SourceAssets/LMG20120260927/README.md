# 201 当前制作与恢复入口

2026-09-29：原 201 已列为废案。旧生成入口、旧根 README 及废案输出移到 `trash/lmg201-rejected-20260929/SourceAssets/LMG20120260927/`。详见 [废案记录](../../Docs/Rejected/lmg201-original-model-20260929.md)。

## 当前新模型

- 模型链：MeshyRetry28 → Refine29 → Install30 → Surface32 → Detail35 的局部输入 → **[Repair36](Repair36/README.md)**。
- 当前完整装配导出：`Repair36/Exports/SK_LMG201_R36_Installed.fbx`；修复盖体：`Repair36/LMG201_R36_Lid.blend`。
- UE 主体：`/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`。旧包名并不代表首轮旧模型。
- 原装弹匣：Magazine24；新布料弹箱：ClothFeed33；通用配件：Accessories22；ADS 衣物：ADS34；开火声：FireAudio01。
- 材质绑定：Repair36 与当前 `Material21/bindings.json`；Detail35 父材质仍被使用。

## 保留的旧来源

Skin07/ArmSprint06 是基础动作捕获源；BeltFeed08 保留基础动作和骨架；PKMFK19 给 Accessories22 提供姿态；Refine12 仅保留原装弹匣抓握所需的 `201_surface.json`；Video26 编辑源只给 Install30 提供原生骨架。它们的旧说明与旧导入器不是当前部署入口。

不要按目录编号批量重跑历史导入脚本。已归档的首轮模型不能覆盖现用资产。Repair36 仍读取 Detail35 的加厚前脚本、Work 和贴图，不能整目录移除 Detail35。

公开 Git 保存选定作者代码、说明与归档清单；完整模型、贴图、Manny/Infima 动作、密集骨骼/网格数据及参考视频仍需本机合法来源。详见 [发布与恢复边界](../../Docs/Weapons/lmg201-publication-20260929.md)。本轮仅归档和发布，没有运行游戏、渲染或重新构建。
