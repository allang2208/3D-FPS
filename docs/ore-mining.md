# 矿石采集破碎动画 · 2026-09-06

旷野 F7 工具模式、7 矿镐，左键连续采集。已接入旷野原有 Poly Haven `rock_09` / `boulder_01` 模型：独立石块（摆放宽度不超过 3 米）三击破碎，大型岩壁保留。普通石块回收石材 ID 2；地形矿物仍是 ID 3，不把普通石块伪装成矿脉。

## 真实石块接入

- `scenic_valley.gd` 为石块碰撞体记录对应 MultiMesh 批次和实例索引，仅隐藏被采集的实例，邻近石块保持原样。不改变摆放、贴地与原有 LOD。
- `rock_fracture_mesh.gd` 从源模型切分 8 块，保留外表 UV、法线，断面封口使用同源材质。`tools/basic-tools/bake_rock_fragments.gd` 将两种模型烘焙到 `assets/models/basic_tools/rock_fragments/`，运行时复用切分结果，并套用场景实际材质和摆放变换。
- `scenic_rock_harvest.gd` 负责三击、单次石材奖励及实例移除；碎片沿用重力、弹跳、淡出清理逻辑。移除记录 `quarried_rocks` 和石材数量写入同一份地形存档，地形刷新与读档不会复活已采集石块。旧存档缺少该字段时视为尚未采集。
- 实际渲染测试 `tests/test_scenic_rock_harvest.gd` 覆盖工具门槛、三击、8 块原模型碎片、相同材质、奖励去重、邻近实例不变、读档与地形刷新。MultiMesh 变换断言需有图形渲染器；无头 Dummy 渲染器不提供可靠的实例变换读回。
- `tests/render_scenic_rock.gd` 使用原有 `rock_09`、正式采集控制器和实际矿镐生成 144 帧 / 6 秒预览，输出 `tools/basic-tools/scenic-rock-preview.gif`。这是独立布光的实际模型动画预览。

## 体素矿格采集（保留）

- 矿镐仍为 0.68 秒周期、0.24 秒接触、3.2 米射线距离。前两次接触播放裂纹、小碎屑和敲击声；第三次才修改地形、回收材料，并爆散 14 块有碰撞和重力的不规则碎片。
- 矿石保持现有蓝灰色，岩石为灰色。泥土仍按原单次采集处理。目标换到另一个矿格会重新计次，F9 读档和 Ctrl+Z 撤销清除未完成敲击进度。
- 碎片弹跳、落地，6 秒后淡出、7 秒清理；只与世界碰撞，不挡准星、不相互堆叠求解，也不重复领取。奖励仍由现有 `world.mine()` 一次结算，随地形存档保存。
- 开始前检查了现有矿镐接触动作和体素材质/回收配置；没有独立矿块源动画，本轮为新制破碎特效。音效复用已接入的 Kenney `impactMining_000.ogg`。

实现：`scripts/tools/ore_break_fx.gd`；采集计次与工具门槛：`scripts/tools/basic_toolkit.gd`；两处接线：`scripts/voxel_lab/voxel_lab.gd`、`wilderness_editor.gd`。

验证：`tests/test_ore_mining.gd` 覆盖工具许可、三击、未完成不扣矿、奖励去重、真实矿格移除、碎片碰撞/法线及存档恢复。`tests/test_basic_toolkit.gd` 对正式旷野工具、树木与存档做回归。`tests/render_ore_mining.gd` 使用现有方块体素世界和实际矿镐/碎片渲染预览，作为独立动画样板，不是正式旷野矿脉外观截图。
