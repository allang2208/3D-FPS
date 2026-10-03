# 图鉴新增「附魔」主分区规划（2026-10-03）

## 目标与交付阶段

- 名称、入口、解决的操作需求：图鉴（`N` 键，右侧抽屉第 4 页）新增第 5 个主分区「附魔」，收录现有全部 14 种附魔卷轴的词缀效果，供玩家离线查阅每种卷轴的效果说明、兼容武器与消耗；只读档案，不提供附魔操作（附魔在强化台完成）。
- 范围与用户已确定的内容：用户指定「给图鉴添加一个新卡片-附魔，把现有的所有附魔卷轴效果添加其中，主要按照 UI 规则开展工作」。版式沿用图鉴状态／祭品分区的整页独占规则（2026-09-29/30 定案）。
- 阶段：游戏接入。用户已授权实现，规划后直接实施；默认不运行游戏、不截图，由用户测试。
- 对照的现有面板、实际源码与规范版本：
  - 源码：`Source/FPSGAME/UI/ColdSteelCodexPage.h/.cpp`（状态／祭品整页模式同源复用）；
  - 数据真源：`Content/ColdSteelData/enhancement.json` 的 `scrolls` 数组 → `UColdSteelEnhancementSystem::Scrolls()`（强化台附魔栏同一入口）；卷轴物品字段（稀有度／字形图标）读物品目录 `UColdSteelStatusModel::CreateItem` 的物品 Data（与背包／浮窗同源）；
  - 规范：`Docs/UI/ui-cold-steel-design-system.md` §4（字体字号）、§17（图鉴栏系统）；`skills/ue5-ui-umg-slate/references/fpsgame-panels.md`。

## 信息结构与布局

面板 → 主分区页签（武器／怪物／状态／祭品／**附魔**）→ 分类页签（全部／前缀／后缀）→ 整页「附魔卡片 · <稀有度>」分组平铺 → 底部快捷键页脚（既有）。

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 主分区页签 | 五项等宽等高 | 顶部 | 同 | 固定 | 恒显 |
| 分类页签 | 全部／前缀／后缀（附魔分区下） | 页签行下居中 | 同 | 固定 | Section=4 |
| 搜索栏 | 按名称／说明／兼容过滤 | 卡片区上方 | 同 | 固定 | Section=4 |
| 附魔卡片·<稀有度> | 组头（稀有度色标签+计数）+ 条目行 | 整页独立滚动 | 同 | 内容滚动 | 组内命中>0 |
| 条目行 | 字形(稀有度色)+名称 14 Medium+右侧 前缀/后缀 12；次行 兼容·粉尘 12；三行效果说明 12 换行 | 同上 | 同上 | 随组滚动 | 恒显 |

- 断点：整页分区不参与「网格+详情」两列/纵排切换（`StackedBelowWidth` 只作用于武器/怪物分区），与状态／祭品一致。
- 长说明自然换行（`Label()` 既有 AutoWrapText(true)）；组内空组跳过；无 legendary 组数据时整组不出卡。
- 空态：无命中显示「此分类暂无附魔档案」（未搜索）／「没有匹配的附魔：换个关键词或清空搜索。」（搜索中），装入「附魔卡片」分区卡。

## 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 分区卡片 | `SectionCard`（StatusCard 底、CardRadius、1px Border） | 标题 16 Medium | 既有缓存画刷 |
| 条目弱行底 | `StatusEntryBrush`（AttributeRow，全条目共享一枚，随 DPI 重算） | — | 既有 |
| 名称/说明/兼容 | Noto Sans SC | 名称 14 Medium、兼容 12、说明 12（TextSecondary/Tertiary） | 工程字体 |
| 计数/粉尘数值 | JetBrains Mono | 12 | 工程字体 |
| 条目字形 | 物品 `icon_fallback`（emoji 字形回退口径与祭品页一致） | 16，`RarityColor` 着色 | 物品 Data |
| 稀有度组头标签 | `RarityColor`/`RarityLabel` 单一来源 | 16 Medium | 既有 |

不新增贴图、不新增主题值、不另建第二套文案表（前缀/后缀用词与强化台 `ColdSteelEnhancementWidget` 一致）。

## 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 卷轴清单（14 条） | `UColdSteelEnhancementSystem::Scrolls()` | enhancement.json `scrolls` 全量（图鉴是档案，不受「背包持有」过滤——那是强化台的合同） | 组间稀有度高→低（复用祭品组序表），组内粉尘升序、同名按名称 | 打开分区／搜索输入／切页签重建 | 只读，无写入 |
| 名称／槽位／兼容／粉尘 | `FColdSteelEnchantOption` 的 Name/Slot/Restriction/Dust | 同上 | Slot prefix/suffix → 前缀/后缀；Restriction 八键 → 中文映射表（未知值如实显示原文） | 同上 | 只读 |
| 效果说明 | `FColdSteelEnchantOption.Description`（enhancement.json `description`，强化台悬停同一字段；items.json 的短 desc 不作效果口径） | 同上 | 原文换行显示 | 同上 | 只读 |
| 稀有度/字形 | `Model->CreateItem(Option.Item)` 的 `rarity`/`icon_fallback` | items.json 物品 Data（缺失时字形 `?`、归「—」尾组如实显示） | — | 同上 | 只读 |
| 分类过滤 | 页签 0=全部、1=前缀、2=后缀；显式映射表 `EnchantCategorySlots[]`+`static_assert` | 与搜索叠加 | — | 切页签清空选中（本分区无选中态） | 只读 |
| 搜索 | 复用 `SearchEdit` 缓存输入框；命中 名称/说明/兼容标签/卷轴 id，大小写不敏感 | 输入即过滤，只重填卡片区 | — | OnTextChanged | 只读 |

本分区为纯展示：不读背包数量、不报价、不扣粉尘/卷轴、不写存档——与强化台「只计背包正数量堆叠」的合同 deliberate 分离（图鉴收录全目录，强化台只列可用的）。

## 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 目录为空/搜索无命中 | 「附魔卡片」空态卡 | 见信息结构 | 无选择态 |
| 搜索输入 | 只重建 `EnchantCardsHost` | 提示词「搜索附魔：名称 / 说明 / 兼容」 | 焦点保留（不重建整页） |
| 切换分区/页签 | 重建整页；`SearchEdit` 文本跨分区保留（既有行为） | — | 滚动随重建回顶 |
| 打开/关闭抽屉 | 复用宿主既有开关与输入模式 | — | 关闭不穿透世界攻击 |

- 键鼠入口：`N` 开图鉴，页签/卡片点击；无立绘请求、无 portrait 队列（不占渲染资源）。
- Construct/Destruct：沿用 `RebuildWidget`/`ReleaseSlateResources` 既有生命周期；`EnchantCardsHost` 在 Release 时 Reset。

## 文件范围与交付

- 修改：`Source/FPSGAME/UI/ColdSteelCodexPage.h`（+EnchantCardsHost、三个方法）、`ColdSteelCodexPage.cpp`（页签数组 4→5、BuildPage 路由、Categories/SectionLabel/Entries 分支、RebuildFilterCards 分支、三个新函数、限制键映射表）。
- 文档同步：设计系统 §17 追加附魔分区条款；`skills/ue5-ui-umg-slate/references/fpsgame-panels.md` 追加同条（个人技能与仓库镜像一致）。
- 无资产新增、无退役文件、无容量/存档变化。
- 必要构建：Game+Editor 双目标；构建成功≠画面已验证。
- 用户预览/测试：未要求，由用户实机测试。
