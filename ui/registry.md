# Godot UI 组件注册表（ui/registry.md）

> 借鉴 shadcn/ui 的「注册表 + 组件即代码 + AI 友好」模式，落地到 Godot UI 线：
> - shadcn `registry:ui` 条目 → 本表的每个组件条目；
> - shadcn `public/r/index.json` → 配套机器可读版 `ui/registry.json`；
> - shadcn 组件文档页 → `DESIGN.md`（风格唯一真源）+ 本表（组件接口/依赖/验收）。
>
> 本地 shadcn 文档站（部署参考）：`E:\3d\shadcn-ui`，
> 启动：`powershell -File tools/shadcn-docs.ps1` → http://localhost:4000

## 铁律

1. 新 UI 任务先查本表；能复用绝不新建，新页面 = 拼组件，差异只在布局与内容。
2. 新组件先登记（本表 + `registry.json`）再实现；改接口先改本表。
3. 所有组件只消费 `ui/style.gd` 的 Token，禁止裸 `Color(` 硬编码。
4. 状态：`stable` = 已通过门禁；`in_progress` = 有人正在改，动手前 `git status` 协调。

## 组件清单

| name | type | 文件 | 状态 | 依赖 | 接口 | 验收/测试 |
|---|---|---|---|---|---|---|
| style | tokens | ui/style.gd | stable | DESIGN.md（唯一风格真源） | `make_theme()` / `make_font(weight)`；`COLOR_*` 生效色板 / `THEME_*` 金白深灰待拍板启用 | tests/test_ui_tokens.gd |
| status_bar | hud | ui/status_bar.gd | stable | style | 消费 `player.gd`（damaged/died/hp）与 `gun.gd`（shot/reloaded/reloading/empty/hit/ammo/reserve）稳定信号；`_build()` 代码建 HUD | tests/test_ui_tokens.gd + test_status_bar.gd |
| npc_bar | hud | ui/npc_bar.gd | stable | style | `signal option_pressed(id)` / `close_requested`；`open(npc)` / `close()` / `is_open()` / `set_text()` / `skip()` / `open_demo()`（F8 调试） | tests/test_ui_tokens.gd + test_npc_bar.gd |
| npc_config | data | ui/npc_config.gd | stable | style | 商店目录/强化/改造/附魔/任务/稀有度只读配置；`standard_price` / `enhance_cost` / `can_enchant` 等 | tests/test_ui_tokens.gd + test_npc_panels.gd |
| economy | data | ui/economy.gd | stable | - | 金币：`get_gold` / `add_gold` / `deduct_gold`，signal changed | tests/test_ui_tokens.gd + test_npc_panels.gd |
| npc_panel | base | ui/npc_panel.gd | stable | style | 居中面板基类：`open_panel()` / `close()` / `set_title()` / `show_message()` / 金币标签 / 物品按钮助手 | tests/test_ui_tokens.gd + test_npc_panels.gd |
| npc_panels | host | ui/npc_panels.gd | stable | 全部 npc 面板 | `build(host,db,bp,eq,econ,npc_bar)` 一键挂 8 面板（含仓库）；`open(panels,npc_bar,id)`；`seed_materials(bp)` | tests/test_ui_tokens.gd + test_status_bar.gd + test_demo_terrain.gd |
| item_cell | widget | ui/item_cell.gd | stable | style | 复刻旧版 .inv-cell：稀有度竖条/图标/名称/堆叠/强化改造附魔徽章/价格角标；signal pressed(cell)/hovered(item) | tests/test_ui_tokens.gd + test_npc_panels.gd |
| drop_slot | widget | ui/drop_slot.gd | stable | style | 拖放接收槽：signal dropped(data)；拖拽高亮（旧版 drag-drop-manager） | tests/test_ui_tokens.gd + test_npc_panels.gd |
| craft_layout | widget | ui/craft_layout.gd | stable | style, npc_config | 改造布局编辑器：坐标格子+连线绘制+编辑拖拽；setup/set_editing/collect_slots | tests/test_ui_tokens.gd + test_npc_panels.gd |
| weapon_formula | data | ui/weapon_formula.gd | stable | - | attack-formula 移植：`compute_weapon_atk` / `formula_text` / `gun_mods_from_item` | tests/test_ui_tokens.gd + test_npc_panels.gd |
| warehouse | data | ui/warehouse.gd | stable | item_db | 100 格仓库：`add_item` / `count_material` / `consume_material` / `retrieve_all_to_backpack` | tests/test_ui_tokens.gd + test_npc_panels.gd |
| warehouse_panel | panel | ui/warehouse_panel.gd | stable | style, npc_panel, warehouse, backpack | 分页格子 + 存入/取出 | tests/test_ui_tokens.gd |
| shop_panel | panel | ui/shop_panel.gd | stable | style, npc_config, npc_panel, item_db, backpack, economy | `setup(db,bp,eq,econ)`；购买目录 / 出售栏（50% 价） | tests/test_npc_panels.gd |
| enhance_panel | panel | ui/enhance_panel.gd | stable | style, npc_config, npc_panel, item_db, backpack, economy | 强化槽 + 金币/强化石消耗 + 预测文本 | tests/test_npc_panels.gd |
| craft_panel | panel | ui/craft_panel.gd | stable | style, npc_config, npc_panel, item_db, backpack, economy | 改造槽 + mod 选择弹层（改造券 1/4 张）+ `_craftEffects` 聚合 | tests/test_npc_panels.gd |
| enchant_panel | panel | ui/enchant_panel.gd | stable | style, npc_config, npc_panel, item_db, backpack, economy | 卷轴/装备槽 + 魔法粉尘附魔 + 卷轴转粉尘 | tests/test_npc_panels.gd |
| quest_panel | panel | ui/quest_panel.gd | stable | style, npc_config, npc_panel | `signal teleport_requested(id)`；列表/详情/接受/传送 | tests/test_npc_panels.gd |
| fusion_panel | panel | ui/fusion_panel.gd | stable | style, npc_config, npc_panel, item_db, backpack | 20 格祭品合成：同稀有度两两升一级 | tests/test_npc_panels.gd |
| expedition_panel | panel | ui/expedition_panel.gd | stable | style, npc_config, npc_panel, item_db, backpack | `signal depart_requested(items)`；10 格祭品 + 稀有度准入 | tests/test_npc_panels.gd |
| item_tooltip | tooltip | ui/item_tooltip.gd | stable | style, item_db | `signal close_requested`；`render(item)` / `is_pinned()` / `set_pinned(v)` | tests/test_ui_tokens.gd |
| backpack_hud | panel | ui/backpack_hud.gd | stable（Vega 金白已升级） | style, backpack, equipment, item_tooltip, icons | `signal player_healed(hp)`；`setup(bp, eq)`；Tab/B 开背包、拖拽、右键使用 | tests/test_backpack.gd + test_ui_tokens（已纳入硬编码扫描） |
| backpack | data | ui/backpack.gd | stable | item_db | `signal changed / item_used / item_added / bound`；`add_item` / `remove_item` / `swap_items` / `bind_hotbar` / `resolve_hotbar` | tests/test_backpack.gd |
| equipment | data | ui/equipment.gd | stable | backpack | `signal changed / equipped`；`equip_from_backpack` / `equip_to_slot` / `unequip` / `swap_equip` / `is_locked` | tests/test_equip.gd |
| item_db | data | ui/item_db.gd | stable | assets（旧版 equipment.json） | `has_item` / `get_def` / `get_all_ids` / `create_instance` | tests/test_ui_tokens.gd |
| style_config | config | ui/style-config.json | stable | style.gd 自动读取 | `radius` / `spacing` / `font` / `font_weight` / `motion` / `active_theme` | tests/test_ui_tokens.gd |
| icons | tools | ui/icons.gd + assets/ui/icons/*.svg | stable | Lucide 48 图标 | `get_icon(name)` / `apply_icon(rect, name, color)` / `has(name)` | tests/test_icons.gd |
| tabs | widget | ui/tabs.gd | stable | style | `signal tab_changed`；`add_tab(title)` / `select(i)` / `current()` | tests/test_components.gd |
| switch | widget | ui/switch.gd | stable | style | `signal toggled`；`set_on(v)` / `is_on()` | tests/test_components.gd |
| checkbox | widget | ui/checkbox.gd | stable | style, icons | `signal toggled`；`setup(text)` / `set_on(v)` / `is_on()` | tests/test_components.gd |
| slider | widget | ui/slider.gd | stable | style | `signal value_changed`；`setup(min,max,step,val)` / `get_value()` | tests/test_components.gd |
| input | widget | ui/input.gd | stable | style | `signal text_submitted`；`setup(label, placeholder)` / `get_text()` / `set_text()` | tests/test_components.gd |
| select | widget | ui/select.gd | stable | style | `signal item_selected`；`setup(label)` / `add_item` / `select` / `get_selected_id()` | tests/test_components.gd |
| context_menu | widget | ui/context_menu.gd | stable | style | `open_at(pos, items)`（支持 separator） | tests/test_components.gd |
| navigation_menu | widget | ui/navigation_menu.gd | stable | style, icons | `signal item_activated`；`add_item(title, icon)` | tests/test_components.gd |
| command_palette | widget | ui/command_palette.gd | stable | style | `signal command_selected`；`register(id, label)` / `toggle()` / Ctrl+K | tests/test_components.gd |
| settings_demo | demo | scenes/ui/settings_demo.tscn + ui/settings_demo.gd | stable | 全部通用组件 + 金白主题 | 独立场景，F6 运行；tabs 切换画面/音频/游戏 | tools/ui_preview.gd 截图验收 |

## 新组件登记模板

```markdown
| name | type | ui/<name>.gd | draft | style, ... | 接口摘要 | tests/test_<name>.gd |
```

登记后同步在 `ui/registry.json` 的 `components` 数组加一条；实现完跑门禁通过后把状态改为 `stable`。

## AI 使用提示

- 动手前：读 `DESIGN.md` + 本表 + `ui/style.gd` 的可用 Token。
- 需要交互/数据：先看 `backpack.gd` / `equipment.gd` / `item_db.gd` 提供的信号与方法，UI 只消费接口。
- 需要视觉：一律走 `style.gd` Token；新色值路径 = `DESIGN.md` → `style.gd` → 组件。
- 需要参考成熟交互：打开本地 shadcn 文档站，把按钮/弹窗/拖拽的无障碍交互要求翻译成 Godot 实现。
