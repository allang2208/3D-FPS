# 地面掉落与准星交互（2026-09-10）

## 行为

- M4A1、AKM 掉落使用当前第一人称枪械资源中的枪体，排除手臂、手套和袖子；复制当前实例的可见枪匠配件。M4 验证实例包含全息镜、消音器和弹鼓。
- 枪体与配件冻结为一个物理物件：以可见模型计算盒形碰撞，开启重力、连续碰撞检测、摩擦和阻尼。玩家胶囊不推动掉落物。其他物品暂用通用小型物理方块。
- 丢弃先寻找附近有效地面，沿前方扫掠为枪体留出墙边空间，再从离地位置释放。找不到附近地面时保留原物品。
- E 通过相机中心的 Visibility 单射线选择第一个阻挡对象；拾取最远 250 cm，仓库保留 240 cm 的接近约束。没有对准、被墙挡住、超出距离或界面占用鼠标时不触发。
- 地面物品与仓库提示只在对准时出现。打开仓库后，界面继续按距离保持，避免鼠标交给 UI 后仓库立即关闭。
- 拾取先验证瞄准的活体对象和库存事务，保存成功后才销毁掉落物。背包满、保存失败均保留原实例；配件、强化数据、数量和弹药沿用完整实例数据。
- 枪械预览角色在 GamePreview/EditorPreview 世界跳过玩法 BeginPlay，防止读取地面存档时预览角色错误连接玩家档案。
- 自动保存及手动保存采集实际物理位置和朝向；新增 `WorldRotation`，旧存档默认零朝向。恢复后以保存的变换生成并重新启用物理。

## 仓库回归修复

`UComboBoxString` 的自定义选项仅保存返回控件的 Slate 引用。原排序选项直接返回未加入树的 `UTextBlock`；预览世界释放会请求垃圾回收，后续仓库文字布局可能访问失效对象。选项现由 `UUserWidget` 包装，借助 `SObjectWidget` 保持 UObject 生命周期。世界交互回归在打开仓库前强制垃圾回收，覆盖此触发条件。

## 验证入口与边界

- `Tools/UI/run_world_interaction_acceptance.ps1`：独立审计存档与进程，真实模型、重力落地、准星 E、满包、失败保存、遮挡、距离及变换恢复；截图位于 `Saved/WorldInteraction/`。
- `SourceAssets/WarehouseMigration20260909/run_validation.ps1`：仓库业务、原箱子动画、拖放、关闭与新进程存档恢复。
- 使用 UE 5.8.2 Editor Development 本机编译和 `-game` 运行；本轮不代表多人或打包验收。原生改动需要新启动的游戏进程加载。

## 本轮结果

- UE 5.8.2 Editor Development 编译通过（`Saved/WorldInteraction-final-build.log`）。
- 世界交互写入 **25 / 25**：`Saved/WorldInteraction/20260910234947-write.log`。
- 新进程恢复并重跑交互 **27 / 27**：`Saved/WorldInteraction/20260910234947-restore.log`。确认 BeginPlay 恢复两把枪模型，预览角色没有替换活动玩家。该进程加载本机并行构建模块 `UnrealEditor-FPSGAME-2026092992.dll`。
- 仓库写入与交互 **57 / 57**：`Saved/WarehouseMigration/aimed_final_20260910-1280-write.log`；另一个进程精确恢复 **1 / 1**：同目录 `aimed_final_20260910-1280-reload.log`。
- 检查真实截图 `Saved/WorldInteraction/landed-model.png`、`akm-landed.png` 和 `warehouse-focused.png`：两种枪械完整落地，仓库面板正常呈现。
- 早期回归发现的排序文字 Slate 崩溃已经修复；最终世界交互回归显式执行垃圾回收后打开仓库，全部通过。
