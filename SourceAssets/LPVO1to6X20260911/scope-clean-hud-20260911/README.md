# 高倍镜隐藏所有游戏面板

FPSGAMEPlayerController::PlayerTick 在 LPVO 光学显示过半时记录本玩家顶层 Widget 的可见性并隐藏，ScopeOverlay 除外；退出或开始菜单交互后恢复原状态。包含血量、时间轴、快捷栏、弹药、天气按钮、快捷提示、倍率提示；引擎屏幕调试信息不作游戏面板处理。

build_scope_clean_hud_final.log 编译成功。write.log：116 项、0 失败。reload.log：112 项、1 失败（fire input consumes rounds）；本次高负载重载启动超过辅助脚本 180 秒等待，进程仍自行完成并正常退出，截图于完成后补收集。不能把重载称为全部通过。

verify_scope_aperture.py 本目录 --hidden-hud：12 张开镜截图全部通过，验证面板消失、圆口、中心分划及两阶段退出 ADS 后面板恢复。相关倍率、再次开镜、镜体恢复检查通过。重载的开火计数失败与 HUD 验证分别记录，未改动或放宽开火断言。
