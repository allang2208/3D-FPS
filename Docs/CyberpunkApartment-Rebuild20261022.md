# 赛博朋克公寓：同布局重建，2026-10-22

> 当前版本已由 [截图反馈 V2](CyberpunkApartment-RefinementV2-20261022.md) 接续：灰黑配色、分体搜索柜、办公室与健身室。下文记录首次重建版，恢复制作请走当前 V2 路由。

地图仍为 `/Game/GameMaps/L_CyberpunkApartment`，替换既有公寓。保留原来的三卧、客厅、厨房、玄关、横向走廊、双卫、服务间和朝海湾阳台的房间关系，建筑尺寸沿用原始布局的 1.25 倍。家具按实际使用尺寸摆放，不再随整栋建筑统一放大。

本次是新结构与独立家具装配。旧的全房间合并网格退出地图，原始资产保留，供追溯和回退。窗外继续使用已保存的“岸的一边看对岸”海湾夜景。

## 交付与真源

| 内容 | 项目相对位置 |
| --- | --- |
| 替换后的地图 | `Content/GameMaps/L_CyberpunkApartment.umap` |
| 新资产目录 | `Content/Props/CyberpunkApartmentRebuild20261022` |
| 房间边界、材质与复用资产映射 | `SourceAssets/CyberpunkApartmentRebuild20261022/design.py` |
| 可维护的几何及装配作者 | `SourceAssets/CyberpunkApartmentRebuild20261022/author.py` |
| 新制构件的 Blender 工程 | `SourceAssets/CyberpunkApartmentRebuild20261022/CyberpunkApartment_Rebuild.blend` |
| 构件导出与布置清单 | `SourceAssets/CyberpunkApartmentRebuild20261022/assembly.json` |
| 资产导入保存回执 | `SourceAssets/CyberpunkApartmentRebuild20261022/assets_saved.json` |
| 地图保存回执 | `SourceAssets/CyberpunkApartmentRebuild20261022/map_saved.json` |
| 最近一次成功安装记录 | `SourceAssets/CyberpunkApartmentRebuild20261022/installed.json` |
| 替换前的原公寓备份 | `SourceAssets/CyberpunkApartmentRebuild20261022/Backups/20261022-083920/L_CyberpunkApartment.umap` |

Blender 文件保存新制网格、布局与共享资产引用；共享 UE 家具在 Blender 中表示为带资产路径的锚点，不重复导出为另一份模型。UE 地图实际引用已安装的原资产。

## 制作内容

- **结构与收口：**按原房间边界重做墙段、开口、分区顶棚、地面、门槛、踢脚线、面板接缝、开敞门套及入口外侧短廊。地板拼接、石材分格和湿区墙面有独立几何间隙。
- **门窗与阳台：**新幕墙框、密封条、上亮窗、窗帘轨道与褶皱窗帘；独立阳台隐私墙、玻璃与金属扶手。栏杆扶手约 1.10 m 高，未把整面隐私墙当作可翻越栏杆。
- **卧室：**新床架、软包床头、圆角床垫、包边、鼓起的枕头、垂落被褥、床头柜、衣柜和带显示器键盘的书桌。床、桌、柜分别是可移动装配实例。
- **厨房与服务间：**新固定柜体、真实开口的水槽、龙头、灶面、烤箱面板、排烟罩、吊柜、洗衣机与供电细节。餐桌、餐椅、冰箱、咖啡机和水壶直接复用已有资产。
- **客厅与卫浴：**复用精修沙发、电视、书柜、茶几、面盆、镜子、马桶、淋浴五金与毛巾架；补充配套媒体柜、地毯、杯盘杂志、淋浴底盘和固定挡水玻璃。
- **灯光：**顶灯、餐桌吊灯、柜底灯带、床头阅读灯和阳台灯都有灯具几何。15 个实际 RectLight 使用相应扩散板的位置；保留海湾与夜间方向光。灯光、材质与视感尚未经过游戏验收。

## 复用清单

复用 21 种家具与植物网格、40 个摆放实例，另保留 1 套原有近景楼体作为阳台下方塔身和上方建筑冠部；已有纹理与材质直接引用。`assembly.json` 记录每个实例对应的精确资产路径。

