# 四款消耗品地面模型接入

生命药水、魔法药水、5.56 与 7.62 弹药盒已经接入 `AColdSteelPickup`。来源为 `SourceAssets/Consumables5080_20260910/*_candidate_v02.glb`，UE 资产位于 `/Game/Items/Consumables/`。

普通物品掉落时按定义选择静态模型。药瓶高度 18/18.5 厘米、弹药盒高度 12/13 厘米；碰撞盒按缩放后的模型边界建立，模型中心与物理根对齐。沿用已有重力、CCD、摩擦、阻尼、屏幕中心 E 拾取以及世界位置/旋转存档。药液采用独立不透明 PBR 内层、瓶身采用半透明玻璃，避免内外半透明排序导致药液在地面不可见。关闭这批小型透明资产的 Nanite，并加入 AlwaysCook 目录。

`export_ue.py` 保留多材质槽导出 FBX 与纹理，`Tools/AssetPipeline/import_consumables.py` 按材质槽名称绑定 UE 材质。源模型及生成记录保留；未替换背包图标，未改正常玩家存档。

验证：Editor Development 编译成功；导入日志 `Saved/ConsumablesImport.log` 包含 `CONSUMABLE_IMPORT_PASS`。独立游戏进程 `-ConsumablePickupAudit -ColdSteelProfile=ConsumablePickupAudit_20260910b` 验证四种物品各 7 个堆叠的掉落、模型选择、刚体重力、下落、落地不穿透、不自动收取、存档重载位置旋转，以及瞄准拾取后数量保持和 Actor 消失。

最终结果：`ConsumableAudit: COMPLETE checks=39 failures=0`。实际运行截图：`Saved/ConsumablesInGame.png`；验收日志：`Saved/ConsumablesRuntime.log`。首轮测试同步旋转相机并立即交互导致使用上一帧视角，已调整为先瞄准、再在后续帧交互，未绕过游戏中的距离或遮挡检查。

模型仍保留上一阶段已记录的部分弹头、盒边近景细节限制。玻璃为实时游戏材质近似，不等同 Blender 的路径追踪折射。已有打开的游戏或编辑器需重新启动对应运行进程，才能加载这次原生模块与资产。
