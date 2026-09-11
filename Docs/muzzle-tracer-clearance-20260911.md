# 枪口发射点与横移曳光修正（2026-09-11）

实际发射点按当前枪口附件出口世界位置加枪管前向 2 cm 计算，在重播开火动画前与瞄具射线一起取样。原装、消音器、制退器、钛制制退器均应用。Niagara 火光仍定位物理出口。摄像机到发射点的遮挡检测覆盖新增偏移，ADS 目标仍取瞄具方向。

原先每次弹道推进产生静止圆柱并保留 35 ms，导致横移时叠加多个历史帧。现在每段仅绘制生成帧；FX 在 PostUpdateWork 清除旧帧段，实际飞行由原 Ballistics 系统负责。最大可见段长由 140 cm 改为 45 cm，直径由 0.65 cm 改为 0.35 cm。飞出的子弹继续沿世界空间弹道运动。

验证：Editor Development 构建 UnrealEditor-FPSGAME-9111731.dll 成功。60 Hz 独立实机通过 67 项、0 失败，含四种枪口的实际 Launch 起点、ADS 左右后坐力下实际命中误差小于 1 mm、左右各 1 秒横移连射、旧帧清除及停弹后无曳光残留。

30 Hz 独立实机也通过 67 项、0 失败；帧到期清理不依赖固定毫秒寿命。日志：Saved/BallisticPresentationAudit-20260911154015.log。

60 Hz 日志：Saved/BallisticPresentationAudit-20260911153841.log。
实机横移录屏：Saved/BallisticPresentationAudit/strafe-tracer-fixed.mp4（120 帧，2 秒）。
预览：Saved/BallisticPresentationAudit/strafe-tracer-fixed.gif。

此前已打开的编辑器需要重新启动以加载新原生模块。本次没有关闭其他会话编辑器。
