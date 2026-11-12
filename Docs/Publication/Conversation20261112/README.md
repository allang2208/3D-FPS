# 2026-11-12 武器、动作与背包图标发布

## 当前交付

| 范围 | 保留结果 | 已有依据 |
| --- | --- | --- |
| M249 背包 | 背包格、装备拖动和详情按枪实例选用脚架备用图，动态预览按完整配件组合更新。混合改造等待预览期间，其他配件可能稍后显示。 | 两个独立进程，主客各有两把 M249。对照应用首帧、动态完成、装回及两次客户端重连。见 [背包实拍比较数据](Evidence/bag-comparison.json)。 |
| M249 改造与动作 | 原厂无前握把。机枪稳固握把适配 M249、201、PKM。后握把使用完整原件；开盖左腕与右手捏链分别由局部关节旋转修正。脚架整套装卸。 | [配件联机记录](Evidence/parts-network.json)、Wrist38、Wrist39、GripMount40、BipodPin41、BipodIcon42 和 RearGrip44 的作者配方及本机存档。 |
| 切枪与弓镜 | 三款轻机枪切枪沿当前相机状态衔接。观峰片内覆盖使用实际镜片边界，松弦和变倍率沿同一镜口。 | [切枪记录](Evidence/equip-camera.json)、[观峰覆盖记录](../../Weapons/peakwatch-lens-coverage-20261110.md)。 |
| 双手锤跃击 | 空中运动连续衔接实际重力和速度，真实落地才结算攻击；碰墙避让和取消收势只交接一次镜头偏移。 | [镜头记录](Evidence/leap-camera.json)、[移动与联机记录](../../Weapons/conversation-network-review-20261110.md)。 |
| 螳螂及 ST6 | 正式螳螂使用 ClawV16 普攻及 PounceV11 飞扑；ClawV17 等预览单独保留。ST6 女性独立领口已保存 18 个网格和 70 条配置路由。 | [正式动作与候选](../../Monsters/MantisM27ClawRollbackAndV17_20261109.md)、[领口制作记录](../../Characters/st6-female-collar-repair-20261108.md)。 |

## 源码与恢复

- 背包修复进入公开树的 `Source/FPSGAME/UI`。公共树沿用已有的物品请求接口；完整本机宿主相对本轮修复前的精确补丁见 `Integration/FinalIcon`。M249 的上一批基础源码、角色接入与素材来源见 [M249 基础恢复包](../M24920261109/README.md)。
- 主工程的角色、武器和移动宿主含并行开发。其他本轮功能的专用消费者保存在 `Integration/Source`，共享调用点保存在 `Integration/host-sections.json` 和按主题拆分的差异文件中。差异按其原阶段基线读取，部分阶段覆盖同一函数；不要按文件名把所有补丁连续套用。双手锤已有基础见 [技能动作发布](../SkillActions20261110/README.md)。`configuration.json` 提供枪匠与装配条目，`st6-routes.json` 列出领口拥有的字段，按稳定 ID 合并。
- 动作资产恢复时从当前数据开始。Wrist36 等工具仍被后续拟合引用；Wrist38 的右手避让、Wrist39 的开盖左臂和 GripMount40 的安装位移有先后关系。RearGrip44 安装工具读取 RearGrip43 的 `saved.json` 辨认旧包。
- 无脚架目录图取自监听主机背包实际绘制的原尺寸透明纹理。已发布图像的 SHA-256 和包散列见 [本机资产记录](Evidence/local-assets.json)。恢复时从有合法素材的本地工程取回 `Content/ColdSteelData/Icons/ue_m249_no_bipod.png`、同名 UI 纹理包及 `SourceAssets/InventoryWeaponIcons20261108/Artwork` 下的作者图。使用原项目内的 `save_icons.py` 同步经过确认的作者图。
- `InventoryCapture` 保存产生双端回执与原尺寸图像的检查源码。还原该次夹具时，放回 `Saved/M249NoBipodIcon/20261112-153142`；其配对档案和对齐样本位于本机 `Saved/M249BagIconWire/20261112-151132`。最终实拍位于 `Saved/M249NoBipodIcon/20261112-153142/run-155947`。存档、截图、模型、贴图、音频、动作、UE 包和 DLL 留在本机。公开源树本次未独立构建或打包。

## 本机归档

[退役明细](archive-summary.json) 记录各组原路径、数量、大小、原因和保留替代物。完整逐文件散列在本机 `trash/Conversation20261112/manifest.jsonl`。UE 注册表确认飞扑 V12 的三段动画均无引用。Beast06 普攻仍被两个预览蓝图使用，原包保留。[动画反向引用](Evidence/mantis-package-references.json)
