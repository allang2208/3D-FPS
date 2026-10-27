# 篝火补充发布（2026-10-27）

本次补齐此前焚化炉提交遗漏的篝火源码与配套资料。开发实施记录见 [篝火升级](../../Building/campfire-upgrade-20261026.md)，原始审计见 [篝火审计](../../Building/campfire-audit-20261026.md)。本次是仓库收尾，不重新改造本机玩法，不启动 UE，不进行游戏或联机测试。

## 已发布范围

- 篝火 Actor、复制炉况、烹饪结算、食材托管与事务、独立面板、烤架食品表现；食品目录、腐败模型、食品时钟及公共保鲜显示工具。
- 共享源码中的明确增量：物品／档案食品字段与事务版本、持久写入、食品消费、F6 按钮及权限、冶炼面板切换、进食道具、VBX v13 食材托管与 v14 免材料来源。序列化保留 v12 存储前缀，不带入屋顶制作行为。
- 七类菜谱及统一 presentation，按键合入 14 个生熟食品条目和 spoiled_food，四个复用进食动作档，以及野味 Cook 目录。其他物品和武器配置保持公共基线。
- Tools/CampfireUpgrade 的四个制作／导入／安装／目录脚本；三类野味的尺寸、颜色、材质和图标生成参数在 prepare_catalog.py 的 ROWS 中。
- 两个定向补丁、十四段共享宿主精确源码片段及必要的逐行接入点，用于保留第三人称、拾取、食品时钟和联机版本合并接入，避免整份覆盖混有其他功能的共享文件。
- 可复用经验沉淀到 ue5-save-load-replication 的 campfire-food-transactions.md，个人技能维护源与仓库镜像同步。

[source-scope.json](source-scope.json) 是直接发布的路径及配置键清单；[integration-manifest.json](integration-manifest.json) 记录定向补丁及前后散列；[integration/source-map.json](integration/source-map.json) 记录精确片段对应的本机源码位置和散列。

## 共享宿主的恢复边界

公共主线本来就是分批发布的源码切片，早于当前完整本机工程。例如发布前的 PlayerState 头文件已经采用 bool ApplyGuestProfile，而公共 cpp 仍是旧 void 实现。本次没有把其他任务的整份网络、天气、背包和武器改动夹带进提交，也没有重新编写一套旧宿主兼容实现。

因此，这份提交提供篝火专属源码、可以归属的共享增量和已在本机接入的精确集成资料；**不代表单独克隆公共仓库即可编译运行完整篝火游戏**。恢复完整工程时必须使用对应版本的共享宿主：

1. PlayerState 的持久 NetworkProfileId 绑定、已确认库存基线、外观上传确认、冻结上传、权威库存版本合并和回执解锁要一起恢复。头文件字段、RPC 签名及两端实现必须一致。
2. 食品时钟依赖当前天气系统的 AdvanceNaturalClock；integration 中保存精确方法、调用点及字段。只加入 FoodSpoilageClock 而缺少自然日推进会使腐败时间停止。
3. 普通库存回执和共享容器也承载食品时钟／实例年龄；沿用当前完整的 ColdSteelInventoryRequests、ColdSteelNetworkInventory、ColdSteelSharedContainers 与 ColdSteelSharedInventorySubsystem 食品支持。不能用旧容器整型计数重建食品实例或重置保鲜时间。
4. pickup 与第三人称动画两个补丁来自升级前的真实快照，不能盲套任意公共 HEAD。归档基线在 trash/campfire-retired-20261027/Before，对应补丁规范化为 UTF-8 无 BOM、CRLF 转 LF。共享网络片段是人工集成资料，不是自动执行的补丁或独立翻译单元。

本机完整工程维持已有接入。公开补充只改变 Git 中的整理版本，没有用索引裁剪版本覆盖真实工作文件，也没有把其他任务的 68 个暂存路径纳入本次提交。

## 模型和内容恢复

六款新野味使用本机授权食品源网格 SourceAssets/Sausage20261014/RoastedSausage_Editable.blend；来源为项目已有 Medieval Banquet 食品资产。商用使用许可不等于原模型／衍生模型可公开再分发。本次公开原创制作脚本和参数，不上传 blend、FBX、贴图、图标或 UE 包。

本机已保存 30 个 UE 包和 6 张生产图标，路径与历史 SHA-256 见 [local-assets-manifest.json](local-assets-manifest.json)。正式目录是 /Game/Items/Consumables/WildGame20261026，已有四类烤肉、生肉、spoiled_food、V7 手臂和动作源仍需按原内容恢复链取得。

需要重建资产时，先恢复合法源 blend，再运行 prepare_catalog.py 生成 foods.json 与独立 AssetHost；在 Blender 后台运行 author_models.py 完成模型、PBR 与生产图标；使用项目既有 Local\CodexUeMcp-Port-8000 批次互斥执行 UnrealEditor-Cmd.exe 的 Python commandlet 导入 author_ue.py；保存成功后运行 install_assets.py，最后 prepare_catalog.py --publish。只写好脚本不算已导入，不自动覆盖散列不同的正式资产。操作按当前用户授权执行，不为发布检查重新运行导入。

## 归档与检查

41 个旧快照和已完成导入宿主的缓存／日志已移动至 trash/campfire-retired-20261027。逐文件原路径、目标、大小、SHA-256、原因和保留替代物见 [archive-manifest.json](archive-manifest.json)，移动后已读回确认。采用中的 blend、FBX、贴图、图标、UE 包、制作参数和最终构建／导入回执继续保留。

本次只检查发布范围、定向补丁、配置键、文本大小、敏感信息、许可边界、归档散列与 Git 推送。此前完整本机 Game／Editor 构建记录在实施文档中；本轮未重新构建，也未进行实际主客机、断线重连或画面验收。使用独立索引准备提交，提交时保留既有暂存和真实工作文件；普通推送 HEAD:main 后回读远端分支及旧 Godot 归档标签。
