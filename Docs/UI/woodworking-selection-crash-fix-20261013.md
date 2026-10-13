# 木工选择卡片绘制崩溃修复

## 原因与证据

本次新增的 SWoodworkingPatternDrawing::OnPaint 使用 `Lines.Add(Lines[0])` 闭合轮廓，将 TArray 自身元素引用传给同一数组的 Add。UE 的 CheckAddress 明确拒绝此调用，即使已 Reserve 多一个元素也会断言。

用户 2026-10-13 10:06 的崩溃日志记录 ArrayNum=4、ArrayMax=5、SizeofElement=16，对应直边毛坯的四点 FVector2D 轮廓及预留的闭合点。日志：Saved/Crashes/UECC-Windows-FB26A1094CA0F18940F3B3B3827A966B_0000/FPSGAME.log:5548。

## 修改

仅替换 WoodworkingPanel.inl 的轮廓闭合调用，复用已有 WoodworkingPresentation::ClosePolyline；该函数先将首点复制到局部值再追加，避免自引用，并处理已经闭合的轮廓。保留卡片布局、横排文字、选择/进入流程与其他并行修改。

源码备份及必要后台构建记录：Saved/WoodworkingSelectionCrash20261013。未启动 UE、未运行游戏或测试；构建不代表实际运行验收。

## 构建过程

前两次 Editor 构建分别遇到并行库存头文件与 UHT 生成内容不一致、并行新增 SprintCameraMotion.h 暂未落盘的问题。没有修改相关模块；后续共享 Editor 构建已成功，成功日志复制到 Editor-completed-shared.log（原日志 Saved/Super90StockCloseout20261013/Editor-UHT.log）。

本次 WoodworkingPanel.inl 修改时间为 10:07:55，包含它的 ColdSteelWoodworkingWidget.cpp.obj 生成于 10:09:38，最终 UnrealEditor-FPSGAME.dll 于 10:17:51 完成链接，均为 2026-10-13 本地时间。修复已纳入 Editor 构建产物。

FPSGAME Win64 Development 后台构建成功、退出码 0；日志为同目录 Game.log。Editor 与游戏版本均已编译落盘，未做实机复现或测试，交由用户确认。
