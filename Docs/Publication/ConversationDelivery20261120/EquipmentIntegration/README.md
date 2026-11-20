# 战术套装与进食的共享宿主

基线为 `c8d8c3b8502274e38b297462753c213a53aabbec`。源码树内的改动使用该基线合入。该目录的四份补丁供具备下述本地宿主的分支恢复。补丁只包含所列功能的差异。SHA-256 按 UTF-8、LF 计算。恢复前核对目标文件的前像，依次使用 `git apply --check --unidiff-zero <补丁>`、`git apply --unidiff-zero <补丁>`。四份补丁独立。

## 01-modern-set-tooltip

目标为 `Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp`。现代战术五件套的悬浮卡名称与四行加成。前置是含 FSetBonusDef、SetBonusList 与 SetDisplayName 的完整装备卡宿主。基线装备卡可直接显示目录 setBonusDesc 和枪械数值，完整套装表为此补丁的交付范围。

- 前像 `dee60ad447ba1e855bcf8392304d0887141a9906fc0708bd92ba8ff3df1171a9`
- 后像 `d834c2c6cdc3435303d485b9ec287d469df7512d399f9bea431bc23fa0303219`

## 02-nonpistol-offhand-stow

目标为 `Source/FPSGAME/Characters/FPSBodyConsumePose.inl`。非手枪副手进入收起和抬回阶段的第三人称 IK。前置为本地提供 PistolArmActive 的分手手枪动画宿主，并已合入本提交的食物咬点修正。通用进食时钟和权重已合入源码树。

- 前像 `52fb91852f020d8d4e8e4b46c2a230c826005a1bf4f256ef337f2155db78fb27`
- 后像 `8dddbac0259313febd1de28846b553f71500374bc7b6b40815e5760bc0f5cfd5`

## 03-consumable-receipt-and-handoff

目标为 `Source/FPSGAME/Items/ConsumableReceiptWireAudit.cpp`。在已发布的 2026-11-05 食用回执网络探针上加入面包与双持收起、隐藏、复位三阶段观察。前像是 Docs/Publication/PlayerInteraction20261105/Integration/Items__ConsumableReceiptWireAudit.cpp.patch 解出的源文件。运行需完整 ShotgunWireAudit 控制器、游戏模式和其既有食用 RPC 入口；使用 -MealReceiptWire -MealHandoffWire。

- 前像 `5b433732f324bddddda9a04cd65a2eb060c7f8e0e8060f3cec8cc4dd215e6e7e`
- 后像 `98a29d5b7a702c342620b9c1cde14240fd18ee9c3e464914fc32929c3f5b9bfb`

## 04-staff-offhand-consumable-arms

目标为 `Source/FPSGAME/FPSGAMEConsumableUse.cpp`。完整本机法杖与副手成对武器组件接入后，进食复用该组件的原生手臂，并在副手攻击时防止抢夺动作。公开源码保留已经存在的弯刀、双持、火器与工具入口。

- 前像 `b84bc59ac8495dacdf930a6087f9df98b4f63df5b0cc6559965aa395e45b0168`
- 后像 `1945bc8791d3ef6f2b562509ec92be0abca6e0c81e55c4729e3599f5fb77b1d3`

## 源码树接入与边界

- 原生 M870 的手套形状、权重与裸手覆盖来自装备映射与对应已保存的蒙皮资产。服装组件按实际内层网格加载裸腕材质，空手套槽恢复 WristUnderlapSkin。基线已支持裸手、分离手套和裤靴、上衣裤装的配对字段。
- 五件套的定义调参与存量装备共用数据迁移，护甲和开镜读取角色套装，后坐与稳定性合并至主武器、双持的左右手及装备界面。公开基线的双持入口为 PistolDualWieldComponent.cpp，本地拆分到 PistolDualEquipment.cpp。
- 食物使用实际咬点驱动第一人称轨迹；道具握持期间依附当前手腕，吞咽、中止和结束清理。第三人称对短面包供体的烤食轨迹进行偏移，双手大羊排保留握距并校准两只手。服务端查看对应玩家的副手，接收端按同一个起点推进动作。
- 进食姿态诊断使用编辑器命令 `fps.body.DiagnoseFood <绝对路径.json> [jason|kaitlin] [contacts]`。装备主客端检查使用既有 MageOutfitWireAudit 游戏模式并追加 `-MageOutfitWireAudit -ModernTacticalOutfitWire`；命令行审计可从 `FPSConsumableAudit` 进入。资产依赖在本机工程，纯源码包无法替代角色和服装渲染。发布时仅做补丁重放与差异归属检查。
