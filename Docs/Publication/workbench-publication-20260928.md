# 工作台、枪械组装与脚架／镭射整理发布

宿主为 `D:/FPS3D/FPSGAME`，目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。按 WORKFLOW 第 8 节精确发布，不切换共享分支，不回退其他工作。

## 本轮成果

- 常规工作台按打铁和枪械面板统一宽度、冷钢样式、配方标题、材料三列、状态摘要、成品参数和窄屏排布。普通配方直接制作，没有小游戏。修复点击制造栏收起、开合时误触、配方下拉生命周期、材料／容量报价不一致和模型变化后预览不刷新。[面板审计与实现](../UI/workbench-panel-audit-plan-20260928.md)。
- 枪械工作台上方弹药／枪械双卡片切页；弹药直接制作进弹药袋。枪械使用同一拖放、转向和持稳校准玩法，由 11 组配方定义枪体与活动件。完成后可领取，或放弃并按实际支付材料逐项向下取整返还一半；返料、工件清空原子提交，背包放不下时保留工件。
- 枪械品质随物品保存并进入后坐力、散布和枪匠／物品参数展示。配方扩展不再逐枪编写游戏逻辑，但仍需准备拆分模型、目标位置和散件布局。
- 脚架获取与提示共用候选生成，加入胶囊周围多方向贴墙探测、法线向内采样和沿边排脚，解决近乎平行障碍物切面时漏判；按实际速度判断静止。保留有效支撑、坡度和高度要求；净空受阻仅限制呈现校正，未宣称任意障碍物成功率已实测。
- 镭射保留连续可见性和变换历史；光束与命中小点分开处理。小点在 After Motion Blur 合成，用解析边缘和显式场景深度遮挡，避免继续依赖接收面历史；光束保留时间响应和透明速度。

## 桌面与废案

本对话曾制作的初版／第二版总装和四个专用作者／导入器已移入本机 `trash/gun-workbench-retired-20260928/`，共 11 份。原路径、归档路径、大小、SHA-256 和原因见 [归档清单](../UI/gun-workbench-retired-20260928.json)。移动后回读散列一致；没有移动或删除 UE 包。

保留初版目录中的 `Assembly` 分件，保留 `Polish/Authored`、`Cleared`、`LibraryTools`、`Ammo` 作者链和原台灯／工具／弹药盒输入。`restore_original_lamp.py` 仍读取 Polish 总装，旧工作垫材质也被后续链引用，因此这些旧源不属于可删除废案。参考图、原始来源、构建日志、导入回执留本机。

当前 `GunWorkbenchMedieval20260928` 总装、青铜火炬及其 palette 调整属于独立工作，用户已撤回该项问题；本次不修改、不归档、不发布这些文件，也不运行旧导入器覆盖它们。历史设计文档保留过程，不代表当前桌面最终状态。

## 公共 Source 与交接边界

直接合入公共 Source：常规工作台控件与必要 HUD／布局／外部点击片段、`CraftingSystem`、安全下拉选项控件、PKM 脚架判定和镭射运行修复。同步发布三份配方、桌面／分件制作脚本、镭射材质作者脚本与 HLSL、文档和 SKILL。

枪械组装依赖的打铁运行层目前仍在 [锻造交接](../Gameplay/forging-publication-20260927.md) 中。本次保留 10 份完整新源码为 [新运行源码补丁](WorkbenchPublication20260928/new-runtime-sources.patch)，19 份共享文件的本题接口为 [接入补丁](WorkbenchPublication20260928/shared-runtime-hooks.patch)。基础提交、文件散列和合并口径见 [交接清单](WorkbenchPublication20260928/runtime-handoff.json)。

这些补丁**未应用到公共 Source，克隆仓库不能单独重建宿主全部枪械组装行为**。宿主已有完整修改，不要再应用补丁。共享补丁基于本次常规工作台直接提交后的版本；部分 HUD 改动与前次锻造交接重合，应合并组合版本而非依次盲打补丁。保留地牢输入恢复分支中的 `!IsGunAssembly()` 门控；该分支本体属于另一个任务，没有夹带发布。枪械品质函数只抽取装配部分，合并其他工具／近战接口时保留它们。

本次明确排除独立 LMG201 实战武器改造、其他地牢实现、采集工具、独立 HUD／天气改造，以及当前中世纪桌面源。公共片段的依赖阅读不代替公共完整工程构建。

## 资产恢复

1. 恢复现有工作台桌子、独立 `SM_WBK_Bench_TaskLamp`／灯臂、库内工具、原弹药盒模型及原材质；沿用其本机许可，不公开重新分发模型／贴图。
2. 历史认可桌面链：`author_station_polish.py`／表面作者 → `restore_original_lamp.py`／`import_original_lamp.py` → `import_cleared_workbench.py` → `place_library_tools.py`／`import_library_tools.py` → `prepare_ammo_sources.py`／`place_library_ammo.py`／`import_library_ammo.py`。它们依赖本机 manifests、源总装和导出件，带有旧引用前置条件；不是更新当前中世纪桌面的命令。
3. 分件链：M4 的 `author_assembly.py`／`import_assembly.py`；其余枪型的 `prepare_catalog_sources.py`、两份 export 脚本、`author_catalog_assembly.py`／`import_catalog_assembly.py`。目录 `gun-assembly.json` 只包含材料、资产路径和少量装配布局参数，不包含顶点、骨骼或动画采样。保留所有配方 ID、活动件顺序，避免改变进行中工件含义。
4. 恢复 `/Game/Building/GunWorkbench20260927/Assembly`、`/Game/Building/GunAssemblyCatalog20260928`，M4 V7 裸手、对应骨架、`Content/ColdSteelData/forge-grip.json` 和现有 HK416 接触音。姿态 JSON 来源于授权手臂，继续只保留本机。工作台稳定 ID 为 `gun_workbench_table`；palette 引用与现有场景实例的模型引用需一起考虑，不靠反复改挂点解决旧实例显示。
5. 打包需将上述两个分件目录加入 `DirectoriesToAlwaysCook`，并沿用 `ColdSteelData` 的 UFS 数据配置；本次不整份提交混合的 DefaultGame.ini。桌面路径按用户当前选定版本恢复，不把历史桌面恢复脚本当作当前指定模型。
6. 镭射入口 `Tools/Weapons/ScopeOptics20260927/create_laser_materials.py`；仅光点使用 `update_laser_dot.py`。After Motion Blur 不能依赖硬件深度开关，必须保留 HLSL 的场景深度比较与相机遮挡射线。

所有 Blend／FBX、纹理、音频、UE 包、密集采样、已保存导入回执、Saved 和 trash 留本机。源码与脚本不能代替已导入资产。

## 经验与交付状态

个人技能和工程镜像同步更新冷钢工作台／结算参考页，以及脚架贴墙判定、镭射光点时间残影规则。保留其他技能修改。

本轮只做用户授权的归档与发布检查：路径／散列、完整暂存差异、补丁结构、JSON／脚本语法、敏感信息、大小、许可和远端回读。不重跑游戏或开启 UE。最近常规工作台宿主后台构建成功记录为 `Saved/Changes/WorkbenchPanelAudit20260928/Build.log`（退出码 0）；本轮没有重新构建，未测试，交由用户自行测试。
