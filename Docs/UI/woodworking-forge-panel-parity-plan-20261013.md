# 木工管理面板对照铁匠复刻 · 2026-10-13

用户提供铁匠与木工截图并要求对照源码复刻，尤其上方必须是下拉选择框。此版覆盖旧选择卡方案；正式配方继续只有猎手长弓、学徒长杖。

## 结构与样式

以 ColdSteelForgingWidget 当前 UMG 构建树及 UpdateScale 为依据：固定标题栏 → 滚动主体（配方/工件标题、居中下拉框、同卡材料表；工件状态及指标/返料；左右等宽的成品图片与真实参数；常展开操作说明）→ 固定状态提示及等宽操作按钮。复制同源玻璃、标题底、边线、字体、12/18 px 内沿、8 px 区块间隔、36 px 操作高度、240 px 下拉列表高度与箭头补偿。整体仍贴背包左侧、与背包等宽。

木工没有冶炼业务，底栏为开始加工/领取成品、废弃返还一半两项；不添加无效冶炼按钮。木工计时、清除率、损伤和评分使用真实木工字段，保留调整/切割操控。取消独立的项目大卡、进入加工大卡及说明折叠按钮。

## 数据与状态

复用 UColdSteelGunRecipeOptionWidget 提供具有 SObjectWidget 生命周期的 UMG 下拉行，程序同步选项忽略 Direct 回调，付费工件/准备期间锁定选择。成品预览复用 UColdSteelForgeBoard 的渐变背景、边线及等比图像；读取现有装备目录图，参数统一来自 BuildColdSteelItemTooltip 的 Summary/ValueScope。目录图在初始化缓存，数据变动只更新行和图片，不在每帧导入或重建。

未开始显示持有/需要与不足色，已投入读取 Job.PaidMaterials，结果读取 Job.Item/结果快照和 GetDiscardRefund。开始仍调用原 ConfirmProject，完成自动返回同一面板，领取、返料继续原有原子事务及联机处理。关闭保留未处理工件。预览不修改装备、属性或保存结构。

## 生命周期与范围

新增 UColdSteelWoodworkingManagementWidget，由现有木工宿主 UPROPERTY 持有，管理区域通过 TakeWidget 嵌入，切割画布保持原实现。模型事件注册/解绑沿 UMG 生命周期，下拉行使用弱缓存；管理状态让键盘导航传给下拉框，Escape 优先关闭展开菜单。源文件、备份及构建记录放 Saved/WoodworkingForgePanelParity20261013。

按用户要求进行截图与源码对照；必要构建后台执行，保留并行修改，不打开 UE、不运行游戏或自动测试。编译与实际画面验收分别报告。

## 本版源码对照结果

| 铁匠截图与实现 | 木工对应实现 |
| --- | --- |
| 上方配方序号、名称、下拉框 | 同顺序 UComboBoxString，两个完整装备选项；移除 ProjectCard 和图样大卡 |
| 下拉展开行、中心文字与箭头 | 复用 UColdSteelGunRecipeOptionWidget 和同款 ComboButton/TableRow 样式；支持鼠标及键盘 |
| 同卡材料表 | 复用同款 Grid、数字分列和语义色；已投入显示实际支付快照 |
| 第二块状态、数值、细进度线 | 同结构，显示木工时限/清除/损伤；结果显示真实评分、清除、损伤、返料 |
| 渐变成品预览与等宽参数区 | 直接复用 UColdSteelForgeBoard，显示现有装备目录图；右栏读取统一 Tooltip Summary |
| 常展开操作说明 | 同款卡片与字号，替换为木工真实操控和结算规则 |
| 固定页脚 | 同款背景、提示、36 px 等宽按钮；开始/领取与废弃返还一半 |
| 完成后恢复管理面板 | 继续调用已接入的木工返回/领取/返料流程，以同一 UMG 树刷新状态 |

首次构建报告管理面板局部变量遮蔽，已更名；另遇 PoisonMaggotSpawner.cpp 与 WitchProjectile.cpp 的 GetPawn 返回值不能用 const auto* 推导，分别只改为显式 const APawn*，不改变行为。修正前文件已备份。最终构建状态以 Saved 下对应结果为准。

后续队列构建暴露 ColdSteelPreviewScene.cpp 缺少 GetRendererModule 声明；补入 EngineModule.h，不修改预览场景逻辑。另一个独立 DragonBreathAuthor 工程的 commandlet 未加载 FPSGAME 模块，本次等待脚本仅等待主工程 commandlet 及引擎共享构建锁，不中断独立资产制作。

本版 Editor 构建随后报告 FacilityHallEncounter 生成构造代码析构 TUniquePtr<FFacilityMonsterGpuWarmup> 时类型不完整；仅在头文件包含既有 FacilityMonsterGpuWarmup.h，保留原 GENERATED_BODY 行号与大厅实现。

链接又暴露 GrantDoorKey / HasDoorKey 的旧对象重复定义。源码各只有一份实现；dumpbin 显示旧 BallisticPresentationAudit 对象仍定义这两个函数，且写出时间紧随角色头文件修改时间。计划归档的两份对象在操作前已不存在，本轮未移动它们。最终采用只刷新 FPSGAMECharacter.h 时间戳、不改变文件内容的方式，使依赖在最新声明下重新编译，避免继续混用中途修改头文件时产生的对象。

## 最终交付

FPSGAMEEditor 与 FPSGAME Win64 Development 均完成编译及链接，最终为 Succeeded、退出码 0。日志：Saved/WoodworkingForgePanelParity20261013/Editor-build-header-refresh.log 与 Game-build-header-refresh.log；构建时间与二进制路径见同目录 delivery.json。

已按用户截图和铁匠源码逐项对照管理面板结构与控件。没有启动 UE、运行游戏或自动测试；尚无修改后的游戏内截图或交互验收，不把构建成功等同于视觉验收。
