# 配方手册打开崩溃修复（2026-10-16）

## 现象与证据

用户点击炼金工作台的“配方手册”后，预期进入实体书阅读界面，实际进程因断言退出。

本次读取现有崩溃记录，没有启动编辑器或游戏复现。崩溃时间为本地时间 2026-10-16 18:20:25，记录的引擎版本为 `5.8.3-58210709+++UE5+Release-5.8`。

证据已保存在 `SourceAssets/AlchemyManualOpenCrash20261016/Evidence/`，来源为 `Saved/Crashes/UECC-Windows-E3175954463B7AF15CAB8293BFE2FE6C_0000/`，包含原日志、CrashContext 与 minidump。修改前源码在同级 `Before/`。

首个失败点：

```text
Assertion failed: InLoadingPolicy != EFontLoadingPolicy::Inline
SlateCore/Private/Fonts/CompositeFont.cpp:135
ColdSteelAlchemyAction::Click
  -> ColdSteelAlchemyWidget::Book
  -> ColdSteelAlchemyBookPreviewWidget::Configure
  -> ColdSteelAlchemyBookWidget::Pages
  -> AlchemyManualLayout::Leaves / FragmentHeight / TextHeight
  -> AlchemyManualLayout::Font
  -> FFontData constructor assertion
```

## 原因与修改

仅修改 `Source/FPSGAME/UI/AlchemyManualLayout.cpp`：

1. 上次排版升级把通过 TTF 文件路径构造的字体设成 `Inline`。UE 明确限制此模式只用于 Font Face 资产内嵌字形数据，文件路径构造函数直接断言。恢复 `LazyLoad`，常规和半粗字体共用该修复。两个 TTF 文件存在，已有 UFS 暂存路径继续适用。
2. 沿相同打开流程发现下一处必然失败：测量文本时向 `FSlateTextLayout::Create` 传入 `nullptr`。本机引擎的 `FChildren(SWidget*)` 构造函数要求 `check(InOwner)`。这是源码确认的后续断言点，尚未出现在这份被字体断言提前终止的调用栈中。为测量创建局部、离屏 `SBox` owner，先构造 owner 再构造 layout，使 layout 析构时 owner 仍存活。

文字内容、字号、语义配色、分页规则、目录、拖动翻页与实体书资产不作改版。

## 构建与交付边界

`SourceAssets/AlchemyManualOpenCrash20261016/build.ps1` 使用共享 UE 批次互斥，等待已运行构建结束，再依次构建常规 `FPSGAMEEditor` 和 `FPSGAME` Development 目标；不运行游戏，不启动编辑器，不关闭已有进程。

本次两个目标均构建成功，产物已经落盘。回执为 `SourceAssets/AlchemyManualOpenCrash20261016/20261016-182438/result.json`，各目标日志同目录保存。源码定位和构建结果不代表游戏内验收；本次没有运行时复测。用户可重新打开工程，在原工作台点击手册，再查看目录与拖动翻页。

当前恢复链、退役文件归档和最终检查状态见 [手册收尾发布](../Publication/AlchemyManual20261016/README.md)。本文所述阶段结果保留为历史记录；本次整理未重新运行测试。
