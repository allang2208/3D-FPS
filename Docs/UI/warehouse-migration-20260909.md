# Godot 仓库与宝箱交互迁移记录

目标项目：`D:/FPS3D/FPSGAME`，UE 5.8.2，单机玩家持久化档案。
参考项目：`E:/3d/3-dfps` 的 `ui/warehouse.gd`、仓库面板、背包空间规则、冷钢 UI 标准及 `warehouse_chest_v6.glb`。

## 使用

在 `DayNight_Lighting` 运行游戏，出生点附近自动放置宝箱（检测地面及阻挡；场景已有宝箱时不重复创建）。走近至 2.4 米内显示 `E · 武器仓库`，按 E 同时打开仓库与装备背包页。

- 仓库：5 页 × 20 格，固定两列；每个物品实例占一格。
- 背包仍采用 18 × 4 空间布局；M4 等双手步枪占 5 × 2。
- 拖放、右键、双击或 Enter 存取物品；装备可直接存仓。
- 仓库之间拖放交换位置；跨页通过背包中转或分页后的目标格放置。
- 底部提供全部存入、取出同类、稀有度/价值/类别整理和分页。
- 鼠标悬停查看共享物品详情，单击固定详情，F1 将焦点交给详情。
- Esc 逐层关闭详情/取消拖放、仓库、背包；仅关闭仓库时背包保持打开。
- 离开交互距离会关闭仓库；所有面板关闭后恢复游戏鼠标与视角输入。

## 功能对应

| 原功能 | UE 实现与数据约束 |
| --- | --- |
| 仓库分页、容量、位置 | Place=4，独立仓库格位；容量与位置进入档案验证 |
| 存放与堆叠 | 兼容实例合并，目标满栈后溢出至其他兼容栈/空格；放不下则整个操作回滚 |
| 指定位置取出 | 复用背包矩形占位验证；边缘非法位置不会自动挪到其他位置 |
| 异物交换 | 背包目标物回原仓库格；装备存仓被替换物进入背包，不自动穿戴 |
| 装备直接存入 | 空仓库格无需背包空间；若要接回替换物且背包已满则回滚 |
| 批量与排序 | 金币先存，倒序处理；按名称取同类；保留稀有度/价值/类别排序顺序 |
| 数据保持 | 保留实例 ID、原始物品 JSON、数量、改造/强化/附魔字段和弹匣数据 |
| 保存失败与旧操作 | 保存后发布；失败不更改两端容器；版本过期的提案与拖动来源拒绝提交 |
| 材料支持 | 按定义统计背包和仓库；背包优先扣减；仓库单独提供谓词统计和部分扣减接口 |
| 外部奖励/容量 | AddWarehouseItem、WarehouseRemainingCapacity、DepositWarehouseAmount；返回实际接收数量 |
| 全部取出 | RetrieveAllFromWarehouse，按现有顺序取出并在首个阻塞处停止 |
| 详情与徽章 | 使用当前共享详情组件；稀有度、强化、改造、附魔徽章；完整原始数据用于详情 |
| 冷钢面板 | 仓库 380px，紧贴右侧 45% 背包；窄屏宽度约束；固定页脚、内容滚动、统一字体和色值 |
| 开关动画 | 300ms 面板过渡；源宝箱 Open 0.9s / Close 0.7s，非循环；连续开关以最后请求为准 |

用户在另一个任务中于本次实施期间明确要求“把迁移过来的6把枪械全部作为废案，删除”。最终接入保留该决定：不恢复六把武器、不重新发放旧初始军械；仓库测试改用现有 `ue_m4a1` 与隔离测试物品。早期六把武器的截图和测试日志仅是历史阶段证据。仓库正式初始内容遵循当前玩家存档，截图中的 M4 仓库实例属于隔离验收档案。

材料接口已覆盖源仓库的数据服务合同；这不等于独立的强化、附魔 NPC 面板已经迁移。

## 模型来源与转换

原文件：`E:/3d/3-dfps/scenes/warehouse_chest_preview/warehouse_chest_v6.glb`。
源 SHA-256：`5e4429cfb88d7c20cab7f3cabee393ade312560b8cfba4bc9125090ebe1b2403`。

