# 冷钢面板标准开发工作流

2026-09-06更新。开发任何新游戏面板或修改现有面板，必须遵守[当前冷钢标准](docs/cold-steel-ui-standard.md)，不得回到旧情绪板、旧黑体正文或旧字号方案。

## 1. 开工前读什么

依次读取AGENTS.md、WORKFLOW.md、DESIGN.md、当前冷钢标准和skills/godot-cold-steel-ui/SKILL.md；查ui/registry.md与实际组件代码。迁移原面板时读原快照index.html、基础CSS、主题覆盖CSS、对应JS的DOM与事件链。

记录一份面板合同：入口/关闭返回目标、占屏比例、分区顺序、字体角色、数据源、允许操作、取消/失败行为、保存时机、空状态和禁用状态。原项目已有布局时直接使用其规则，不为已有明确目标重新生成候选图或要求用户重复选风格。

## 2. 先复用结构和数据

- HUD由autoload拥有；NPC类面板优先复用npc_panel生命周期及npc_panels注册。
- 用Control、MarginContainer、Box/GridContainer、ScrollContainer组织；不靠字符串空格、手工换行或固定像素坐标拼完整布局。
- 标题、正文、物品名、纯数字分别使用公共字体入口。Label物品名用Style.style_item_name；不要在新面板构造另一个FontVariation。
- 所有配色、字号、间距查公共Token。确需新增先记录来源和语义，再补Token或reference adapter。
- 交互只调用装备/背包/仓库等数据层；保留实例ID、加工属性、弹药和保存结构。原有战斗信号接口保持不变。

## 3. 代码排版模板

```gdscript
const Style = preload("res://ui/style.gd")

func make_panel_title(text: String) -> Label:
    var label := Label.new()
    label.text = text
    label.theme = Style.make_theme()
    label.add_theme_font_override("font", Style.make_heading_font(20))
    label.add_theme_font_size_override("font_size", Style.font_size("h2"))
    return label

func make_item_name(text: String) -> Label:
    var label := Label.new()
    label.text = text
    label.theme = Style.make_theme()
    Style.style_item_name(label)
    label.add_theme_font_size_override("font_size", Style.font_size("label"))
    label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
    return label
```

普通正文使用Style.make_font()，数字使用Style.make_mono_font()。分区用make_heading_font(16)与16px。不要把整页全部变成加粗SimHei。

## 4. 交互与状态必须成套实现

打开/关闭、Esc、焦点、鼠标捕获、重复打开和中途关闭动效一起检查；使用已有动效工具，不在每页另起动画系统。菜单必须处于正确CanvasLayer，不被遮罩或其他面板吞掉。

预览类操作分开已应用状态、草稿和确认；撤销/切换/关闭按合同处理。拖放校验既覆盖_can_drop_data也覆盖实际drop入口，禁用外观和禁用行为一致；锁定槽不能仅显示叉号却继续接收物品。

与背包联动的面板保留先背包后仓库/加工抽屉顺序。小窗口允许滚动，底部关键操作独立于内容滚动区。非正常路径不得越界写入、悄悄丢失物品或扣除资源。

## 5. 字体排查顺序

1. 核对源CSS层叠、实际DOM角色和内联样式，记录字号/字重/行高/字距/阴影。
2. 核对打包字体是否正确、是否为SimHei及正确的0/0.9字重、控件实际字体及是否发生fallback。
3. 查控件与父级缩放、DPI与viewport，再比较同字号样张。
4. 查是否遗留局部embolden或引擎默认RichText加粗字体；只修定位明确的差异。
5. 同文件同参数仍有差异再比较灰度/LCD抗锯齿、hinting等，未经对照不要全局重导字体。

## 6. 验证与证据

- UI改动运行 `tests/test_ui_tokens.gd` 检查Token与硬编码，并运行相关组件检查；新增组件同步registry.md和registry.json。
- 按WORKFLOW.md第4节执行无头导入（新增资源时）、180帧启动、combat/reload及本次相关检查。
- 启动前设置独立INVENTORY_SAVE_PATH；确认HUD不会读写正式玩家存档。
- 实际GPU渲染并查看1920/1280主布局及960小窗口；保留正常、空、禁用、长文本、预览/应用/取消的必要证据。
- 同尺寸同状态对照源与实现；拒绝空白、仍加载、被其他窗口覆盖或动效未稳定的截图。
- 检查字体家族、四档字号、标题字距、名称粗细、数字对齐、容器裁切、滚动和固定按钮。
- 业务变动跑能覆盖真实风险的测试；纯样式不要写只复述参数的无意义测试。
- 逐项记录通过/问题/未验证，不宣称完整无障碍或所有功能100%复刻。

## 7. 交付、沉淀与整理

有用规则更新DESIGN/当前标准/本流程，对应经验写入项目SKILL，新增组件更新registry。原快照只用于来源，不把Godot适配值改写回原CSS；刷新快照另按manifest规则处理。

保留正式脚本、最终截图、源资产和许可证；废案只删除本任务创建且已确认无引用的明确文件，配套UID/import一起处理。禁止全库clean/reset/add -A。提交和普通推送严格按WORKFLOW.md第8节，混合未发布提交使用独立发布工作区；推送后回读SHA。不要把他人未提交实现或模型依赖夹进本任务。

枪械改造页面最终格式见 [改造UI合同](skills/godot-weapon-workflow/references/gunsmith-ui.md)；以本次最终要求为准。
