# 唐刀限定改造金色卡片

用户要求将前轮限定改造的金色卡片同样应用于唐刀限定改造，直接制作和接入。

## 范围与呈现

显式武器、槽位、改造 ID：

| 武器 | 槽位 | ID | 显示名称 |
| --- | --- | --- | --- |
| ue_tang_dao | blade_1 | yanling_edge | 破锋燕翎刀身 |
| ue_tang_dao | blade_1 | tengyun_dragon | 腾云游龙刀身 |
| ue_tang_dao | pommel | yanling_breaker | 破锋燕翎配重锤 |

沿用既有 `ExclusiveCard / ExclusiveCardHover / ExclusiveCardPressed / ExclusiveBorder / ExclusiveText`：暗金卡面与金边、淡金标题、悬停提亮、按下压暗，状态显示“专属 · 已安装／已选 · 待应用／选择配件”。灰阶图标、已选绿色流动描边及收益／代价颜色继续沿用现有语义。

## 布局与交互合同

只在 Slate `UM4GunsmithWidget::BuildOption` 的显式专属身份判断中增加三组匹配。沿用既有卡片尺寸、响应式排列、滚动区、字体及所属区域模糊，不增加控件树或独立 Tick。原厂、共享改造和其他武器的呈现继续走原判断。

数据来自现有枪匠 `Option / Draft / Installed`，列表刷新仍走现有事件入口；选择、应用、数值、报价与存档继续走现有模型。输入焦点、工具提示限位、打开／关闭及解绑沿用原工作台生命周期。

## 文件与交付

实现：`Source/FPSGAME/UI/M4GunsmithLayout.cpp`。本次不生成新图标、材质或 UE 资产；复用前轮已落盘的共享样式。必要后台构建记录存放于 `SourceAssets/TangDaoMeshy20261002/ExclusiveGoldCards20261002/`，未启动编辑器／游戏，未进行视觉测试，由用户测试。

已完成后台 `FPSGAMEEditor Win64 Development` 和 `FPSGAME Win64 Development` 构建，两次均 `Result: Succeeded`，正式 Editor DLL 与游戏 EXE 已链接落盘。日志为 `build-editor-console.log`、`build-game-console.log`，此结果不代表游戏界面已测试。
