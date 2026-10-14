# 暴风雪修复（2026-10-12）

承接 [源码排查](blizzard-audit-20261012.md)，用户授权修复发现的问题。范围与持续时间的成长公式、基础伤害、蓝耗、冷却、无需法杖的装备条件均保留。

## 施法与联机事务

- 客人凝聚后等 Phase 0 成功回执再发送释放；Phase 1 发出后保留付款预留和施法占用，收到成功回执才提交本地冷却、释放连锁／急速奖励并清云。拒绝则由两端分别退回真实预留并解除占用。镜像已提交时不重复提交。
- 取消等待可靠回执后释放本技能槽；释放请求已发出时，死亡或菜单操作只清表现，由释放回执决定提交／退款。离场时已发出的释放不保留可读档退款的本地凝聚状态，权威失败由服务端档案回写。
- 暴风雪释放和取消不受原有 150 ms 静默丢弃影响；凝聚过快明确回传拒绝。通用取消仅清理对应技能的预留，不误清其他技能。
- 服务端在释放被拒、角色死亡／丢失、凝聚超过持有时限加动作与传输余量时清理预留并退款。Phase 2／3 取消即使 pawn 已离场也能收尾。
- 本地与服务端共用地面重验：落点附近重新找实际地面、禁止跳到其他楼层、核对坡度、最大距离及施法视线。单机落点无效可重选；联机权威拒绝则退款取消。创建区域前清除失效引用并执行每人最多四区限制。

入口：`FPSBlizzardComponent.*`、`Multiplayer/ColdSteelPlayerState.cpp`。

## 区域时钟、加载与净空

- 区域复制服务端开始时间和结束状态；客户端从同步世界时间算年龄，停止降雪／寒雾／落冰出生，随后沿原 0.6 秒消散。迟收到的区域只显示剩余时间；客户端不结算修炼奖励。
- 远端 15 个资源通过一次异步请求准备，保留生命周期引用；不在 Tick 内同步 `LoadObject`，离场取消请求。
- 25 个相邻盒体向上扫掠覆盖云团足迹，包含采样点之间的横梁，每 0.5 秒更新一次；隔墙的采样点和起点贴墙／地面的扫掠不作为顶部净空。遇低顶立即压低，净空恢复时平滑回升。
- 云的高度、厚度由服务端复制；四层 49 团云使用表面法线对齐、零贴片旋转及独立厚度，避免宽贴片转动后竖直穿顶。低顶下落冰装饰随净空缩小，范围伤害仍从原地面椭圆独立结算。
- 云改用 `/Game/Skills/Blizzard/ClearanceV4/NS_BlizzardStormCloud`；保留当前近手凝聚云、雨雪、薄霜、寒雾和冰锥资产。

入口：`FPSBlizzardZone.*`。定向制作 `Tools/Skills/build_blizzard_clearance_v4.py`；共享作者 `build_blizzard_charged_v3.py` 同步厚度／朝向，并在完整恢复后调用 V4 作者。既有 Blizzard Cook 目录包含 V4。

## 进度与界面

- 加入统一升级通知，显示新等级的完整椭圆宽深与持续秒数。
- 接入现有 F6 技能目录与定义路由，可选暴风雪升一级／升满级。
- 技能详情改为凝聚、点按或长按预览后释放、释放后冷却、菜单保留完成凝聚、30 秒持有到期退款；列明持续时长的升级档位。

入口：`ColdSteelSkillModel.cpp`、`Development/ColdSteelDevelopmentTools.cpp`、`UI/ColdSteelSkillPage.cpp`。

## 交付状态

源码和制作脚本已落盘。V4 云资产已由后台 Python commandlet 编译并保存，日志为 `Saved/BlizzardFix20261012/asset-build.log`，保存回执为同目录 `asset-authoring.json`；commandlet 正常退出，0 个错误，5 个现有插件 Python 重名导出警告。

`FPSGAMEEditor Win64 Development` 常规构建已成功，基础 `UnrealEditor-FPSGAME.dll` 与 `UnrealEditor-ColdSteelNet.dll` 已完成链接；日志 `Saved/BlizzardFix20261012/Editor-build-final.log`，Result: Succeeded。此前构建受到工程中移动模块编译错误影响；相关源码更新后重新构建成功，本轮没有修改移动模块。

`FPSGAME Win64 Development` 常规构建也已成功，`Binaries/Win64/FPSGAME.exe` 已完成链接；日志 `Saved/BlizzardFix20261012/Game-build.log`，Result: Succeeded。两项目标都是常规基础构建，不依赖 Live Coding 补丁。

未启动图形编辑器、游戏、PIE、截图、渲染或自动测试；源码、Niagara 编译和构建结果不代替用户实机与联机体验。
