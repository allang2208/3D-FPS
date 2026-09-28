# 枪械工作台：桌面与入口（2026-09-27）

> 历史版本记录。初版桌面 Authored 已归档；Polish 仍被原台灯恢复及后续小件链引用，保留作制作依赖。当前桌面与发布边界见 [整理发布说明](../../Docs/Publication/workbench-publication-20260928.md)，不要运行旧导入器覆盖其他任务的新桌面。

现有工作台的枪械工位外观，以及 M4 散件拼装、校准、扣料、品质与成品领取。玩法说明和当前构建状态见 `Docs/UI/firearm-assembly-workbench-plan-20260927.md`。

## 资源来源

- 桌体来源：`SourceAssets/WorkbenchBuildable20260924/Authored/StandaloneWorkbench.blend`；UE 原网格 `/Game/Building/Workbench/Meshes/SM_WBStandalone_Workbench`。
- 握把和弹匣来源：`SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend` 中原有分件；材质复用当前 `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416`。
- 装配垫、标记、两处定位支架与零件托盘由 `Tools/GunWorkbench/author_station.py` 制作。没有新增下载的第三方资产；既有模型及其材质沿用项目原来源与许可。本目录不是对既有素材的独立再分发许可。
- 不覆盖原桌子、原枪源文件或实战资产。桌面装饰分件已合并为静态网格，尚不是可拖拽的小游戏组件。

## 制作产物

- `Authored/GunWorkbench.blend`：独立作者文件。
- `Authored/SM_GunWorkbench.fbx`：105,936 三角，保留原桌子坐标、UV 与部件材质槽。
- `Authored/manifest.json`：导出位置、原材质映射与新增材质参数。
- 目标 UE 路径：`/Game/Building/GunWorkbench20260927/SM_GunWorkbench`。
- 目标建造菜单条目：`gun_workbench_table`／「枪械工作台」，建筑 → 其他。
- 导入时复用原桌子的 Nanite 设置、使用网格碰撞，并只更新建造调色板中本构件的条目。

## 交互源码

`ColdSteelWorldInteraction` 将新 ID 识别为工作台；`ColdSteelWorkbenchHUD` 向原面板传入枪械工位模式；`ColdSteelGunWorkbench.cpp` 显示所需／已支付材料、五件进度、继续拼装和领取成品。按 E 进入，Esc 或 × 返回。完整桌面操作由 `GunAssemblyInteraction` 管理，业务和评分由 `GunAssemblySystem` 管理。

## 可交互组件

`Assembly/M4_AssemblyParts.blend` 与六个 FBX 来自同一原 M4 作者源；枪身包含扳机，护木／枪托／握把／弹匣／枪口件独立。每件以自己的包围盒中心为旋转枢轴，共同安装坐标与散件托位记录在 `Content/ColdSteelData/gun-assembly.json`。导出不覆盖原枪。

`Tools/GunWorkbench/author_assembly.py` 负责导出；`import_assembly.py` 复用原 M4 材质并新建半透明安装轮廓材质。六件 UE 网格和轮廓材质已保存，回执 `Receipts/assembly-import.json`。手臂复用 V7 裸手和原抓握数据，接触音复用 `/Game/Weapons/M4HK416Audio/S_HK416_MagSeat`；未新增外部素材。

本轮小游戏 C++ 与 `UnrealEditor-FPSGAME.dll` 已落盘，常规构建成功：`Saved/GunWorkbench20260927/build-assembly-02.log`。六件组件经后台 commandlet 最终导入保存，包含坐标反射时的面朝向修正，日志 `Saved/GunWorkbench20260927/import-assembly-final.log`；没有运行游戏、测试或渲染。

## 当前落盘状态

Blender 作者文件、FBX、manifest、C++ 源码及 UE 网格、四个新增材质、建造菜单条目均已保存。`FPSGAMEEditor Win64 Development` 常规构建成功，日志为 `Saved/GunWorkbench20260927/build-editor.log`。用户关闭 UE 后使用无界面 commandlet 完成导入，没有启动交互式编辑器或游戏。

导入入口为 `Tools/GunWorkbench/import_station.py`；成功回执为 `Receipts/import.json`，日志为 `Saved/GunWorkbench20260927/import-commandlet.log`。引擎报告 0 errors；保留了导入网格局部近零切线／副法线的警告，未进行视觉验收。早期因 PIE 拒绝保存的调用记录保留于 `Receipts/import-mcp-01.txt`。未测试、未截图、未渲染，交由用户自行测试。