使用本地转换脚本保留 42,893 顶点、5 个刚体节点及原动画时间/旋转曲线；为 UE 骨骼导入建立一顶点一骨骼的刚体权重和反绑定矩阵。原 GLB 未改写。转换结果为 `SourceAssets/WarehouseMigration20260909/warehouse_chest_rigid.glb`，可重导入。

8 个材质采用源 GLB 的 PBR 材质与纹理，并生成仅供本宝箱使用的骨骼材质父级及实例副本。运行时从 `Content/ColdSteelData/warehouse_assets.json` 加载。没有改写引擎共享 glTF 材质。Godot 的运行时自定义宝石/石材 shader 未逐行移植，UE 使用 PBR 表现；实际开关箱渲染见下方。

`Config/DefaultGame.ini` 已加入宝箱目录 AlwaysCook。来源为现有项目资产，原授权沿用；本次未引入新的第三方下载资产。

## 文件与恢复边界

仓库专属实现：`Source/FPSGAME/UI/ColdSteelWarehouseRules.*`、`ColdSteelWarehouseModel.cpp`、`ColdSteelWarehouseWidget.*`、`ColdSteelWarehouseHUD.cpp`、`ColdSteelWarehouseChest.*`、`ColdSteelWarehouseAudit.cpp`。

共享接入点包括库存类型/校验、状态模型/档案、背包原生拖动、HUD、角色页输入及 PlayerController。同期其他任务在修改这些文件，保留其最新改动。初始备份位于 `trash/warehouse-migration-20260909`，不可整目录回写覆盖同期任务。

## 验收

最终编译与运行记录见 `SourceAssets/WarehouseMigration20260909/build-final.log`、`Saved/WarehouseMigration/`。
运行脚本：`SourceAssets/WarehouseMigration20260909/run_validation.ps1`；使用独立 `ColdSteelProfile`，不会操作正式玩家存档。

| 验收 | 结果 | 记录 |
| --- | --- | --- |
| Editor Development 最终编译 | 成功，含指定空格存放修正 | build-final.log，模块后缀 2026090937 |
| 1280×720 / 1920×1080 / 960×540 | 每种 56 项，0 失败，进程退出 0 | current_m4_b-*-write.log |
| 最后指定空仓库格规则回归，1280×720 | 57 项，0 失败，进程退出 0 | final_d-1280-write.log |
| 新进程读档 | 完整实例 ID / JSON / 数量 / 格位 / 弹匣签名一致；1 项，0 失败 | final_d-1280-reload.log |
| 原背包/装备功能回归 | 49 项，0 失败，进程退出 0 | inventory_regression-1280-write.log |
| 宝箱实景 | 源开关时长正确；关闭/打开 PBR 渲染均已查看 | chest_b-1280-chest.log，chest-closed.png，chest-open.png |

57 项检查包含 3000 次随机转移后的数量守恒与格位无重叠检查、保存失败注入、目标位置验证、满仓/满包整单回滚、部分存入/材料扣减、实际 UMG 拖放处理、鼠标焦点、离开距离关闭、原开关动画及快速反复开关。

![最终仓库面板，隔离 M4 测试档案](../../Saved/WarehouseMigration/ColdSteel_WarehouseAudit_final_d_1280-open.png)

材质 commandlet 的 8 个保存断言通过；其进程仍报告项目既有 GameFeatureData 配置与 8000 端口占用错误，不能仅把 commandlet 的 PASS 行当作整体进程成功。实际游戏渲染已验证材质副本生效。加载骨骼时原导入材质会先报缺少骨骼 usage 标记，随后由运行时副本替换，最终截图不存在灰色默认材质。

本次验收使用 Editor 的 `-game` 真实渲染模式；未执行 Shipping 打包或多人网络验收。

![UE 宝箱关闭](../../Saved/WarehouseMigration/chest-closed.png)
![UE 宝箱打开](../../Saved/WarehouseMigration/chest-open.png)
