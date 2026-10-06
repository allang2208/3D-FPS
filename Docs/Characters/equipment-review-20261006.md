# 裤装、鞋靴与本机身体开发复查

用户于 2026-10-06 确认肩口尖刺已解决，并明确要求回头检查开发内容、修复遗漏。本次保留已接受的几何、材质、相机位置和持枪动作，采用代码审查、隔离的发布脚本回归及只读资产 commandlet。没有读取活动游戏组件或启动游戏。

## 已修复

### 换装异步加载期间过早移除旧外观

`FPSModularOutfitComponent.cpp::DiscoverSources` 原先按新的装备组合生成 `CurrentKeys`，随后立即释放 key 不匹配的旧 Presentation；实际的新网格却要到 `UpdatePresentation` 异步加载完成后才装配。因此新裤子、鞋靴或上衣尚未就绪时，会暴露世界源身体，或令全隐藏驱动的本机身体短暂为空。资源已在内存中时通常看不到这个空档。

现在按本轮实际参与装配的组件集合清理失效外观。同一有效组件的旧完整外观在异步等待期间保留，新网格和材质全部就绪后，仍由原 `UpdatePresentation` 一次性替换。已销毁组件、源网格改变、退出换装路线的组件继续恢复原材质并释放派生部件。过时加载的取消、八个在途请求上限、远端装备数据来源及可见性跟随不变，没有加入同步加载或新 Tick。

### 重新发布本机衣物覆盖镜头调参

`publish_shared_body.py` 原来每次把完整 `first_person_body` 替换成作者脚本中的常量，后续调参或新增字段会在重建衣物时丢失。现在以默认值补全缺失字段，再继承已有设置，只明确保持当前 `shared_world_pose` 模式。正式相机配置没有被本轮运行改写。

隔离回归把临时项目的前移值设为 73 cm，并增加一个扩展字段，执行真实发布脚本后，两者均保留；全部装备配方也与正式输入相同。脚本运行只写临时项目，未对正式装备表执行重发布。

## 检查范围和结果

- 12 件目标物品：牛仔裤、工装裤、锁子甲裤、皮革裤、七分裤、休闲鞋、普通靴、铠甲靴、皮革靴，以及三件本机上衣。
- 124 个配置中引用的资产文件均存在；目标 PNG 图标存在，装备槽语义一致：裤子 15、鞋靴 13、上衣 7。
- 26 个已保存的身体／上衣／裤装／鞋靴和鞋筒配套网格成功加载；使用中的骨骼名字均能由身体姿态源提供，原生权重有效且归一化，身体遮挡材质编号有效。
- 三件连续肩口上衣的隐藏段名称和编号一致，每件三个 LOD 都含可见躯干和隐藏袖臂；各 LOD 保留相同分区面数。
- 裤子显示格 13、鞋靴显示格 16，点击命中、拖拽预览和键盘导航共用 `ColdSteelEquipmentLayout`，持久化槽编号未变。
- 网格目录包含在现有 Cook 范围；`FPSGAME.Build.cs` 将整个 `Content/ColdSteelData` 作为 UFS 依赖，包含配置和 PNG 图标。本轮没有执行完整打包。
- 人称切换、死亡／翻越隐藏、共用世界骨骼、裤脚按鞋型选择、材质遮挡恢复路径已按源码检查；没有把代码审查表述为实机状态测试。

## 交付文件与记录

- 修复源码：`Source/FPSGAME/Characters/FPSModularOutfitComponent.cpp`。
- 发布脚本：`Tools/FirstPersonLegs/publish_shared_body.py`。
- 可重复离线检查：`review_equipment_offline.py`、`review_saved_equipment_assets.py/.ps1`，位于 `Tools/FirstPersonLegs`。
- 本轮修改前副本及检查结果：`SourceAssets/EquipmentReview20261006/Before`、`offline-review.json`、`saved-asset-review.json`。
- 编译入口：`Tools/FirstPersonLegs/build_equipment_review.ps1`；`-CompileOnly` 仅编译对象文件，不更新编辑器 DLL。

第一次编译因 `UBA FATAL ERROR 9887: Failed to create shared memory` 中止，随后改用最多一个编译动作的资源设置。第二次运行完成 60 个编译动作，其中第 15 个 `FPSModularOutfitComponent.cpp [NoUba]` 成功产生对象文件，本轮 C++ 修改未报告编译错误；但完整目标返回 `Failed (OtherCompilationError)`，耗时 439.60 秒。

错误位于本次衣物任务范围外的 M08 怪物实现：`LurkerM08AirCannon.cpp`、`LurkerM08Monster.cpp`、`LurkerM08Traversal.cpp`，涉及 `Super`、`Busy`、`HasAttackSupport`、`FinishPounceMovement`、委托成员等继承／声明不匹配。没有修改这些其他模块，也没有跨对话询问或协调。编译记录为 `build-objects-console.txt`、`build-objects.log` 和 `build-result.json`。

原编辑器进程在编译期间已自行退出，本轮没有主动关闭、重启或打开 UE。第一次交付时全目标编译失败，没有继续链接，当时换装 C++ 修复尚未进入正式 DLL；发布脚本修复和离线检查工具已经落盘。原失败回执保留在 `build-result.json`。

## 后续构建完成

用户要求“继续尝试”后，从当前构建产物确认阻塞已解除：正式 `UnrealEditor-FPSGAME.dll` 于 2026-10-06 12:57:20（北京时间）更新；`FPSModularOutfitComponent.cpp.obj` 生成于 12:47:28，晚于本轮源码的 12:40:12，并明确列在正式 DLL 链接响应文件中。

12:57:25 开始的 `FPSGAMEEditor Win64 Development` 常规构建（未使用 `-NoLink`）返回 `Target is up to date`、`Result: Succeeded`，耗时 2.67 秒。此成功构建是后续已完成的工程构建，本次继续操作确认并保留其证据，没有再次启动重复构建。

**换装 C++ 修复已进入正式 DLL，发布脚本修复也已落盘。** 后续完成回执为 `build-completion.json`；对应构建日志副本为 `completed-build-20261006.log`，链接输入副本为 `completed-link-inputs.rsp`，均在 `SourceAssets/EquipmentReview20261006`，同时记录本轮源码、对象和 DLL 的时间与 SHA-256。

没有启动或重启 UE、读取活动游戏现场、运行实机换装／动作回归；已有进程保持原状。不能把编译成功或用户此前对肩口的认可当成新换装逻辑的实机验收。

2026-10-06 整理：本文历史备份／旧版本路径按 [归档清单](lower-equipment-archive-20261006.json) 映射到 trash。当前制作入口与恢复顺序见 [整理发布](lower-equipment-publication-20261006.md)。
