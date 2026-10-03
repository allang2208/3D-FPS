# 天气筛选打开详情修复 2026-09-27

用户报告事件进度栏的“天气”按钮不显示下方天气详情。
原因：HandleTimelineFilterWeatherClicked 已绑定 OnClicked，但 RefreshEventTimeline(true) 重建详情后调用 SetTimelineDetailsOpen(false)，使点击始终关闭详情。
修复：刷新后使用 bTimelineHasEvent 打开详情。没有天气事件时仍收起；重复点击不切换关闭。全部筛选、轨道标记的切换行为保持原样。

编译：当前已运行编辑器内 Live Coding 返回 Result: Success / Live coding succeeded；日志 Saved/BuildEditor/event-weather-click-live-result.txt。当前会话已应用热补丁；正式常规 DLL 尚未重编译。未运行交互测试。
