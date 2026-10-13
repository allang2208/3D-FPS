# 木工工作台交互即崩溃修复（2026-10-09）

用户报告交互工作台后立即崩溃，堆栈为 `SWoodworkingCanvas::OnPaint`，`ColdSteelWoodworkingWidget.cpp:138`；引擎 `Array.h:2196` 的 `TArray::CheckAddress` 断言失败，ArrayNum=34、ArrayMax=35、元素大小16。

## 根因与修复

实际触发表达式是 `KnifeBoundary.Add(KnifeBoundary[0])`。两段 0..16 的闭区间循环各添加17个 FVector2D，数组已 Reserve(35)。即使不扩容，Add(const ElementType&) 仍会先检查参数地址，不接受自身存储中的元素引用。因此预留更多容量不会解决这个断言。

新增 `WoodworkingPresentation::ClosePolyline`：先忽略少于两个点和首尾已相同的路径，再用 `const FVector2D FirstPoint=Points[0]` 建立独立值副本，最后 `Points.Add(FirstPoint)`。OnPaint 使用该函数闭合刀口轮廓；公用 Line 绘制入口对少于两个点直接返回。未关闭引擎断言，也未改变刀口形状、绘制层级、采样数量或游戏判定。

原生修改范围为 `Source/FPSGAME/UI/ColdSteelWoodworkingWidget.cpp`、`WoodworkingPresentation.cpp`、`WoodworkingPresentation.h`。审查了木工 UI/Building 的12份相关源码：目标轮廓、推料柄、损伤环、木屑、轮廓追踪、掩码队列及移动操作没有发现第二处同类自引用追加。TargetContours 在删除 map 项前把 Next 复制为值，Path.Add 使用独立 Point；Out.Add(MoveTemp(Path)) 涉及不同容器。保留这些正确路径。

## 针对性回归

新增 `Tools/UI/check_woodworking_polylines.py`，编译实际 `WoodworkingPresentation.cpp`，使用小型带地址断言的容器/数学替身执行14项离线 C++ 回归：空、单点、两点、已闭合、重复点、34点且容量35、容量34触发扩容、旧表达式在两种容量下均被拒绝、空目标、空前景、单像素闭环、错误掩码尺寸、外轮廓和孔洞。全部通过；绘制入口短路径保护与12份文件的直接自引用模式另做静态核对。

这不是 UE/Slate 运行测试；替身只用于集中检验值复制与边界行为。真实 UE 类型/API 由随后常规 Editor/Game 编译验证。回归可在指定全新输出目录重跑：

```powershell
python Tools/UI/check_woodworking_polylines.py --project D:/FPS3D/FPSGAME --output C:/Users/allan/AppData/Local/Temp/woodworking-polyline-regression-new
```

## 本次构建与保存证据

串行后台构建包含现有 UE/UBT/cl/link 进程等待、目标二进制独占打开检查、最长60分钟等待边界；不使用 -WaitMutex，不关闭进程。

- Editor：`FPSGAMEEditor-20261009-091435.log`，退出0，Result: Succeeded，DLL 写入时间 **2026-10-09 01:14:50 UTC**。
- Game：`FPSGAME-20261009-091450.log`，退出0，Result: Succeeded，EXE 写入时间 **2026-10-09 01:15:13 UTC**。
- 本轮证据：`Saved/WoodworkingUICrash20261009/completion.json`、`build_receipt.json`、`Regression/receipt.json`、`Regression/regression.log`、两份构建日志和 `change.diff`。
- 修改前三份源码备份：`C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_ui_crash_20261009/Before`。

完成时核对38份受保护文件哈希不变，包括V4资产、正式调色板、woodworking.json、木工逻辑和独立锯片组件。未重导模型、修改真实存档、运行游戏/PIE、关闭任何其他进程或提交/推送。没有剩余编译阻塞；仍未实测用户的完整游戏交互场景，不将离线回归和构建成功写成游戏验收。
