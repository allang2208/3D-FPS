# 合阙主泵厅扩容交付

2026-10-22：已制作、导入并保存到 `/Game/GameMaps/L_Dungeon_Randomized`。普通 Game 与 Editor 构建成功。未运行游戏、截图、渲染、试听或多人验收。

## 已落地

- 主厅由 30×26 米扩大为 44×38 米，主厅地面 1672 平方米，约为原来的 2.14 倍；两个局部侧翼另计。
- 中央保留约 22×24 米交战区，两台原尺寸泵机错位移至两翼。立柱嵌入墙侧，泵岛外侧绕行空间按约 6 米净宽制作。
- 连续 U 形回廊改为两个局部控制高台，楼梯收进侧翼；每处设置正常楼梯及明确的落地出口。中间落台高 0.8 米，平台到落台落差 2.8 米。
- 更新 52 块楼梯与平台支撑面。合阙面对高台目标时使用房间的地面站位导航，攻击继续沿用原来的视线、距离与高度条件。
- 后墙增加破损主泵转子，顶部增加吊装结构；地面局部磨损、潮湿，西侧偏冷、东侧偏暖，灯具和光源位置对应。
- 保存 24 组建筑网格，沿用现有泵机、接收罐及材质。新增两个清水滴落材质、一个原创低频机械循环声；仅为环境表现，没有伤害或新增刷怪。
- 奖励室、机械门、宝箱、返程门整体后移 12 米；四个原关闭设施保持关闭。
- 新占位与侧翼纳入随机生成目录、遭遇区域及灯光调度。120 组后备布局重新构造完成；可选捷径和宝藏支路继续按实际运行种子生成。

## 与提案的尺寸差异

净高最终采用 **10 米**，替代提案中的 11 米目标。现有终点下沉 10.8 米，11 米屋顶占位在布局制作中侵入部分上层房间；10 米净高保留首领跃击空间，并与原有地下连接结构衔接。主厅面积、中央交战区、两翼和高台方案保持。

首领技能、伤害、冷却、怪物数量，以及此前单独保留的风险路线／奖励设计均未调整。

## 保存与构建记录

- 制作与重建入口：`SourceAssets/HeQueArena20261022/README.md`
- 可编辑源：`SourceAssets/HeQueArena20261022/Authored/HeQueArena.blend`
- 配方：`SourceAssets/HeQueArena20261022/Config/rooms.json`、`recipe.py`
- 网格保存：`SourceAssets/HeQueArena20261022/Receipts/import.json`
- 材质及音频保存：`SourceAssets/HeQueArena20261022/Receipts/ambience.json`
- 布局数据制作：`SourceAssets/HeQueArena20261022/Receipts/layout-bake.json`，120/120，`game_run=false`、`tested=false`
- 正式地图保存：`SourceAssets/HeQueArena20261022/Receipts/install.json`，`stage=map_saved`
- Editor 构建：`SourceAssets/HeQueArena20261022/Receipts/build-editor.log`，Succeeded，145.14 秒
- 最终 Game 构建：`SourceAssets/HeQueArena20261022/Receipts/build-game.log`，Succeeded，6.12 秒
- 安装前地图与生成器备份：`SourceAssets/HeQueArena20261022/Backups/install-20261022-144233`

重新进入随机地牢生成的新一局使用新场地。空间感、走位、照明、音量及联机体验交由用户测试；上述保存和构建记录不代表游戏验收。
