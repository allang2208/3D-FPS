# 四品阶药水瓶 V1

用户同意按瓶型区分普通、中级、高级、特级，生命与魔力只替换瓶中液体颜色，并选择 Blender 精确建模。

模型、作者参数、导出和保存回执位于 [SourceAssets/PotionTiersBlender20260926](../../SourceAssets/PotionTiersBlender20260926/README.md)。参考设计仍保留在 [PotionTierDesign20260926](../../SourceAssets/PotionTierDesign20260926/README.md)。

运行时使用独立的 `/Game/Items/Consumables/PotionTiersV1` 资产。四档各保存 Shell / Liquid / Stopper / Closed 四个网格，红蓝版本共享几何。所有网格导入三级 LOD；液体无碰撞，其余部件带简化 UCX。

`Content/ColdSteelData/potion_visuals.json` 将八种物品 ID 映射到四套瓶型、实际高度、统一瓶口抓握基准及红蓝材质实例。`Items/PotionVisuals.*` 缓存只读目录；`FPSPotionUseComponent` 提前异步请求四档分件和两种液体材质，饮用开始时切换；`ColdSteelPickupConsumable` 在拾取物构建时使用对应 Closed 网格及液体材质槽。

原物品身份、数量、药效、稀有度、存档与 2.10 s 喝药时序不变。共用 HP 既有抓握姿势并按各档高度平移瓶底，瓶口距离抓握基准保持 3.2 cm。原模型保留；背包目录图标仍为原版本，未扩展本轮任务进行重绘。

本轮是后台制作、导入保存与必要编译。没有启动交互编辑器、游戏或运行验收。玻璃为实时透射近似；手指接触、折射观感、拾取与空瓶抛出表现待用户测试。构建输出在源资产目录 build-console.log。

FPSGAMEEditor 常规构建结果：Succeeded，16 个构建步骤，18.90 秒。基础 UnrealEditor-FPSGAME.dll 已链接落盘，未使用 Live Coding。构建记录：Saved/BuildEditor/build-20260926-214301.log。

2026-09-27 握点微调：按用户反馈，左手沿瓶身再下移 1.5 cm。运行配置 potion_use_motion.json 中 HP 的 grip_in_palm.Y 从 -2.0 改为 -3.5，兼容 MP 参数从 -2.2 改为 -3.7；当前四品阶 HP/MP 共用 HP 握姿，因此全部同时应用。瓶口、瓶身轨迹、各档 grip_height_cm、手指屈曲与动作时间保持原参数。本次为运行 JSON 调参，无需 C++ 构建；重新创建玩家（重新开始游玩）读取。未测试或重烘焙旧版瓶型的 Blender 手臂动作参考文件。

2026-09-27 第二次握点微调：按用户继续下移的反馈，再下移 1.0 cm，HP grip_in_palm.Y 为 -4.5，兼容 MP 为 -4.7。相对本日首次调整前累计下移 2.5 cm；仍保持瓶口轨迹、手指参数和动作时序。四品阶 HP/MP 共用的运行配置已落盘，重新开始游玩读取，无需编译；未运行测试。
