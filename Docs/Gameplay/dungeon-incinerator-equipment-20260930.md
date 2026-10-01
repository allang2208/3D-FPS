# 焚化厅精密设备 V1

后续用户反馈修订：炉门铭牌已改为单一正面贴图，栏杆更换为带连续 UCX 的 V2。当前引用及边界见 [铭牌与栏杆修订](dungeon-incinerator-scene-fixes-20260930.md)；下文为 V1 制作来源记录。

2026-09-30 按用户要求走 Blender 硬表面管线制作，已导出 FBX、导入 UE、完成 Nanite 制作并保存至独立焚化厅地图。没有启动交互编辑器、游戏、PIE、渲染或运行测试；实际视觉、操作空间与碰撞体验交由用户测试。

## 已保存的设备

| 设备 | 已建模的结构 | 作者尺寸 / 场景数量 |
|---|---|---|
| 炉门与驱动组件 | 厚门板、折边、槽钢加强筋、门框密封条、三组铰链、六点锁紧压爪、连杆、手轮/轮毂/减速箱、液压缸端盖与拉杆、镀铬活塞杆、双耳销轴与开口销、接头/两条软管、压力表、检修铭牌 | 炉口对应 2.2 × 2.6 m；包含墙侧液压件的整套包围尺寸约 3.21 × 0.76 × 2.90 m，三座炉复用同一网格 |
| 滚筒投料推车 | 17 根金属滚筒、轴承座、止挡杆、护边、空心焊接车架、真实开口叉车槽、下层折边接液盘、双握把、四组轮胎/轮毂/轮叉，其中两组万向带刹车 | 约 1.43 × 1.75 × 1.09 m，1 件；滚筒顶面 0.72 m，对应固定投料槽高度 |
| 带盖医疗废物翻转料斗 | 有板厚的锥形斗体与内部、翻转支架/耳轴、折边与密封、双片独立盖/合页/提手、后部弹簧锁扣、短保险链、排液堵头、叉车槽、四组脚轮、后推手 | 约 1.66 × 1.71 × 1.59 m，1 件 |
| 既有配电柜 | 复用此前有百叶、门封、铰链、仪表的精修资产 | `/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet`，观察台 1 件 |

两辆车合计两件，均在用户指定的 1.8 × 2.0 m 单件占地内。尺寸来自本次作者导出清单，并非独立运行测量。当前为停用状态的静态布景，未加入开门、液压动作、推行或投料交互。

两车中心位于作者坐标 `(-6,-3.6,0)` / `(6,-3.6,0)`，靠炉前停放；配电柜位于 `(0,9.55,2.4)`。炉门组件以各炉前墙面 `y=-7.25` 和房间地坪为安装基准。UE 坐标换算为 `(x,-y,z)×100`。

## 表面制作

共用一套 4096 × 2048 图集：BaseColor、NormalGL、ORM（R=AO、G=Roughness、B=Metallic），单网格单材质。区分耐热灰黑漆、褪色青绿烤漆、工业赭黄漆、拉丝钢、镀铬杆、橡胶与积灰。裸露金属采用线性反照率制作后统一编码 sRGB；漆层和氧化物保持非金属。

掉漆偏向板边，污垢偏向下缘；焊缝、槽口、销轴、铰链、轮缘、密封、软管接头和钣金厚度为实际几何。小腐蚀起伏复用项目已有 `BlastFurnace_WroughtIron_Height.png`，来自既有 Sharur Normandy Village / `T_MetalRust_00A` 派生流程，保留原项目使用范围，不把图集或来源原件声明为 CC0。其余材质变化与设备标识为本次原创制作。

沿用了 `asset-model-workflow` 的既有沉淀：真实接合面、闭合圆环索引、板厚/折边、每面 UV、平滑标记先于加权法线、有效切线、正确 Normal/Masks 采样器；新修订资产使用独立路径，不通过旧网格重导叠加单位转换。未触发技能里的默认测试或验收步骤。

## 文件与接入

根目录：`SourceAssets/DungeonIncineratorHall20260929/Equipment20260930/`。

- `Authored/IncineratorEquipment_PrecisionV1.blend`：贴图已打包；`EDITABLE_COMPONENTS` 中保留未三角化母版及语义顶点组，`GAME_EXPORTS` 中保留导出网格。各液压/门/轮组件可按顶点组选择编辑，尚未做动画绑定。
- `Authored/SM_Incinerator_*_V1.fbx`：三组游戏网格，作者三角面分别为 40,351 / 49,186 / 54,436。不是 UE Nanite 回退计数，不能据此推断帧率。
- `Authored/Textures/`、`atlas.json`、`manifest.json`：PBR 原图、图集区域、作者尺寸、语义部件和导出清单。
- `Scripts/author_textures.py`、`mesh_helpers.py`、`author_equipment.py`：可重复制作源；`Config/layout.json`：关卡设备定位及旧粗模替换清单。
- `Scripts/install_equipment.py`：只写入本批新包与焚化厅独立地图。先保存依赖，再替换旧门板/门框/粗细节三个 Actor，增加三套炉门、两车与既有配电柜；不改原配电柜资产。
- UE 资产：`/Game/Dungeons/IncineratorHall20260929/EquipmentV1/{Meshes,Materials,Textures}`。
- 地图：`/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject`；仍从出征菜单“废弃焚化处理厅 · 主体样板”进入。
- `Backup/L_AbandonedIncineratorHall_Subject.umap`：本批编辑前地图；旧粗模资产保留，不再由当前地图引用。
- `Receipts/blender-author.log` 与 `Receipts/install-v1-stdout.log`：实际制作日志；`Receipts/install.json` 的 `stage=equipment_and_map_saved`、`map_saved=true` 表示本轮完成落盘，6 个设备 Actor 已记录。

使用无界面 `UnrealEditor-Cmd -run=pythonscript -nullrhi -NoShaderCompile` 导入和保存，进程退出码 0。材质节点、纹理压缩与静态网格构建均已写入资产；着色器实际显示、近景表现和运行表现未验收。没有修改随机房池、怪物、伤害、灯光或原生 C++，本轮不需要原生重新编译。

结构源的 `prepare_design.py` 已维护设备安装器入口，`install_subject.py` 在新建样板地图后接入本轮组件；对已经存在的地图仍禁止整厅覆盖，使用独立设备安装器。重做几何修订时使用新的 UE 版本目录，保留本版来源和回执。

## 制作参考与剩余素材

机械结构语言参考了制造商公开资料：[Inciner8 医疗焚化设备](https://www.inciner8.com/medical-incinerator-range/i8-m500)、[Unitran 自卸料斗](https://www.unitran.ca/product/specialty-products/self-dumping-hoppers/)、[Creekside 自卸料斗](https://creeksidemanufacturing.com/products/self-dumping-hoppers/)。这些页面仅作为液压、轮架、翻转支点、叉槽与锁扣的结构参考；本模型是为现有炉口原创适配的游戏布景，不是上述产品的准确复刻。没有下载或复制页面模型。

炉门机构、两件移动设备和配电柜无需再寻找资源。仍可补：密封医疗废物桶/封口袋、灰渣堆、炉口烟熏和锈水贴花、灭火器、防护面罩与耐热手套。专门炉控台可留到后续：已有配电柜承担配电布景，不表示已实现炉控交互。原免费候选和素材交接位置见 [素材清单](dungeon-incinerator-hall-assets-20260930.md)。
