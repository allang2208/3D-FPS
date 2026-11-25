---

name: ue5-ui-umg-slate

description: Plan and implement UE5.6-UE5.8 panels, tabs, sections, cards and popups using UMG and Slate. Use for new UI or UI upgrades, FPSGAME Cold Steel design rules, panel/column workflows, Widget Blueprint setup, lifecycle binding, data visibility, input/focus, tooltips and viewport layout.

---

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

- **2026-10-27 优先规则**：浮窗、改造栏与数值交付统一写 `暴击率+10%`、`暴击伤害+10%`，不用中文百分比单位；按[百分比显示规则](references/percentage-display.md)执行，覆盖旧显示写法，保留实际公式。 原因：统一百分号写法可以保持不同界面的指标名称和阅读口径一致，文字调整不改变公式。

- 新增或修改武器／配件介绍，先读 [详情与介绍编写标准（2026-10-09）](../ue5-weapon-workflow/references/attachment-detail-presentation.md)：只列直接属性；攻击分段、附加伤害拆分与派生值默认不列，总览也不保留，仅按用户明确要求例外；独立机制简述，外观不复述数值；区分改造台绿色特效、物品浮窗整行说明及武器背景介绍。 原因：同一个数值在不同区域重复或换口径展示会产生歧义，详情需要保留明确的数据来源。

## 执行约定

遵守用户全局规则：后台制作、不主动测试、不跨对话协调。涉及 UE 构建或资产操作时，按需读取[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)；已读则复用。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

## FPSGAME 性能开发约束（2026-09-23）

新增 HUD、快捷栏、状态面板或图标时，读取 [性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md) 的高频路径与图标部分。先明确刷新触发和调用链，复用属性读取与可见条目，不把重复 JSON 解析、全量控件重建或资源等待放进 NativeTick。 原因：高频显示路径会放大重复计算，按变化刷新才能保留同样内容而减少无效工作。

# Quick Start

- 出征页奖励/规则空白、行前准备与缩略图刷新，读取 [出征面板的真实内容](references/expedition-live-content.md)，共享实际掉落表和角色数据。

- 改造栏图标采用用户认可的金属方框图片，PNG 已含边框时不重复绘制或内缩；分类、原厂、选项与强化入口共用 [改造图标标准](../ue5-weapon-workflow/references/attachment-icons.md)。

- 背包 F 转向后图标缩小、透明留白与拖动尺寸跳变，读取 [运行时图标的横竖比例](references/runtime-icon-pipeline.md)，同步目录图和动态图的可见轮廓规则。

- 枪械、弓、近战与生产工具浮窗的字段命名、伤害口径、核心摘要及改造／强化一致性，读取 [武器浮窗固定格式](references/weapon-tooltip-schema.md)；共用 `ColdSteelWeaponText.h`，计算条件与字段名称分开表达。

- 启动选档、进场加载、重试与取消页面，读取 [资源准备与交互状态](../ue5-performance-packaging/references/entry-resource-preparation.md)，沿用 `TransitLoadingSubsystem` 和冷钢共享样式。

- For FPSGAME building categories, construction cards, model thumbnails, fonts or detail popups, read [the building-panel standard](references/building-panel.md).

- For FPSGAME persistent panel icons, hotkey effects, dual-pistol layout, or melee stamina readouts, read [HUD navigation and weapon readouts](references/hud-navigation-and-weapon-readouts.md).

- For FPSGAME new panels, tabs, sections, cards, or UI upgrades, first read [panel planning and Cold Steel rules](references/fpsgame-panels.md). Plan structure, layout, data scope and states before implementation; use the project's current design system.

- For FPSGAME inventory drawers, detached item menus, or drag/close regressions, read [inventory input and validation](references/fpsgame-inventory-input.md).

- For a blurry weapon/item preview, incomplete-looking materials, or transparent SceneCapture composition, read [preview rendering and texture residency](references/preview-rendering.md).

## UI 实现合同

- 沿用最近的现有面板和冷钢设计规则，先明确布局、数据、空态、禁用态、选中态和操作提交方。原因：共享外壳与状态语义能让新栏目保持既有使用习惯。
- 规划属于制作准备；用户已授权实现时继续完成，不增加规划后的重复审批。原因：本次授权决定工作阶段，文档步骤不应制造新的阻塞。
- UMG、Slate 或二者桥接按现有面板架构和实际需求选择，不因通用模板强制更换技术。原因：现有数据、输入和控件生命周期已经与所属框架相连。
- 展示控件从现有模型读取数据，操作回到业务提交入口；高频内容沿用事件或失效通知刷新。原因：在显示层重复写玩法状态或每帧重算全量数据会造成状态分叉和额外开销。
- 注册委托、计时器与预览资源时明确所属控件，关闭或销毁时释放对应绑定。原因：反复打开面板会暴露悬挂回调、重复订阅和预览资源滞留。
- 打开、嵌套弹窗与关闭分别处理输入模式、焦点和返回目标。原因：焦点遗留可能吞掉玩法输入，关闭按键也可能穿透触发攻击。
- 提示框根据实际锚点与视口限制位置，保持悬停来源稳定；文本沿用全系统横排与现有字体规则。原因：边缘反复换位会造成闪烁，窄列逐字换行会降低可读性。
- 控件生命周期与输入 API 使用当前工程的实际签名；不保留跨 UE 小版本完全一致的承诺。原因：桥接方式和框架版本会影响可用接口，通用列表不能证明项目兼容。
- 保存和必要构建照常完成；重开巡检、截图、多分辨率和交互测试仅按用户要求执行。原因：制作完成与界面验收需要分开报告，默认工作流不应启动额外测试。

