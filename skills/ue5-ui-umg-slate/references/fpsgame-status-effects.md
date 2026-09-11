# FPSGAME Buff / Debuff 显示桥

当前宿主 `D:/FPS3D/FPSGAME`，实现 `Source/FPSGAME/UI/StatusEffectsComponent.*` 和 `StatusEffectsHUD.*`。原版来源及散列见 `SourceAssets/MonsterFeedback20260911/reference/source.json`。

- 真实中毒与恐惧来自战斗组件，卡片不能自行加减效果。通用显示记录支持 timed、persistent、battle-count，不能把显示接口验收冒充全部效果玩法迁移。
- 新效果、叠层、消退使用 OnChanged；活跃倒计时按 0.1 秒刷新。Effect Type 不变时复用卡片，避免重建造成悬停闪烁。无效果隐藏。
- WorldSubsystem 创建单个本地 HUD，玩家重生后改绑新 Pawn，移除旧委托；World 结束清理定时器与视图。
- 原 HTML 使用 CSS 像素。本项目用 SDPIScaler 抵消 viewport DPI curve，卡片保持 54×44、左104/上12。提示定位使用缩放后 Root Canvas 的几何，不能混用外层 UserWidget 坐标。
- 本项目左 Alt 已有 GameAndUI / GameOnly 输入切换，复用它显示鼠标。验收需发送真实 Slate 鼠标移动和滚轮事件；直接调用 ShowTip 不能证明悬停可达。
- `Tools/MonsterFeedback/Run-Regression.ps1 -Mode Status` 检查实际中毒/恐惧数据、层数消退、计时/持续/场数、多行滚动、悬停、死亡/重生改绑。720p 和 1080p 画面分别验证；汇总读取本次 acceptance-summary.json。
