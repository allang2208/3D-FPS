# 伐木斧：单次重冲击与竖直占格

## 镜头

`Content/ColdSteelData/axe_impact_motion.json` 将命中镜头合并到 `hit_camera`：接触后 40 ms 达到一次向下、向后的重冲击，保持到 85 ms，再平滑回稳，480 ms 回到原位。峰值原始角度为 Pitch -9.4°、Yaw -1.9°、Roll -2.2°，位置为前后 -2.1 cm、左右 -0.85 cm、上下 -3.2 cm；实际画面继续受玩家镜头运动强度控制。

清空原 `impact_camera` 和 `extract_camera` 的反向回弹，撬柄对镜头的两个增益归零。斧头本身的停帧、撬动拔出、攻击和回收时间不变；挥空镜头不变。

## 占格与图标

伐木斧基础尺寸由 2×3 改为 **1 列×3 行**。新物品沿用 `bRotated=false`，默认竖放；手动旋转后为 3×1。

`NormalizeProductionState` 同步旧存档斧头的 `grid_w/grid_h`，并重算实例 Width/Height，保留原实例、格子及玩家设置的旋转方向。两个方向都只缩小占地，不移动相邻物品。镐与铲的尺寸不变。

用当前 BattleAxe_16000 模型及用户 Meshy 源包中的原 PBR 贴图制作 256×768 透明竖直图标。正式 PNG 路径保持 `Content/ColdSteelData/ProductionTools/axe.png`，同时重导入同名 UE 贴图；背包、仓库与快捷栏继续共用现有加载逻辑。

可编辑图标场景、脚本及旧图标备份位于 `SourceAssets/AxeImpactInventory20260919/`。这是交付用图标制作，没有启动游戏或进行验收渲染。

## 接入状态

数据、源码及正式图标已接入。`Tools/Build/Build-Editor.ps1` 返回 Succeeded（排队等待并行构建完成后，目标已是最新）；记录位于 `Saved/BuildEditor/build-20260919-204411.log`。图标 Python commandlet 导入完成，退出码 0，记录位于 `Saved/Logs/AxeUprightIconImport20260919.log`。

未执行自测或实机验收，由用户测试。重新进入游戏后加载新镜头、竖直图标，并对旧存档斧头应用尺寸迁移。
