# shadcn → Godot UI 映射矩阵（docs/shadcn-mapping.md）

> 目的：把 shadcn/ui 的设计语言**逐项登记**地翻译进 Godot，避免"凭感觉翻译、隐性失真"。
> 用法：每次翻译组件/Token 前查本表；每一项都有对应物与验证方式；差异必须显式登记并拍板。
> 参考源：本地文档站 http://localhost:4000（E:\3d\shadcn-ui，官方仓库 v4）。

## 0. 不失真的三层保障

1. **映射矩阵（本表）**：shadcn 每一项 → Godot 对应物 → 验证方式，没有"差不多"栏。
2. **数值断言**：颜色/尺寸/间距/字号等数值型由 `tests/test_ui_tokens.gd` 自动校验，错一个就红。
3. **截图验收**：组件形态用 GLM-4.6V 读图并排对比（Godot 渲染 vs shadcn 参考页），差异列表给人拍板。

## 1. 硬指标 vs 软指标

| 类别 | 含义 | 示例 |
|---|---|---|
| 硬指标（必须 1:1） | 数值可精确搬运 | 色值、尺寸、间距、字号、圆角、状态色、时长 |
| 软指标（允许等效，显式登记） | 实现机制不同，只能视觉等效 | 阴影模糊、发光、动效曲线、hover 细节、玻璃模糊 |

软指标的差异必须在翻译时写进本表对应行，用户知情后拍板，否则视为失真。

## 2. 颜色 Token 映射（shadcn 31 个 → palette.json）

| shadcn Token | 含义 | Godot 对应 | 当前值 | 状态 |
|---|---|---|---|---|
| `--background` | 全局背景 | `THEME_BG` | `#0F0F10` | ✅ 已映射 |
| `--foreground` | 主文本 | `THEME_WHITE` | `#FFFFFF` | ✅ |
| `--card` / `--card-foreground` | 卡片底/字 | `THEME_BG`(α0.8) / `THEME_WHITE` | 玻璃面板 | ✅（等效映射） |
| `--popover` / `--popover-foreground` | 浮层底/字 | `COLOR_TT_BG` / `COLOR_TT_NAME` | 白浮窗 | ✅（旧版浮窗） |
| `--primary` / `--primary-foreground` | 主强调/其上字 | `THEME_GOLD` / `THEME_WHITE` | `#D4AF37` | ✅ |
| `--secondary` | 次级面 | `THEME_GRAY_MID` | `#3A3A3C` | ✅ |
| `--muted` / `--muted-foreground` | 弱化底/弱化字 | `THEME_GRAY_MID` / `THEME_GRAY_LIGHT` | `#3A3A3C` / `#B5B5B5` | ✅ |
| `--accent` / `--accent-foreground` | 悬停强调 | `THEME_BTN_HOVER_BG` / `THEME_WHITE` | 金底 | ✅ |
| `--destructive` | 危险 | `THEME_DANGER_RED` | `#D95B4A` | ✅ |
| `--border` | 边框 | `THEME_GRAY_MID` | `#3A3A3C` | ✅ |
| `--input` | 输入框边 | `THEME_GRAY_MID` | `#3A3A3C` | ✅ |
| `--ring` | 聚焦环 | `THEME_GOLD` | `#D4AF37` | ✅（待 Godot focus 实现） |
| `--chart-1..5` | 图表色 | `THEME_HP_GREEN` / `THEME_WARN_ORANGE` / `THEME_DANGER_RED` / `THEME_MP_BLUE` / `THEME_GOLD` | 状态色组 | ✅（游戏无图表，映射到状态色） |
| `--radius` | 圆角 | `style-config.json` → `Style.RADIUS` / `make_style()` | 8px | ✅ 已配置化 |
| `--sidebar*` | 侧栏系列 | 暂不需要 | — | ⛔ 无侧栏 UI |

> 注：我们 Godot 的 Token 是扁平命名（THEME_*/COLOR_*），shadcn 是语义命名；映射关系登记在上表后，
> 语义差异不再靠翻译者记忆。新增 shadcn token 出现时先补本表再落地。

## 3. 非颜色风格维度

