# F6 生成物品下拉分组布局（2026-10-03）

## 范围与结构

用户已授权调整 F6 → 基本调参 → 生成物品的下拉列表。复用现有开发抽屉和冷钢主题；数量、生成按钮和档案事务沿用现有入口。

下拉按「类别标题 → 标题下方分隔线 → 子类标题 → 缩进物品行」排列。武器按实际 weaponType／weaponTypeTag 分为手枪、步枪、机枪、近战、弓等；消耗品按 type 分为常用消耗品、食物、附魔卷轴。其他已有类别完整保留，仅有实际条目的类别／子类才显示。标题与分隔线不参与选择。

## 布局与主题

- UMG 开发面板持有一个 Slate 下拉控件；菜单使用 SComboButton、SScrollBox 和实际物品按钮。
- 类别标题 16px 中等字重、子标题 14px 中等字重、物品正文 14px，统一 ColdSteelUI 字体与黑灰／银白主题。类别标题下方为 1px 分隔线，物品相对标题缩进。
- 下拉入口沿用 320px 弹性宽度和 36px 操作高度；窄窗继续走既有卡片重排。菜单宽度至少适合正文且不超过视口，最高 480px，同时限制到视口高度的一半以内，沿用菜单自动翻转与窗口内弹层。
- 菜单独立滚动，长物品名称换行并提供全文提示；菜单打开时定位当前选择，键盘焦点移动时滚动到对应物品。

## 数据、状态与生命周期

- 数据来自 UColdSteelStatusModel::ItemCatalog() 与现有 AmmoCatalog() 箭矢补充；类别 → 子类 → 名称 → Definition 排序。分类只在现有目录缓存构建时读取 JSON，不增加 Tick 全量解析或控件重建。
- 选择始终按 Definition，显示名称重名不影响生成。重开 F6 保留仍有效的选择，失效时选择首个实际物品；无目录时显示「暂无可生成物品」并禁用下拉及生成。
- 只有实际物品按钮发送选择事件，生成仍走 Model->AddItem(Definition, Count)；背包、弹药袋、容量和保存规则不变。
- 关闭 F6、切换页签或释放 Slate 资源时关闭弹层；使用既有控制器输入模式与返回游戏流程，菜单委托由 UObject 生命周期管理。

## 文件与交付

新增 DevelopmentItemPicker.h/.cpp，调整 DevelopmentPanelWidget、DevelopmentPanelTools、ColdSteelDevelopmentTools 与目录行元数据；无新增图片或 UE 资产。

完成必要 Game／Editor 后台构建并落盘，不启动 UE、游戏、预览或测试。运行时画面与操作由用户测试。

## 实施记录

已接入独立的不可选择类别标题、标题下方分隔线、子标题与缩进物品按钮；选择按 Definition 保留，长名称换行，当前选择在展开时滚动到可见区。关闭面板、切换页签、视口／DPI 改变或销毁控件时关闭弹层。

Game 与 Editor 后台构建均成功，编译产物已落盘。最终构建日志及状态：`Saved/F6ItemGroups20261003Retry1/gameBuild.log`、`editorBuild.log`、`delivery.json`；首轮日志保留于 `Saved/F6ItemGroups20261003/`。未启动 UE、游戏或任何测试。