接口定位：`UUserWidget` 的构造/销毁、`RemoveFromParent`、输入模式与焦点；自定义 Slate 入口及 `TakeWidget` 仅在现有桥接需要时使用。原因：这些入口分别控制对象寿命、输入归属和显示宿主，能直接定位对应缺陷。

# FPSGAME Reference

- For this project's Buff / Debuff display, read [the status-effects bridge](references/fpsgame-status-effects.md).

## 技能图标系列

生成或替换冷钢技能图标时，读取 [技能图标系列](references/skill-icon-series.md)。

## 弹药袋与圆形选择

弹药袋子页、按弹种数量等分的 R 轮盘、鼠标选择和图标缓存，读取 [动态弹种轮盘与弹药袋](references/ammo-radial-and-pouch.md)。

## 运行时图标与诊断界面开销

处理动态图标首次准备卡顿、图标通知全量刷新或诊断文本反复失效时，读取 [运行时图标准备](references/runtime-icon-pipeline.md)。

## 动态面板生命周期与布局

- 点击代理 UObject 由专用 UPROPERTY 容器持有，生命周期跟随实际绑定；不随普通行缓存重建而失去引用。原因：被回收的代理会让委托静默失效。
- 贴缝凸舌按所贴面板或弹层填色，Normal 状态透明，悬停和按下才加反馈；使用现有逐角圆角工具处理接缝。原因：凸舌承担面板边缘延伸，重复卡片边框会显得与主体分离。
- 按当前全系统规则保持文字横排，窄按钮优先调整宽度或布局。原因：旧的“升\n级”竖排示例已不符合当前可读性要求。
- 交付区分源码、基础 DLL 与已加载进程；必要构建后台完成，不主动触发 Live Coding、重启或运行验收。原因：源码和补丁状态不能证明下一次启动会加载什么版本，运行中的编辑器也可能仍持有旧模块。
- 用户要求排查代理回收时，可显式触发 GC 后再观察委托路径。原因：此方法针对对象寿命故障，不是所有 UI 改动都必须运行的回归门槛。

## 背包拖拽：装备栏旋转与拖到仓库换装（2026-09-24）

- 拖拽中按 F 的来源包括背包（Place 0）、装备栏（Place 1）和仓库/箱子（Place 4）。朝向只在落点是背包或仓库时写入；装备槽放下仍用作者朝向。 原因：背包展示方向与身体接触面承担不同用途，混用会让预览或穿戴朝向错误。

- “可旋转”预览只在悬停背包或仓库、且来源是 0/1/4 时打开。从装备栏拖到背包或仓库可以转；悬停装备槽不要提示可转。 原因：装备槽不消费旋转方向，提示可转会给用户一个不会生效的操作。

- 从装备栏拖到仓库时，落点锚格上、能装备进空出槽位的那件换上；覆盖到的其余物品进背包。背包放不下则整次移动取消。预览文案是“松开替换装备”。双手武器换上时副手按现有规则进背包，进不去就中止这次装备。

- 仓库堆叠合并的余量必须带回源容器和源宽高。余量若先改掉 `Container` 再提前返回，箱子里的物品会变成主仓库物品。

## 锻造材料与已投入工件

处理制作材料红绿提示、数字分列、已支付材料与领取／废弃状态时，读取 [锻造材料与已投入工件](references/forging-materials.md)。

## 成品参数与准备提示

锻造成品等宽预览、配方下拉选择及体力条上方蓄力／架枪进度，读取 [成品参数与准备提示](references/product-preview-readiness.md)。

## 常规工作台与枪械组装

处理制作栏规格、直接制作、分件配方、下拉行 GC 崩溃或完成后返料时，读取 [工作台面板与结算](references/crafting-workbenches.md)。

## 生存与消耗品（2026-10-03）

[冷钢生存状态栏](references/survival-status-layout.md)：等级框与资源区的独立 Grid、语义轨道、状态提示和历史方案归档。

- 涉及统一 E 交互小浮窗（FPSGAME，2026-09-24 定版）时，读取[统一 E 交互小浮窗（FPSGAME，2026-09-24 定版）](references/unified-interaction-hint-popup.md)。

物理书本、纸面文字/图片、长按拖动与书签跳转，读取 [物理书本阅读器](references/physical-book-reader.md)。

- 玻璃容器式能量条顶部补全、上下端帽对称及魔法漂浮光粒，读取 [浮动能量条端帽](references/energy-vessel-caps.md)，使用实际布局反射并保留版本间制作输入。

- 世界工作台拖动卡片、场景命中坐标及四位置种植布局，读取 [工作台拖动与四位置种植](references/world-workbench-drag-and-four-plots.md)。

地图系统的实景底图、输入焦点和冷钢标记表现，读取 [实景底图、地图输入与标记表现](references/world-map-navigation.md)。

新增村民对话、货架详情或排查无 RHI 的目录图标时，读[村民对话与商店预览](references/resident-dialogue-and-shop-previews.md)。

名册卡片与并排装备详情参见[名册卡片与并排装备详情](references/roster-cards-and-equipment-detail.md)。
