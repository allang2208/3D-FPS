# 裤鞋与第一人称身体整理发布（2026-10-06）

本次发布休闲鞋单只斜视图标、裤鞋装备卡位置、MetaHuman Boots、锁子甲裤 V2、铠甲靴、棕色皮革裤靴、七分裤及裆缝修复，以及保留原生手部的共用身体显示。用户已反馈肩口修复后“没问题了”；随后要求回查，修复了异步换装提前释放旧外观和重新发布衣物覆盖相机参数的问题。

## 当前有效实现

- `FPSPlayerFirstPersonBody.cpp`：本机身体直接使用世界身体最终姿态。手、手套和袖子沿各武器原生绑定；身体胸腹、裤子和鞋跟随同一姿态源。相机参数保留站立 56 cm、蹲姿 62 cm、低头附加 12 cm、躯干余量 40 cm。
- `FPSModularOutfitComponent`：本机上衣独立引用，按鞋型选裤脚，所有新网格／材质加载完成后再替换旧外观；仍在加载时保留最后完整服装。
- 当前本机上衣使用 `OwnerShoulderSeam20261006` 三件网格及其 LOD 设置。在上臂权重等值线内拆分混合三角面，替代整面裁切产生的尖刺。
- `ColdSteelEquipmentLayout.h`：逻辑槽裤子 15、鞋靴 13 保持存档兼容；显示为第 5 行中列裤子、第 6 行中列鞋。绘制、命中、拖放和键盘导航共用映射。
- 七分裤普通版与高筒靴版均为 `CrotchSeamFix20261005` 连续裆缝，UV 接缝与骨权重处理相互独立。

配置只纳入本任务的六个新增物品、对应服装配方和第一人称参数。共享角色头文件／实现仅提交本任务部分；其他武器、怪物、第三人称动作、UI 和战斗的并行改动不纳入。

## 恢复顺序与资源边界

公开仓库提供 C++、配置引用、原创制作脚本、归档元数据与 SKILL。UE 包、Fab／Jason 原始及派生密集网格／骨架／权重、贴图、图标 PNG、Blend 母版、导入／构建日志留在本机。已被旧提交跟踪的 `SourceAssets/LowerBodyEquipment20261003` 数据从当前发布树取消跟踪，继续留作本地生产输入；不改写已有 Git 历史。

原始服装来源：用户导入的 [MetaHuman Casual Sneakers](https://www.fab.com/listings/7e58d5c5-5666-4ab2-9c4e-011eeaba3c07)、[MetaHuman Jeans](https://www.fab.com/listings/07dc895c-7402-411c-a74a-e1c47b33ac68)、[MetaHuman Cargo Pants](https://www.fab.com/listings/586d2fd4-9ae9-4d91-9e61-2a362008d052) 和本机 MetaHuman Boots 包。沿项目既有授权使用，不把免费获取视作允许公开原始资产。Boots 原包标识与散列见本机 `SourceAssets/BootsEquipment20261004/provenance.json`。

恢复完整项目需要本机授权输入，不能仅 clone 源码就获得完整资产：

1. 恢复已有 Jason 身体、原生武器手部、三件上衣与锁甲材质；按 `Tools/LowerBodyEquipment` 和 `Tools/BootsEquipment` 恢复供体、适配身体／裤装／鞋靴。Boots 使用独立 `BakeOutfit` commandlet 导出真实衣物，不把包内体型参考当作靴子。
2. 按 `Tools/ChainmailPants` 的基础裤身 → `refine_armor.py` → V2 保存顺序恢复锁甲裤。基础作者数据仍是 V2 的生产输入，不能一并归档。原静态展示／掉落路径为旧物品实例保留，并已同步为 V2。
3. 按 `Tools/ArmoredBoots` 恢复高筒遮挡基础身体、铠甲靴和三套裤脚；再按 `Tools/BrownLeatherSet` 恢复皮革裤靴。最新身体为 `ArmoredBoots20261004/SK_Jason_Base`，原世界 profile 键保持兼容。
4. 按 `Tools/SmokeGreyCapri` 恢复七分裤，使用当前连续裆缝作者入口及 `save_crotch_repair.py`。活动配方统一 `Jason`，本机和世界显示共用；已退役的 `JasonFirstPersonLegs` 不再注册。
5. 运行 `save_continuous_owner_shoulders.py/.ps1` 保存三件当前本机上衣，再使用 `publish_continuous_owner_shoulders.py`／`publish_shared_body.py` 更新引用。后者必须有完整 `saved_shoulders.json`，缺少时停止，不回退废弃整面裁切网格；保留已有相机调参。
6. 图标用已保存的独立展示网格及 `ColdSteelWeaponIconCatalog` 重制。`Tools/LowerBodyEquipment/save_icon_meshes.py` 保留休闲鞋单只斜视规则。发布脚本多数为首次插入入口；已有物品应定向更新，勿把重跑插入器当成迁移存档。

`SourceAssets/OwnerBodyShared20261005/saved_shirts.json` 保留为发布器核对骨架／源网格的契约元数据，网格输出已经退役。其他仍使用的制作源、最终回执和失败诊断证据保留本机；不依据文件日期判断废案。

## 归档

131 个文件、392,929,517 字节移入 `trash/lower-equipment-retired-20261006/`。包括独立腿模 V1／V2／V3、旧动画类和入口、旧整面肩口网格／制作器、被替换的镜头版本、一次性现场读取器、裆缝修复前源与旧快照。21 个退役 UE 包经离线 AssetRegistry 查询无外部包引用，运行配置中的旧 profile 与别名也已移除。

每个文件的原路径、归档路径、字节数、SHA-256、原因与替代物见 [逐文件清单](lower-equipment-archive-20261006.json)，本机 trash 内也保存同一清单；移动后全部散列一致。`trash` 不推送。历史文档中的旧 `Before`／`PreviousStaticPackages` 地址按清单映射恢复，不从归档恢复旧模型覆盖当前版本。

## 已完成与未执行

此前用户要求的离线回查覆盖 12 件装备、124 个资源引用和 26 个保存网格；三件本机上衣的三档 LOD 有效区段已读取。换装 C++ 修复已进入本机 2026-10-06 12:57:20 的正式 DLL，证据位于 `SourceAssets/EquipmentReview20261006`；这是既有构建记录，不是此次公开快照的新构建验收。

本次整理执行发布范围／敏感内容／许可边界检查、退役依赖检查、移动散列核对及相关配置／发布器检查。去掉退役引用后，12 件装备的 121 个当前资源引用均在本机，真实发布器在临时目录中重发仍保留调参和活动配方；源码检查限发布所需语法及引用范围。未启动、关闭或重启已有 UE 编辑器，未运行游戏、动作、换装或画面验收；实际游戏表现仍由用户测试。

可复用方法已同步个人技能与仓库镜像的 [共用身体与裤鞋装备](../../skills/ue5-fps-arms-animation/references/shared-owner-body-and-lower-equipment.md)，并从手臂 SKILL 和衣物工作流入口链接。
