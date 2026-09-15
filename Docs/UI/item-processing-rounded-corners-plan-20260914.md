# 装备与背包加工角标圆角匹配

2026-09-14，用户要求装备栏及背包中的强化、改造、附魔三角角标贴合物品卡片圆角。本轮直接修改并接入，未要求预览或测试。

- 结构与布局：复用 `ColdSteelInventoryPresentation.cpp` 的物品卡片绘制；右上强化、右下改造、左下附魔位置和自适应尺寸沿用现状。卡片半径使用共享物品卡主题值，角标按内缩距离计算同心圆弧；保留朝内的三角斜边，边缘加窄透明过渡。
- 数据与状态：继续读取 `Presentation` 中的强化等级、改造和附魔标志；未加工状态不绘制。原有语义色、错相扫光、悬停、选中与拖动透明度沿用；不新增业务写入或存档字段。
- 所属层与输入：现有 UMG 控件通过 Slate 自绘实现；沿用模型事件刷新、装饰动画 Paint 失效及 Construct/Destruct 管理。仅改绘制几何，命中、拖放、焦点、滚动及浮窗定位继续由原控件管理。仓库复用相同物品绘制入口，同步获得相同边缘形状。
- 文件范围：`ColdSteelInventoryPresentation.cpp`、`ColdSteelUIStyle.h`、正式 UI 规则和技能案例；无新增图片、材质或退役资源。
- 交付：完成必要 Editor 原生构建；不主动运行游戏、截图、检查或测试，由用户测试画面。

实施状态：代码、共享主题和规范已修改。用户关闭编辑器并要求继续后，`Tools/Build/Build-Editor.ps1` 完成 `FPSGAMEEditor Win64 Development` 构建，结果 `Succeeded`；日志为 `Saved/BuildEditor/build-20260914-214555.log`。构建输出含现有 `Building/VoxelCollapseFragment.cpp:17` 的两条 double 转 float 警告，本轮未修改该文件。未运行游戏或测试，实际圆角与扫光效果由用户测试。

## 装备栏细缝复查与修正

用户随后反馈背包贴合，但装备栏右侧仍有细缝，并要求按相同方式检查其他角与边。此次检查范围为角标、卡片边框、冷却覆盖、三列装备和空间背包的绘制几何；不扩展到库存玩法回归。

- 源码发现：固定内缩 2px 比普通 1px 边框多留出 1px；卡片 `MakeBox` 默认像素吸附，而角标 `MakeCustomVerts` 保留小数位置。三列装备宽度 `(Width-36)/3` 可产生小数，左右两类绘制的取整偏移不一致。
- UE 5.8 本机源码依据：`SlateCore/Private/Rendering/ElementBatcher.cpp` 的 `AddBoxElements` 根据像素吸附选择顶点取整；`Shaders/Private/SlateShaderCommon.ush` 的 `GetRoundedBoxElementColorInternal` 将外半径减去描边厚度作为内轮廓半径，并在内边界作半像素过渡。
- 修正：统一卡片实际最小／最大坐标；底色、冷却覆盖和最终边框关闭独立像素吸附，与自绘角标一致。角标按当前 1／2px 描边减去 0.5px 重叠量定位，外圆弧随之同心缩放；最后绘制一次外框，使颜色和扫光压在轮廓下。上、下、左、右直边共用该矩形，三个加工角不再各自平移补偿。
- 小尺寸角标复查：旧网格把半径限制为尺寸的一半，会破坏小背包格的同心关系。改为先保证尺寸容纳半径，允许圆弧与三角尖端相接；弧线端点使用精确坐标，透明边去除重合点。
- 左上没有加工角标，继续保留原标题与高光；使用同一最终圆角边框。点击、拖动和占格仍读取原布局，未改变格子边界。

本轮已完成上述源码检查与修改；`Build-Editor.ps1` 构建 `FPSGAMEEditor Win64 Development` 成功，日志 `Saved/BuildEditor/build-20260914-223904.log`。输出仍有现有 `VoxelCollapseFragment.cpp:17` 的两条浮点转换警告。本次未启动游戏，尚未进行游戏画面检查，实际贴合效果由用户测试。
