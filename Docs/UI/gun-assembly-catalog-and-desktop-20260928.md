# 枪械组装面板与桌面改版

> 历史制作记录：本页初版／第二版桌面已被替代，相关退役源已归档；当前保留链与公共源码接入边界见 [整理发布说明](../Publication/workbench-publication-20260928.md)。


游戏操作沿用既有拖放、转向、持稳校准和品质结算。

## 面板

准备界面改为独立 `UColdSteelGunAssemblyWidget`。宽度与打铁面板、背包一致，按可用视口夹取，上下留 12 px；跟随背包共同收回。沿用打铁面板的磨砂外壳、20 px 标题、16 px 分区标题、14 px 正文、12 px 辅助文字、36 px 按钮与材料三列表格。中段为成品图和实际物品参数双列，内容可滚动，主操作固定底部。进行中的工件锁定配方，下次打开继续。

小游戏信息条使用打铁同款 600 px 最大宽度、底部位置、磨砂背景、三项读数和进度细线。抓取、对位轮廓、准星和操作规则不变。

## 后续新枪接入

普通新枪不需要再编写一套 C++ 组装小游戏。`Content/ColdSteelData/gun-assembly.json` 已改成 `recipes` 数组，面板自动列出配方。现有 M4 仍是一把枪身加五件活动组件；其他配方可使用 1～30 个活动组件。

每把新枪仍需准备以下内容：

1. 先完成正常武器与物品目录接入；`output` 填物品定义 ID，名称和图标由物品目录读取。
2. 从该枪原模型导出固定枪身和活动散件。统一朝向与尺度（UE 厘米），每件网格以自己的中心为原点，保持原材质。不要将其他枪型导出到 M4 资产路径。
3. 在 `recipes` 增加唯一且稳定的 `id`，填写 `body_mesh`、`body_position`、`camera`、`look_at`、材料 `inputs`。
4. 每个 `parts` 条目填写 `id/name/mesh`、组装目标 `target`、散件初始位置 `loose`、半尺寸 `extent`、初始角度 `angle` 和选取半径 `radius`。位置都相对工作台网格局部坐标，单位 cm；角度单位 °。
5. 配方级 `position_tolerance_cm`、`angle_tolerance_deg`、`calibration_seconds` 控制对位与校准。M4 继续使用 5 cm、18°、5 秒。

这些是每把枪的资产准备与配置工作，不是每枪重写玩法。只有增加不同操作机制（例如独立拧紧流程）才需要增加玩法代码。现有 M4 导出脚本只更新自身配方，保留其他配方。

已付款工件记录组件数和校准时长，旧 M4 工件缺失字段时默认 5 件／5 秒。工件存在期间不能换配方；已有工件的配方 ID、组件顺序不可直接改写，修改装配结构请使用新配方 ID。缺失配方时保留工件；已完成成品仍可领取。

## 桌面

参考图与提示词：`SourceAssets/GunWorkbench20260928/Reference`。参考图为设计图，不是游戏截图。用户随后明确要求复用现有台灯，因此最终模型的灯具沿用 `SM_WBK_Bench_TaskLamp` 和 `SM_WBK_LampFlex`，只重新安排位置；参考图的灯具造型不作为新建资产。

保留原木桌板和金属桌架；移除旧桌面台钳、工具、瓶罐、托架和装饰枪件。中央为薄硅胶垫，远角放原台灯，侧翼安排旋压浅盘、三把冲针、精密起子、尼龙／黄铜小锤、六位批头座和维护瓶。手持枪械分件继续使用原版已接入的组件资产。

作者文件：`SourceAssets/GunWorkbench20260928/Authored/GunWorkbench_Editable.blend`；导出网格：同目录 `SM_GunWorkbench.fbx`。台灯与桌子源资产不修改。新网格导入 `/Game/Building/GunWorkbench20260928/SM_GunWorkbench`；建造目录继续使用稳定 ID `gun_workbench_table`。

本次不运行游戏、不追加测试或验收截图。实际视觉、布局与交互交由用户测试。导入回执与编译日志保存在 `SourceAssets/GunWorkbench20260928`。

资产已保存，回执 `Receipts/import.json`。用户关闭编辑器后，`FPSGAMEEditor Win64 Development` 最终构建成功，日志为 `build-complete.log`，DLL 已落盘。构建中还遇到法杖文件在 Unity Build 中局部变量 `Slots` 与全局同名的 C4459，已仅将该局部变量改名为 `AssemblySlotNames`，没有执行其审计命令。
