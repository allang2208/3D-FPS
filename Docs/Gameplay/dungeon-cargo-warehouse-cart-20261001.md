# 仓库复用液压拖车

已将先前货运转运间的手动液压拖车放入仓库样板，2026-10-01。

- 原始来源：`SourceAssets/DungeonVentFreight20260922/Authored/Dungeon_VentFreight.blend` 内 `SM_RS_FreightTransfer_Props`，对应 `DungeonRailCart20260923/Scripts/pallet_jack.py` 的已精修拖车。直接提取成品几何、UV、顶点磨损与六种原有材质；旧货运场景保持原引用。
- 独立资产：`/Game/Dungeons/CargoWarehouse20261001/Reused/Meshes/SM_Freight_PalletJack`。原尺寸约 0.812 × 1.665 × 1.395 m，85,052 三角形，启用 Nanite。五组简单碰撞分别覆盖两根叉臂、泵体和操纵柄；叉臂中间保留空隙。
- 摆放：仓库左侧货箱区旁，Blender 米制坐标 `(-5.1, 3.7, 0.002)`，UE yaw 为 180°，原尺寸，叉臂朝装卸平台方向。避开中央主通道、两侧楼梯、门口及禁堆区。静态陈设，无新增驾驶或推动玩法。
- 已保存地图：`/Game/GameMaps/Design/L_AbandonedCargoWarehouse_Subject`，Actor 为 `Reused_PalletJack`。
- 同步 `prepare_design.py`、`Config/room.json` 和 `Config/module-draft.json`，后续重新构建和正式模块接入可保留此位置。当前仍为待体验样板，未修改随机池。
- Blender 源、FBX、后台安装脚本、操作回执及本次修改前备份位于 `SourceAssets/DungeonCargoWarehouse20261001/CartPlacement/`。

后台导入和地图保存已完成；未启动编辑器界面、游戏、截图、渲染或验收。导入沿用的原模型带近零切线/副法线提示，未因此改造已认可的原始造型。由用户在游戏中体验。

控制台：`open /Game/GameMaps/Design/L_AbandonedCargoWarehouse_Subject`
