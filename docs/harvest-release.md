# 采集与矿脉发布范围

从 origin/main 独立整理本次基础工具、伐木、石块/矿脉采集、六种背包材料、八种矿脉几何及对应技能。未合并共享 master 上其他会话的未发布提交。

当时建筑工坊基础尚未发布，因此该批只带入采集所需的 build_costs.gd 与木石物品定义。2026-09-07 的后续批次已从最新 origin/main 独立组合正式 BuildingSystem、五构件目录与旷野接入；本段保留为 2026-09-06 发布边界记录。

保留可编辑 Blender、两把工具源 GLB、Kenney 原包及许可证、贴图原件、烘焙脚本和最终预览。旧铁矿贴图 iron_albedo.png 为生成历史原件，当前使用 iron_albedo_v2.png；旧采集 GIF 保留的是最终材质版本，八种新形态以 ore-variants-preview.png 为准。

清理仅限本会话 tools/basic-tools 中旧帧目录、临时日志、被替代的三份 GIF 和 basic_tools.blend1。模型源文件和有效导入配置没有清空。

## 发布目录验证

- 新目录首次 --import 退出 0；远端既有 AKM.mtl、fir_sapling 贴图缺失信息仍存在。
- 主场景 --quit-after 180 退出 0，无脚本解析错误；既有装备图标缺失及退出资源告警仍存在。
- test_reload 两条换弹路径 ok=true；test_combat 移动、玩家伤害等通过，但 proj_hit_damage=false，未宣称完整战斗回归通过，本次未改其战斗脚本。
- test_basic_toolkit、test_tree_cut_fit、test_ore_mining、test_ore_variants 均 PASS。
- 图形模式 test_scenic_rock_harvest 金矿 PASS：当前谷地 6 种实际变体，露出高度检查、三击、8 碎片、单次背包奖励、相邻实例、存档恢复通过。此次结算样本 13 ms。
- 建筑工坊基础未发布，因此本发布目录未执行 test_build_materials；该功能的原开发目录验证记录保留在 docs/build-materials.md。
