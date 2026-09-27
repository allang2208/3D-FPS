# 锻造落锤加速与冲击感

用户要求落锤速度加倍并增强打击感。本次通过运行时已读取的 `Content/ColdSteelData/forge-grip.json` 调整，不改 C++，不进行 Live Coding。

| 阶段 | 原时序（秒） | 新时序（秒） |
| --- | --- | --- |
| 起手抬锤 | 0–0.16 | 0–0.16 |
| 落锤 | 0.16–0.34（0.18 秒） | 0.16–0.25（0.09 秒） |
| 锤面接触 | 0.34 | 0.25 |
| 接触停顿 | 0.34–0.38 | 0.25–0.29 |
| 回弹峰值 | 0.45 | 0.36 |
| 恢复待机 | 0.82 | 0.73 |

下落段的中间关键帧也按同一映射压缩：0.24 → 0.20 秒。接触后 40 ms 固定锤面，不下穿剑胚；回弹高度从 5 cm 增为 6 cm，角度从 -15° 增为 -18°，接一个小幅回落再恢复待机。保留握柄关系、骨长及既有腕肘解算。接触之后的总恢复阶段仍为 0.48 秒，光圈生成的随机间隔与交互缓冲不变。

现有运行逻辑把 `contact_seconds` 同时传入锻造判定并用于 `Contact()`，因此评分、用户提供的打铁录音及火星跟随新的 0.25 秒接触点。无需另改声音起始时间或特效延迟。

作者入口统一到 `Tools/Forging/forge_stroke.py`；完整模型作者 `author_forge.py` 也复用该动作表。已完成运行 JSON 保存和 `rebake_forge_motion.py` 的可编辑动作重烘焙，源文件为 `SourceAssets/ForgeInteraction20260927/ForgeTools_V7_Grasp.blend`，之前的 JSON/Blend 保留于 `BeforeFastDownstroke`。动作标记从同一数据取时序。

锻造交互创建时读取 JSON；当前已打开的打铁面板需退出并重新进入。无需导入新 UE 资产或编译 DLL。未主动运行游戏、试听、截图或测试，手感由用户确认。

> 2026-09-27 发布整理：BeforeFastDownstroke 作者快照已移至 trash/forging-publication-20260927/SourceAssets/ForgeInteraction20260927/BeforeFastDownstroke。当前快速落锤源与参数保留。
