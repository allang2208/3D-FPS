# 门框闪动、默认材质方格和墙面细节排查修复

用户截图：`codex-clipboard-986dc35d-0ad1-49b2-a735-0753f14f8972.png`。本轮排查与制作限定在地牢接口模型、对应材质及作者／导入脚本。

## 已定位的原因

运行日志明确记录 `M_NaturalCeramicAtlas`、`M_NaturalCeramicCore`、`M_CeramicFractureCore` 缺少 `InstancedStaticMeshes` usage，游戏使用 Default Material。后台读取保存资产也确认这些标记为 false；新版 `M_FabIndustrialMetalV2` 还同时缺少 ISM 和 Nanite 标记。黑色方格来自默认材质回退，不能通过增加灯光或换更高分辨率贴图解决。

普通房间作者函数给墙壳和钢框使用了相同的门洞边界：两者的侧面都位于净口两侧，底面都位于 2.8 m。另一个冲突是普通 Transit／Threshold 的墙内侧与房间钢框内侧重合，RouteElbow 的顶棚底面也与门框下表面重合。9 月 23 日的退让修改只覆盖 TreasureLink。

性能批次确实引入／扩展了 Nanite 和实例化，但没有对这批墙、瓷砖做破坏性减面。当前资产抽查的 `keep_percent_triangles=1`、`trim_relative_error=0`、`fallback_percent_triangles=1`、`fallback_relative_error=0`；Distribution 墙皮仍为 180199 个三角形。当前设置及该次运行日志中纹理质量为 3，Streaming.MipBias 为 0。本次不回退这些性能设置。

## 修复内容

- 将活动目录以及该次日志涉及的地牢材质用途持久化。48 个相关材质引用中，25 个基础材质需要修正用途；实例随父材质更新。材质图、颜色、法线、粗糙度贴图和用户指定的 Fab 来源保持原有内容。
- 普通墙壳的原有门洞边缘向钢框背后退让 6 cm，门楣底面退让 7 cm；在 7 cm 钢侧框和 8 cm 顶框背后留 1 cm 重叠支撑，避免形成透光缝。钢框净口仍为 300 × 280 cm。
- 既有钢框厚度由 29 cm 增至 32 cm，前后饰面与瓷砖形成明确高差，保留原有 UV、材质槽及其他栏杆构件。
- Transit、Threshold 的墙内侧和顶棚底面后退 4 cm，通过调整墙／顶板厚度保持外包围不扩张；地板不修改。所有三份瓷砖随机表面及踢脚线同向移动，缩短直段也不依赖沿长度缩放的退让距离。
- RouteElbow 墙顶抬高 4 cm、顶棚向上退让 4 cm，外顶高度保持原值。门口位置、朝向、占地、楼梯与地下汇流算法不改。
- 75 份网格在原资源路径重导，保留原碰撞设置、Nanite 设置和完整回退；不替换地图目录或重置随机池。只处理普通接口及其带侧门版本，不重新制作 Boss 自定义建筑或楼梯内部结构。
- 同步更新公共墙体作者函数、瓷砖变体作者函数、房间导入器，以及釉面／断面／锈钢材质制作入口。新增 `Tools/AssetPipeline/dungeon_material_usage.py`，在资产生产阶段保存所需用途，避免依赖游戏运行时自动补标记。

## 排查证据与执行边界

- `SourceAssets/DungeonSurfaceRepair20260924/Receipts/inputs.json`：修复前保存资产的几何设置和材质用途。
- `materials.json`：基础材质用途修改及保存记录。
- `geometry.json`：局部几何制作、修改前后尺寸与原始 FBX 备份。
- `reveal-diagnosis.json`：按用户要求对比实际源网格；31 份墙壳与钢框内表面共面的面数从 476 降为 0，面数和 UV 层数保持一致。它只证明对应几何接触面修正，不等于游戏画面验收。
- `import.json`：逐网格保存、来源散列、碰撞及材质槽记录；仅 `stage=meshes_saved` 且 `remaining=0` 代表全部导入结束。

原始 FBX 与改前资源保存在 `Sources/BeforeFBX`、`Sources/Before/Content`；本轮修整后的可编辑 Blender 文件和 FBX 放在 `Authored`，后续导入所用原作者目录的 FBX 也已同步。本轮没有改 C++，无需新增原生构建。

后台 commandlet 执行资产读写，不启动交互编辑器、游戏、PIE 或验收渲染。运行画面、碰撞和实际帧数仍待用户复测。

最终落盘结果：`import.json` 为 `meshes_saved`、75 份网格、`remaining=0`；全部导入批次正常退出。另一次后台读取的 `saved-inputs.json` 中，原先对应问题区域的 8 个基础材质均已具备 ISM／Nanite 用途，缺失数为 0。此读取没有运行地牢或截取画面。
