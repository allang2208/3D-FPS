# 档案中心设备：参考图与 Blender 制作

2026-10-01：认可版本已 [接入正式随机地牢并退役样板](dungeon-data-archive-pool-20261001.md)。模型作者源保留；本文涉及的独立样板布置／安装器现为归档历史。

本文记录首版制作；用户截图反馈后的当前版本见 [贴墙布局与设备细化](dungeon-data-archive-refinement-20260930.md)。V1 保留为作者历史，服务器机柜继续复用；其余柜体、控制台和桌子由 V2 接管，当前摆位也以 V2 为准。

用户指定自行构建老式服务器机柜、档案柜、磁带存储柜和老式调度控制台，先出预览图，再尽量按图还原结构与细节。

## 设计与模型

使用内置 image_gen 分别生成四张一致风格的三视图参考，完整提示词与项目内参考路径保存在 `SourceAssets/DungeonDataArchive20260930/Equipment20260930/Config/references.json`。这些是设计参考；`Previews/*_Blender.png` 才是实际制作模型的 Cycles 渲染。

| 模型 | 主要还原结构 | 作者三角面 |
|---|---|---:|
| ServerRack | 折边壳体、侧检修盖、可调脚、开孔立轨、两组共六个磁盘抽取模块、指针表、8 颗状态灯、真实通风百叶、后部电缆接头 | 56,450 |
| FileArchive | 双列十抽屉、分隔板、索引牌、金属拉手、锁孔、半开中层抽屉的内壁／滑轨／文件夹 | 20,456 |
| TapeLibrary | 按生成图采用五层三列格架、带标签磁带盒、三辐卷盘、留空格槽、下部双抽屉与铭牌 | 74,482 |
| DispatchConsole | 双侧基座及中部膝部空间、斜面台板、双指针表、旋钮、4:3 圆角弧面 CRT、独立键帽、16 个按钮、拨杆、急停按钮及背部接线 | 44,684 |

壳体设计尺寸分别约 0.72 × 1.05 × 2.15 m、1.10 × 0.60 × 1.95 m、1.10 × 0.62 × 2.05 m、2.70 × 1.05 × 1.45 m。把手、半开抽屉和电缆在局部略伸出壳体；精确导出包围尺寸见 `Authored/manifest.json`。

四件共用一套原创 4096 × 4096 BaseColor／Normal／ORM 图集与一个材质槽。烤漆层保持非金属，掉漆区域露钢，氧化区域重新转为粗糙非金属；磨损沿边缘及接缝分布。标签、键面和表盘在图集中印刷，百叶、把手、按钮、玻璃弧面和柜体内壁保留实际几何。Blender 使用 OpenGL 法线，UE 使用独立 DirectX 法线，不重复翻转绿色通道。

采用 Nanite、显式切线和完整回退网格；作者 UCX 简单碰撞按物件整体／控制台支座划分。小螺丝和开关并入整件网格，不生成逐件 Actor 或 Tick。这些制作选择不代表实测性能结果。

## 场景接入

安装脚本只操作 `/Game/GameMaps/Design/L_AbandonedDataArchive_Subject`：西、东设备区各四个服务器机柜；南侧档案区三个档案柜、磁带区三个存储柜；中央下沉区一套控制台，替换 `DataArchive_RecordsDesk1`，保留两侧记录桌。机柜按设备底座顶面 Z=0.16 m 定位，控制台按下沉地面 Z=-0.60 m 定位。设备正面朝向操作通道。

UE 资产根目录：`/Game/Dungeons/DataArchive20260930/EquipmentV1`。最终后台导入及地图保存已完成，`Receipts/install.json` 记录 `equipment_and_map_saved` 和 15 处设备摆放；资产保存记录在 `Receipts/import.json`。原地图备份位于本批 `Backup/`。保存完成不代表游戏内测试通过。

## 交付与恢复

根目录：`SourceAssets/DungeonDataArchive20260930/Equipment20260930`。

- `References/`：四张原始设计预览。
- `Authored/ArchiveEquipment_Editable.blend`：可编辑源，按机械分组保留语义顶点组；包含游戏导出与编辑副本。
- `Authored/SM_Archive_*_V1.fbx`：四件游戏网格与 UCX 碰撞。
- `Authored/Textures/`：原创共用 PBR 图集及两种法线约定。
- `Previews/`：四张实际模型预览。
- `Scripts/author_textures.py` → `author_equipment.py` → `render_preview.py`：纹理、模型及用户要求的预览。
- `Scripts/install_equipment.py`：标准恢复安装入口；`finish_equipment.py` 仅用于本轮尚未发布的细化更新。

主体场景作者配置已接回设备安装链。当前设备作为静态场景资产；抽屉开合、电源开关与终端交互尚未制作。档案中心仍处于独立样板阶段，不提前加入正式随机池。

本轮按用户要求生成设计参考及实际模型预览；没有启动 UE 编辑器、运行游戏、做性能测试或游戏内验收。还原是依据可见参考进行的手工参数化重建，遮挡区域按可制造结构补全，并非扫描级逐像素复制。
