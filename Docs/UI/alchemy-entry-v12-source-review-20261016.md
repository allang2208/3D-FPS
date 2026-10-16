# 炼药进入页 V12 源码排查

范围：按用户要求逐项阅读进入页、配方/物品数据与事务调用链。只做后台源码/数据检查及必要编译，不运行 UE 界面、游戏、PIE、commandlet 测试或自动化测试。

## 配方切换与数据

读取 `alchemy-recipes.json` 和 `items.json` 的实际八条关联，图标文件均存在。读取得到的原始记录保存于 `SourceAssets/PotionWorkbenchDesign20261015/EntryV12/catalog-source-review.json`；这不是游戏界面测试结果。

| 配方 ID | 成品 ID | 使用效果 | 材料：基液 / 主料 / 催化剂 |
|---|---|---|---|
| brew_hp_basic | hp_potion | +30 生命、+15% 最大生命 | 1 / 1 赤脉 / 0 |
| brew_hp_medium | hp_potion_medium | +80 生命、+20% 最大生命 | 1 / 2 赤脉 / 0 |
| brew_hp_high | hp_potion_high | +150 生命、+25% 最大生命 | 2 / 2 赤脉 / 1 |
| brew_hp_special | hp_potion_special | +180 生命、+30% 最大生命 | 2 / 3 赤脉 / 2 |
| brew_mp_basic | mp_potion | +25 魔法、+15% 最大魔法 | 1 / 1 蓝髓 / 0 |
| brew_mp_medium | mp_potion_medium | +60 魔法、+20% 最大魔法 | 1 / 2 蓝髓 / 0 |
| brew_mp_high | mp_potion_high | +120 魔法、+25% 最大魔法 | 2 / 2 蓝髓 / 1 |
| brew_mp_special | mp_potion_special | +150 魔法、+30% 最大魔法 | 2 / 3 蓝髓 / 2 |

百分比是按使用者最大值恢复的比例，不是提升最大值。进入页继续从公共 `BuildColdSteelItemTooltip` 读取真实效果，不在 UI 另写一份数值。

| 路径 | 实际入口与源码结论 | 本轮处理 |
|---|---|---|
| 鼠标/键盘选择 | `Select → Selection → Refresh → RefreshEntry`，配方 ID 变化使缓存失效 | 选择时强制标记数据变更、清除旧本地提示，重新展示当前配方可开炉/缺料原因，避免旧“材料不足”留在新配方上 |
| 成品预览 | 当前配方 `Output` → `CreateItem` → `ue_icon` → 同一 `ForgeBoard::Configure`，Configure 使 Slate Paint 失效 | 八条映射及图标引用一致；有批次时始终读保存的 `Job.Product`，不替换成当前目录物品 |
| 效果参数 | `BuildColdSteelItemTooltip` 的使用效果进入 Summary；行复用后隐藏多余旧行 | 固定值与最大值百分比同源；生命/魔法配方切换不会保留旧行文字 |
| 材料数量 | `CountMaterial` 与 `Pay` 同样读取背包、夹层、主仓库；`OnChanged` 触发重建 | 无批次显示持有/需要；已有批次按 Escrow 汇总实际已扣数量；目录材料顺序之后保留旧批次额外材料 |
| 同名配方的批次快照 | 原 `Recipe()` 只比配方 ID，未比其缓存来自哪个 Job | 增加 `RestoredId == Job.Id`；快照读取失败清空旧 Accepted，避免误用前一批次配方 |
| 继续本炉 | `Resume → LoadJob → Acquire`，没有 Pay/扣料调用 | 新增共享只读 `CanResume`，校验保存/同步、工序记录、距离及占用；不因剩余背包材料不足而禁止恢复 |
| 资源准备期间 | 原来准备完成后临时按 HasJob 决定 Start 或 Resume | 保存点击时的配方和 Job ID；只执行原意图，批次变化则提示重选，不会把继续旧批次改为新炉扣料；读书期间不提交准备中的操作 |
| 领取 | `Claim` 先把全部成品插入临时库存，再与清空 Job 一次提交 | 保留原原子提交；背包不足不部分领取、不清批次；UI 点击先比对所显示的 Job ID/Revision |
| 作废确认 | 原先确认仅为 bool | 确认绑定 Job ID/Revision；批次更新即失效，旧确认不能直接作废新版批次 |
| 成品作废退半 | `DiscardRefund` 先按 Definition 合并 Escrow，再取 floor(total/2) | 保留原算法，不按碎堆分别取整；未完成批次仍仅退未开封材料 |
| 退料与容量不足 | `Discard` 将所有退款试插临时库存，再同次清空 Job | 放不下则整炉保留，没有部分退料；按钮同步期间禁用 |
| 快速连点 | 原领取/作废成功后，同位置主按钮立即变成备料开炉 | 批次清空后的 0.5 秒暂停新炉动作；收到异步回执后先刷新，拒绝按旧按钮状态操作新批次 |
| 联机重复请求 | `RequestInventoryAction → ServerInventoryAction → ExecuteStation` | 已有递增请求序号、当前 Pawn、库存 Revision 和非开炉操作 Job ID 校验；领取/退款与清空批次同一事务，后一请求失效 |
| 保存与网络忙碌 | `PersistState/WorldAction/AuthorityTransactionFinished` | 原写入/回滚语义保留；进入页补齐背包同步禁用和原因，未能发出的请求给出反馈 |

## 修改边界与交付

修改 `ColdSteelAlchemyWidget.h/.cpp` 与 `AlchemySystem.h/.cpp`，未改变配方、扣料数量、奖励、退半算法、库存通用事务或持久化结构。V11 布局、V10 操作动画及书本模型保持。

原文件快照、数据读取记录和 Game/Editor 构建日志位于 `SourceAssets/PotionWorkbenchDesign20261015/EntryV12`。实际编译状态由 `delivery.json` 记录。真实快速点击、延迟、背包容量不足和联机同步场景未运行测试，不能把源码检查或编译结果当作运行验收。

2026-10-16 后台构建结果：Game `Result: Succeeded`（328.57 秒），Editor `Result: Succeeded`（207.78 秒）。未启动 UE 编辑器、游戏、PIE、自动化测试或审计 commandlet。

本次必要构建另外遇到 `AlchemyManualNetAudit.h/.cpp` 的参数命名编译错误：`ServerHello(Role)` 遮蔽 `AActor::Role`，lambda 的 `Pawn` 遮蔽控制器成员，复制属性函数的 `Out` 不符合 `DOREPLIFETIME` 宏要求的变量名。仅把对应参数改为 `InRole`、`InputPawn`、`OutLifetimeProps`，未改变该审计的逻辑或执行它。两份原文件保存在 `Before/CompileUnblock`。