| 维度 | shadcn 规范 | Godot 对应物 | 当前值 | 状态 |
|---|---|---|---|---|
| 间距 | 4px 网格 | `style-config.json` → `Style.spacing(key)` | DESIGN.md 第 4 节 | ✅ 已配置化 |
| 字体 | Heading/Inter + 字重阶梯 | `style-config.json` → `Style.font_size/font_weight`（思源黑体） | 12–48 阶梯 | ✅ 已配置化 |
| 图标 | Lucide 线性图标 | `assets/ui/icons/*.svg`（96px，黑色 stroke）+ `ui/icons.gd` | 48 个图标，modulate 任意着色 | ✅ 已落地 |
| 动效 | 150–250ms ease-out | Tween | DESIGN.md 第 7 节 | ✅ 已按规范 |
| 阴影/发光 | 柔和阴影 | Shader / 半透明叠加 | 仅关键元素发光 | 🔶 等效实现，待登记 |
| 玻璃模糊 | backdrop-blur | Godot 无原生 backdrop blur | 半透明深灰近似 | 🔶 软指标（已用 α0.8 面板） |

> 主题切换：`style-config.json` 的 `active_theme`（`dark_gold` 旧暗金 / `gold_white_gray` 金白深灰）。
> 金白板 = 把 THEME_* 按语义覆盖到 COLOR_*（`Style._apply_theme_preset()`），组件零改动。

## 4. 组件映射（shadcn 63 个 → 我们的 registry）

### 已落地 / 已有对应

| shadcn 组件 | 我们的组件（registry） | 状态 |
|---|---|---|
| progress | `status_bar.gd` 血条/经验/弹药条 | ✅ 已迁移 |
| tooltip | `item_tooltip.gd`（三段式浮窗） | ✅ 已迁移 |
| dialog / sheet | `backpack_hud.gd`（侧滑面板 + 遮罩） | ✅ 已迁移 |
| dropdown-menu | 快捷栏 + 装备右键交互 | 🔶 部分（行为已做，视觉按暗金板） |
| badge | `COLOR_BADGE_*` 稀有度/改造/附魔徽章 | ✅ |
| toast / sonner | `status_bar.gd` 状态提示/命中标记 | 🔶 雏形 |
| button | `THEME_BTN_*` 三态 | 🔶 规范已定，金白板未启用 |
| skeleton / spinner | 加载占位 | ⛔ 游戏加载不需要 |
| avatar | 玩家头像 | ⛔ 暂无需求 |
| table / calendar / chart | 游戏 UI 不需要 | ⛔ |

### 待做（按优先级，进 registry 先登记）

| shadcn 组件 | 预期用途 | 优先级 |
|---|---|---|
| tabs | 背包分类页 / 设置页分页签 | ✅ 已落地（ui/tabs.gd） |
| switch / checkbox / slider | 设置页（音量、灵敏度） | ✅ 已落地（ui/switch.gd 等） |
| input / field | 设置页文本输入 / 搜索 | ✅ 已落地（ui/input.gd） |
| select / combobox | 设置页下拉 | ✅ 已落地（ui/select.gd） |
| separator | 面板分隔线（现用 THEME_DIVIDER） | ✅ 已有等效 |
| command palette | 开发者工具（跳转场景） | ✅ 已落地（ui/command_palette.gd，Ctrl+K） |
| context-menu | 装备右键菜单 | ✅ 已落地（ui/context_menu.gd） |
| hover-card | 物品悬浮卡片（现 tooltip 已覆盖） | ⛔ 等效 |
| navigation-menu | 主菜单 | ✅ 已落地（ui/navigation_menu.gd） |

## 5. 翻译工作流（每个组件固定六步）

1. 查本表：shadcn 组件对应的 Godot 目标、硬/软指标。
2. AI 实现：Token 全部走 `palette.json` / `style.gd`，新颜色先补表再落地。
3. 数值断言：`test_ui_tokens.gd` 及相关组件测试跑绿。
4. 截图对比：Godot 渲染截图 vs shadcn 参考页，GLM-4.6V 逐项读图列差异。
5. 差异拍板：软指标差异登记本表；硬指标差异必须修正。
6. 登记 registry：组件进 `ui/registry.md` + `registry.json`，`ui:` 提交。

## 6. 当前翻译总览

- ✅ 颜色层（31 个 token 中 27 个已映射，4 个 sidebar 明确不需要）
- ✅ 动效规范（150–250ms ease-out）
- ✅ 圆角/间距/字号/动效/主题开关（style-config.json + 调色面板「风格配置」tab）
- ✅ 图标层（48 个 Lucide SVG + icons.gd）
- ✅ 组件层（HUD/背包已迁移；tabs/switch/checkbox/slider/input/select/context-menu/nav/command-palette 全落地）
- ✅ 设置面板 Demo（scenes/ui/settings_demo.tscn，F6 运行测试）
