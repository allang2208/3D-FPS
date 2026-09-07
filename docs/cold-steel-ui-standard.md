# 冷钢 UI：当前 Godot 执行标准

2026-09-06 收尾版。用户确认枪械改造字体，并要求所有新面板遵守。此文是Godot适配规则；原game-dev快照保持原始字节，不修改其CSS/JS或manifest。

## 规则优先级

用户已确认的当前要求 → 本文与DESIGN.md → 原快照对应组件的实际CSS、DOM和交互 → 公共Theme实现。旧暗金情绪板、旧字号和旧SKILL说明不再决定当前样式。不能只读主题变量：index.html先加载game-style.css，再加载冷钢覆盖层，内联样式也需核对。

源资料：[完整快照](reference/game-dev-cold-steel/README.md)、[设计系统](reference/game-dev-cold-steel/docs/ui-cold-steel-design-system.md)、[主题CSS](reference/game-dev-cold-steel/ui/panel-theme-backpack.css)。开发步骤见[面板工作流](../UI-WORKFLOW.md)。

## 字体合同

| 内容语义 | 字体入口 | 字号/处理 |
|---|---|---|
| 普通正文、按钮、输入、说明 | Style.make_font() | SimHei，14px常规，embolden 0 |
| 辅助信息 | Style.make_font() | 12px；原HUD紧凑标签11px |
| 面板标题 | Style.make_heading_font(20) | SimHei加粗（embolden 0.9），20px，字距2px |
| 分区标题 | Style.make_heading_font(16) | SimHei加粗（embolden 0.9），16px，字距1px |
| 加载/页面显示标题 | Style.make_heading_font(24) | 24px，字距2px |
| 物品、武器、配件名称 | Style.make_item_name_font()；Label用Style.style_item_name() | SimHei，统一embolden 0.9，轻阴影 |
| 纯数字、容量、堆叠、坐标、冷却 | Style.make_mono_font() | SimHei常规（embolden 0），按所在信息层级选字号 |

六档24/20/16/14/12/11px，普通单面板最多四档。背包格物品名12px、装备名称及空槽标签16px；详情标题可20px。稀有度竖标、图标、地牢等级徽章沿用原组件例外，不视为正文。中数混排与纯数字均使用同款常规SimHei。

字体文件由assets/ui/fonts提供，统一simhei.ttf；标题/名称0.9粗化，正文/数字0粗化。不要各面板另建字重。RichTextLabel使用主题normal_font/bold_font/mono_font，字体家族保持一致。

原CSS标题tracking为0.08em、分区0.04em；2px/1px是Godot整数字距近似。embolden 0.9是用户认可的Godot效果，不是CSS600的换算公式。轻阴影和CSS模糊不逐像素等价。字体不对时依次核对字体文件/face、实际字体、字号、字重、字距、阴影、缩放，最后才比较渲染后端，禁止盲改全局抗锯齿。

## 配色与组件

颜色入口ui/palette.json，尺寸与档位ui/style-config.json，代码统一消费ui/style.gd；有原组件精确样式时集中在reference style适配器，不散落页面。

- 炭黑#171d23、石墨#232b33，正文#eef3f5，辅助#9ca8b1，低强调#6b7882。
- 冷银强调#8ea6b2、明银#c4d3da；旧Token名字含GOLD不代表实际为金色。金色只用于金币等真实游戏语义。
- 外壳渐变#181e24（.98）→#070a0d（.99），控件#35414a→#20272e，悬停#43505b→#273038。
- 普通壳圆角10px，控件6/8px，细边框、滚动条8px；特殊组件按原CSS证据，不擅自统一掉例外。
- 按钮默认、悬停、按下、禁用、焦点状态完整；不以持续闪烁、弹跳代替状态反馈。

## 布局、操作和动效

1. 背包45%屏宽、全高、250ms水平滑入；背包装备页使用黑化深青冷钢表面，空槽微凸、占用槽压下，不再使用白色格面。仓库先联动打开背包，再展示仓库抽屉；关闭、焦点和鼠标捕获沿现有生命周期。
2. 枪械改造是用户授权的全屏工作台例外：宽屏左选枪、中预览、右配件与说明；宽度不足1200时配件移到预览下方，底部撤销/应用固定。保留真实枪械实例、允许部位、预览草稿与应用保存的边界。
3. 长列表使用容器与滚动，长名称允许省略但详情可查看；不要缩小全局字体硬塞内容。关键确认动作不能被滚动区遮住。
4. 拖动显示实际物品的半透明预览；取消/失败不消耗、不丢失、不复制实例属性。装卸、仓库、加工暂存、保存走业务层，UI不私改共享武器资源。
5. 双手锁定：weapon→offhand，weapon2→ring2；禁用槽背景rgba(120,120,120,.6)→rgba(90,90,90,.7)，边框#444，整格opacity .6，名称#888，图标灰度且opacity .5，中心32px粗体黑✕与白色光晕。无悬停/点击/拖放；拖动结束仍维持.6，卸下或换单手恢复。只封锁禁用槽UI目标，快捷装备副手支援物的冲突卸装规则按原业务保留。
6. 原右侧栏目PNG应复用实际资源。不要用emoji或近似画图替换已有正式图标；已有源组件符号保留其角色。

## 验收与发布边界

必须保存同窗口尺寸、同状态的原图与实渲染图，检查字体、字距、裁切、禁用/空状态；主要分辨率1920×1080与1280×720，小窗960×540检查滚动与关键按钮。不能把空白/未稳定截图当通过。

按WORKFLOW.md跑规定检查，测试前设置独立INVENTORY_SAVE_PATH。记录实际通过、失败、未覆盖项，不把复制规则、静态检查、截图或退出码0说成完整业务复刻。

本收尾发布以规则、工作流、SKILL、公共字体接口为界；本地已实现的全屏枪械、时钟及部分面板改进仍与未发布武器/历史UI提交关联，不通过此文声称远端已具备所有本地功能。

枪械改造页面最终格式见 [改造UI合同](../skills/godot-weapon-workflow/references/gunsmith-ui.md)；以本次最终要求为准。
