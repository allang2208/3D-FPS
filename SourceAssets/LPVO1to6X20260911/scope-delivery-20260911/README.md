# LPVO ADS 大视野交付

现有网格与材质保留。ADS 改为主相机 FOV 放大 + 独立光学镜框，清晰圆口直径为屏幕短边 85%，在 1600×900 下约 765 px。旧 6× 原始图像的清晰圆口约 270 px；显示口径扩大约 2.8 倍，圆形可用面积约 8 倍，场景放大倍率仍为 1–6×。

LPVOScopeWidget 在 HUD 下方绘制 256 段圆形薄边框与轻微边缘羽化，没有额外 SceneCapture 或 RenderTarget。分划与射击方向均按主相机中心，保留相机后坐力及原有弹道系统。它是游戏光学显示，不是物理镜片折射模拟。

镜框随 CameraADSFactor 平滑进入和退出；中段切换仅持枪者不可见的视模/配件。外部模型、改造预览、库存图标继续使用原资产。退出 ADS、换弹、切枪后恢复被该功能隐藏的组件。1× 同样使用大圆口，固定二倍镜及其他瞄具显示方式未变。

滚轮仍每格 0.5×、初始 1×、上下限 1–6×，退出再开镜保留本次武器的倍率。跨进程倍率存档未扩展。血量、快捷栏和弹药 HUD 在镜框上层，倍率提示单独放在快捷栏上方。

本目录的 write/reload 日志、1/2/4/6× 及 reopen 截图来自独立测试存档。lpvo-hip-restored 是关闭光学显示后的实际外观；m4-holographic-fire/reload 是沿用审计命名的 LPVO 开火/换弹画面。aperture_acceptance.json 由 verify_scope_aperture.py 对实际截图测量外缘口径、检查中心分划和 HUD，不能替代性能基准。

编译日志：../build_scope_delivery.log（Result: Succeeded）。此前 full-aperture 和 scope-release 目录是修正 HUD 分层/倍率提示位置之前的中间验证。

最终验收：write 116 项、reload 112 项，均 0 失败，共 228 项通过；12 张实际截图的口径、分划和 HUD 检查通过。已检查 6× 大口径和退出 ADS 的外观恢复画面。
