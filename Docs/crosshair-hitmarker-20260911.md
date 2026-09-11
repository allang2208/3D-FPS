# 准心命中提示（2026-09-11）

- 准心中心四角绘制四段白色斜线，保持中心空白；1080p 下每轴由 10 px 延伸至 20 px，线宽 2 px，随 HUD 高度缩放。
- 最大不透明度 65%，停留 60 ms 后在 180 ms 内淡出；连击刷新同一个提示，不叠加亮度。
- 腰射、ADS 均显示，保留 LPVO 倍率提示；打开库存、仓库、鼠标操作或翻越时隐藏。
- 弹道、即时射线和穿透命中均读取 ApplyPointDamage 返回值，仅对非自身 Pawn 且实际伤害大于零触发，墙面不触发。
- 编译：UnrealEditor-FPSGAME-9111431.dll 成功。
- 实机：run_ballistic_presentation.ps1，22 项通过、0 失败。新增验证包括墙面、零伤害、真实弹道目标命中、淡出、连击刷新、到期及 ADS 显示。即时射线路径本次只做编译验证。
- 截图：Saved/BallisticPresentationAudit/05-hip-hitmarker.png、06-ads-hitmarker.png。使用隔离审计靶（不可见 Pawn 碰撞体），背景墙面本身不触发命中提示。
