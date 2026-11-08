# 灼锋焰甲：武器附着与篝火 V6

当前通用武器与飞行箭矢均使用 [原版暖色火焰全武器适配 V12](../FlameArmorAllWeapons20261108/README.md)。本目录 V6 系统作为历史保留，以下为制作记录。

武器附焰最新活动资产为 [局部逐帧跟随 V10](../FlameArmorFollow20261108/README.md)，通用武器、剑、锤统一挂接实际部件。此目录的箭矢系统继续沿用，原作者保留 V6／箭矢恢复用途。

2026-11-07，按用户要求排查新增武器漏焰，并升级武器火焰。保持技能伤害、耗蓝、持续时间、修炼及脚下火环。

## 定向排查发现

- `FlameArmorAttachments::Gather` 只采样双手剑、工具、弓、法杖、空手和枪，未采样 `UKukriWeaponComponent`，因此单持、双持、独自副手的弯刀/战斧遗漏。
- 手枪副手 `UOffhandKukriComponent`、法杖副手 `UStaffOffhandMeleeComponent` 未进入附着采样。第三人称采样也未处理 `Kukri`、`KukriDual`、`OffhandKukri`。
- 法杖搭配副手近战的世界装备描述没有建立副手模型。本次补入现有 `KukriDual` 左手装备路径，使用同件物品的模块、正握和现有序列化。
- 刀刃只有中心直线，且环绕基向量按世界朝向临时求取，没有使用实际模型截面。新弯刀曲线、斧头宽刃不适合复用细圆柱。
- 原生铁铲已把铲面烘入 `SK_Shovel`，静态 `ToolMesh` 不承担可见模型；旧工具附魔坐标仍是估算值。本次直接从保存网格中提取 `WPN_root` 刚性铲面，不改共用电附魔坐标。

## 制作与接入

`build_surface_profiles.py` 读取八套当前模块目录的刀刃/斧头模型，以及静态和原生铁铲。逐模型从真实三角形求八个截面，输出 `FlameArmorSurfaceProfiles.h`：中心偏移、宽度、厚度随截面变化，运行时沿实际已装配组件/骨骼变换。运行时不读取顶点、不扫描场景；最多缓存 64 个几何查询结果。

补齐上述第一人称、第三人称入口，以及动作组件到焰甲的帧序依赖。既有枪管、双枪、弓臂、搭弓箭、法杖、工具刃、双手锤的接口继续使用；锤头火焰保持两个锤面两侧分区。仍使用最多四个附着系统。

新资产目录 `/Game/Skills/FlameArmor20261107/CampfireV6`：

- `M_FlameArmorCampfire` 复制当前篝火 Fire 渲染器实际使用材质；保留橙红火色及曝光通道，8×8 帧图集启用相邻帧混合，接触淡出调整为 0.45 cm。
- `NS_FlameArmorWeapon`：20 个持久表面底焰，28/s 随机火舌，最多 12/s 短运动余焰，4/s 余烬。独立相位、方向、尺寸、速度与寿命；每帧依据武器截面重新定位。每个火舌以 48–60 fps 播放一段连续动画，不逐帧重抽随机值。
- `NS_FlameArmorArrow`：飞行箭沿用原世界空间尾焰合同，换为同一篝火材质，每支箭使用自己的种子。

主体供体为 `/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire`，底焰使用原焰甲 FireballV3 热核。篝火、星髓蓝火、旧 TorchV2 资产及脚下火环不修改。无需新增灯光。

## 制作入口与状态

通过 `save_assets.ps1 -Script run_assets.py` 使用现有批次互斥窗口，合并截面导出和独立新资产制作、编译、保存。已有编辑器走桥，无编辑器走后台 commandlet。`surface-profiles.json` 已记录 49 个实际网格；`install-receipt.json` 已记录新材质、武器和箭矢 Niagara 三个资产保存成功。运行时常量已切换到新 Weapon/Arrow 路径，Body 仍使用原火环。

本次定向排查读取源码和已保存几何；未启动测试、游戏、截图或渲染，未主动打开或关闭交互编辑器。视觉与性能由用户测试。

`FPSGAMEEditor Win64 Development` 后台构建成功并生成普通模块 DLL（866 个构建动作，`Result: Succeeded`）。日志：`Saved/BuildEditor/build-20261107-004307.log`。这份构建结果不代表运行时或画面验收。
