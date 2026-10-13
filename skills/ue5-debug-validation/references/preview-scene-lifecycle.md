# 保留预览 World 时释放渲染场景

适用：FPreviewScene 闲置回收、释放 FScene 保留 UObject 世界、EndPIE/预览清理出现插件渲染线程访问异常。

## 生命周期合同

释放捕获组件、被摄体和 RenderTarget，与释放整个 FScene 是不同层级。世界子系统可能保存 Scene 引用，即使预览世界没有显式摆放对应物件。不要只执行 Scene->Release() 并把 World->Scene 置空。

UE 5.8.3 的 UWorld::RecreateScene 在旧场景释放前广播 FWorldDelegates::OnPreRecreateScene，重建渲染场景/关卡资源后广播 OnPostRecreateScene。DynamicWind 在前者中排队注销 provider，后者中重新注册；退出世界时才注销一个仍引用旧 Scene 的 provider 会访问失效资源。复用本机引擎的生命周期顺序，使插件注销先于场景销毁，不用关闭风效或加入每帧 FlushRenderingCommands 掩盖错误。

这对委托只存在于 WITH_EDITOR。没有等价运行时合同的构建应保留空场景到正常世界清理，继续回收闲置模型/捕获/目标；不要把 Editor 内省下的场景缓存量写成独立运行已经节省。

## 诊断与结论边界

关联 BeginTearingDown、预览世界 CleanupWorld、最近一次场景释放与崩溃模块/偏移。插件栈不等于该地图某个风场物件错误；也不能将退出崩溃当作刷怪低帧的统一根因。排查 provider 保存的引用以及注销队列顺序。

FPSGAME 2026-10-13：ColdSteelPreviewScene 修订了缺失的通知，常规 Editor 构建成功；当日停止优化前尚未完成退出试玩/恢复预览的运行验证。后续从 Docs/Backlog.md 的地牢怪群条目继续，不写成已证实彻底解决。
