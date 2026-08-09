# UI 面板化审计报告（2026-08-09）

> 目的：核对所有 UI 面板是否统一走 Style 面板体系（玻璃/内嵌/槽位贴图族 + tt_* 排版 + Token 色），
> 灰白（gray_white）主题下是否有破坏项。方法：全量扫描 `ui/*.gd` 的面板构建、样式来源、字体、
> 圆角、裸色；门禁 = `tests/test_ui_tokens.gd`（硬编码扫描已扩展到 25 个通用组件）。

## 1. 面板清单与样式来源

| 面板 | 文件 | 样式来源 | 状态 |
|---|---|---|---|
| 主背包/装备面板 | backpack_hud | `make_glass_panel_style` + blur shader + 拉丝纹理层 | ✅ 统一 |
| 属性页内嵌卡 | status_page | `make_inner_panel_style`（灰白/暗色自动） | ✅ |
| 设置面板 | settings_demo | `make_glass_panel_style` | ✅ |
| 命令面板 | command_palette | `make_glass_panel_style` | ✅ |
| 物品/属性/HUD 浮窗 | item_tooltip / status_page / status_bar | `COLOR_TT_*` 白卡 + `tt_*` 排版 | ✅ |
| 快捷栏容器 | backpack_hud | 半透明玻璃（THEME_BG 30%） | ✅ |
| 格子/槽位（背包/快捷/装备/技能） | backpack_hud | `make_slot_texture_style`（明暗主题自动选贴图） | ✅ |
| 页签激活态 | backpack_hud | `make_tab_active_style`（明暗主题自动） | ✅ |
| NPC 面板/栏 | npc_panel / npc_bar | `make_panel_style`（平坦半透明，非玻璃系） | ⚠️ 其他线 |
| 锻造/附魔/强化/仓库/商店 | craft / enchant / enhance / warehouse_panel 等 | 各自 `make_style`，未统一 | ⚠️ 其他线 WIP |
| 全局加载界面 | loading_screen | 独立样式 | ⚠️ 其他线 |

## 2. 一致性检查

### 2.1 面板样式 ✅
主面板/设置/命令/属性卡/槽位全部走 Style 面板体系，灰白与暗金主题自动切换贴图与色板，无第二套面板语言。

### 2.2 字体 ✅（待显式化，低优先）
- 浮窗已统一 `tt_*`：标题 16/700、分组 12/600、正文 12/400、数值 12/600（雅黑）。
- `make_theme()` 默认字体 = 雅黑、字号 = 14（body），未显式挂字体的组件继承同一家族/字号，视觉一致。
- ⚠️ 其他线新面板存在游离字号（13/30/9 等），未入阶梯，建议纳入 `Style.font_size`/`tt_*`。

### 2.3 圆角 ✅（建议常量化，低优先）
槽/条/浮窗使用 3–12 硬编码，数值与 RADIUS 阶梯（4/6/8/12）一致；后续建议统一替换为 `Style.RADIUS_*`。

### 2.4 灰白主题兼容 ✅
全 UI 线扫描无"深底/白字"破坏项（裸色扫描已清空，门禁覆盖 25 个组件）；item_tooltip 关闭按钮白字在红底上两主题均正确。

### 2.5 硬编码门禁 ✅
`test_ui_tokens.gd` 组件裸色扫描：status_bar / item_tooltip / backpack_hud / command_palette / status_page /
settings_demo / switch / checkbox / slider / input / select / tabs / context_menu / navigation_menu /
hud / sound / backpack / equipment / skillbar / skill_page / icons + 其他线 npc/仓库/商店面板，裸 `Color(` 即红。

### 2.6 布局 ✅
背包 25 格（5×5）底部 1031px 不超屏；背包面板 z=110 位于快捷栏 z=100 之上；快捷栏在暗/灰白主题均为半透明玻璃。

## 3. 待办（按线归属）

- **UI 线（低优先）**：① 组件显式字号化（开关/滑条/按钮 label 走 `Style.font_size`）；② 圆角数字 → `RADIUS_*`。
- **其他线**：NPC/锻造/仓库/加载面板并入玻璃系 + `tt_*` 阶梯；warehouse_panel 当前 parse error 待修。

## 4. 提交前规则（沉淀进 WORKFLOW）

1. 新面板一律用 `Style.make_glass_panel_style` / `make_inner_panel_style` / `make_slot_texture_style`，禁止面板级 `make_style`。
2. 字号一律 `Style.font_size` / `tt_*`，禁止裸数字。
3. 颜色一律 palette Token，跑 `test_ui_tokens` 门禁。
4. 灰白主题交付前跑本审计扫描（`tools/audit_ui_panels.py` 可复用，见下）。