| 部位 | 来源 | 使用方式 |
| --- | --- | --- |
| 沙发、餐椅、茶几 | `Dungeons/ReceptionHall20261006/Refine20261007/Meshes` | 复用沙发包边、靠垫与家具细节；沙发表面使用现有织物材质覆盖 |
| 人体工学椅 | `Dungeons/MedicalExecutiveOffice20261010/Meshes` | 三个卧室书桌各一把 |
| 餐桌 | `Dungeons/StaffLiving20261002/Meshes` | 维持原桌面高度，与餐椅配合 |
| 书柜、电视、面盆 | `Dungeons/StaffLiving20261002/ScenePolishV4/Meshes` | 复用当前已安装精修版本；不重建公共资产 |
| 冰箱四部件、马桶、洗衣篮 | `Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes` | 冰箱按原门体铰点装配为关闭状态；其余独立摆放 |
| 镜子、淋浴五金、毛巾架 | `Dungeons/StaffLiving20261002/RefinementV3/Meshes` | 对齐本公寓的安装面和瓷砖饰面 |
| 咖啡机、水壶 | `CoffeePolishV7`、`WallInsetV6` | 置于实际台面高度；供电线跟随本场景插座重新布置 |
| 植物 | `PN_tropicalGroundPlants/Meshes/tropicalPlant_01_01`、`02_01` | 配合新花盆使用；不另做低面数叶片 |
| 木皮、织物、地毯、拉丝钢、橡胶、涂漆 | `SubstrateMaterials/Materials` | 新制构件复用既有材质和贴图 |
| 石材、地坪、陶瓷、玻璃、屏幕 | 接待大厅、员工生活区、既有公寓 | 引用共享材质；共享源包不修改、不复制 |
| 阳台外近景楼体 | 既有 `CITY_our_tower` | 沿用原来的 1.25 倍变换，承接下方塔身与上方冠部，避免公寓悬空；不恢复旧室内家具或旧城市远景 |

没有使用世界坐标已经烘进模型的整房间装饰组。厨房固定柜体、卧室床具与衣柜等缺少适合本布局的完整组合件，因此单独制作。

## 碰撞与交互接入

- 建筑主体约 20 × 13.75 m，顶棚底面 3.6875 m；原房间关系与阳台朝向不变。
- 地面采用连续碰撞。墙体按实际实墙分段生成 UCX，门洞没有封口凸包。门窗玻璃、挡水玻璃、家具、阳台栏杆各自处理；杯盘、窗帘、灯带、植物叶片不阻挡玩家。
- 七处门继续使用原生 `ColdSteelSlidingDoor`：入口、主卧、卧室二、卧室三、卫浴一、卫浴二、阳台。保留 E 交互、现有音效、服务器权威开合及 6 秒自动关闭。门 Actor 为单位缩放，网格尺寸已烘到最终厘米尺寸。
- 门框与半宽门扇的初始位置按原生 `AlignGeometry` 规则设置；单扇各一个把手。原生代码未修改。
- `AP_RailCollision` 使用连续简单碰撞并带 `Traversal.GuardrailDrop`，接原有栏杆翻越/下翻逻辑。
- 出生点位于玄关，UE 坐标 `(1240, -1255, 100)` cm，朝向客厅一侧。胶囊半径 42 cm、半高 96 cm，起始位置按胶囊中心设置。
- 使用原 `FPSGAMEGameMode`。没有修改项目默认启动地图或其他场景。

这些是制作与装配参数，不是碰撞、交互、视觉或多人功能的实测结论。

## 维护与制作入口

新作者入口为 `author.py`；UE 后台导入及落盘入口为 `publish.py`，内部依次执行 `import_assets.py`、`install_level.py`。当前可继续使用旧的 `31_author_playable.py`、`34_import_playable.py`、`35_install_level.py`，它们在新版本已保存时转到本次作者链，不恢复旧低模装配。

制作使用接待大厅已有精密几何工具 `SourceAssets/DungeonReceptionHall20261006/Scripts/geometry.py`，该文件仍是源依赖。不得按旧日期批量删除它或上述共享艺术资产。

模型按房间与家具拆分；小五金合并到所属构件。适合的高面数不透明构件使用 Nanite，其余较复杂构件提供距离 LOD。装饰件与灯光设置局部距离限制。未进行性能测量，不提供帧率提升结论。

本次仅完成后台制作、必要资产编译、导入与地图保存；未启动编辑器、PIE 或游戏，未制作验收截图或渲染，交由用户体验。
