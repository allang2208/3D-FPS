# 废弃焚化处理厅：后续细节素材清单

检索日期：2026-09-29 至 2026-09-30。以下是公开页面可获取的候选，尚未下载、导入或进行模型/材质适配。主体沿用本工程已有材质、灯具及管件制作方法，本轮不依赖新购素材。

**2026-09-30 更新：** 用户指定的炉门机构、滚筒推车、带盖医疗废物料斗已通过 Blender 原创制作并导入样板地图，配电柜已复用项目现有精修资产。这四项无需再下载。详见 [精密设备制作记录](dungeon-incinerator-equipment-20260930.md)；下方公开资源保留为后续候选，没有因制作新设备而自动获取。

## 优先获取

**标识更新：** 三炉编号与停用牌、入口牌、生物危害牌，以及投料位、主通道、暂存位、灰坑边缘地面划线已制作并保存，见 [标识与地面划线](dungeon-incinerator-signage-20260930.md)。接灰区原有提示牌继续使用。

| 优先级 | 细节素材 | 预计数量 / 尺寸约束 | 用途与获取建议 |
|---|---|---|---|
| 已制作 | 工业焚化炉门的锁紧机构、手轮、液压缸、隔热门板 | 1 套已复用三处；适配约 2.2 × 2.6 m 炉口 | Blender 精细建模、PBR 与 UE 资产已保存。含六点锁紧、减速箱、铰链、销轴、压力表与软管；无需另找。 |
| 已制作 | 滚筒投料推车 / 带盖医疗废物料斗 | 各 1 件；占地约 1.43 × 1.75 m / 1.66 × 1.71 m | 已保存至两侧炉前区域；带真实滚筒、轮组、叉车槽、盖板、翻转支点及锁扣，无需另找。 |
| P1 | 控制台、仪表盘、压力表、急停按钮 | 控制台 1 组，仪表 3–6 个 | 观察台预留约 4 × 1.3 m 靠墙带。下方 Power Box 可提供局部配电细节，不能代替完整炉控台。 |
| P2 | 密封医疗废物桶、危废箱、封口袋 | 4–6 件，尽量单件带盖 | 集中在东侧设备区；下方 Industry Props Pack 6 可用于通用桶/箱，医疗危废标识和袋体需另配。 |
| P2 | 积灰、烧蚀、烟熏、锈水贴花与灰渣堆 | 2–4 种形态，各少量 | 只围绕炉口、集烟罩、灰渣坑放置。需要透明边缘、正确法线方向、可辨认来源；不以随机污渍铺满作业区。 |
| 可复用 / 标识已制作 | 消防器材与标识 | 现有灭火器可放 2 个；本批新增实体标牌 8 块 | 项目已有 `/Game/Dungeons/ArtPass20260922/Meshes/SM_Prop_Extinguisher`，无需再下载；本厅灭火器摆放留待后续。编号、停用、生物危害与入口牌已完成，接灰区牌保留。 |
| P3 | 工具、耐热手套、防护面罩、检修灯、断开的电缆 | 3–5 个成组布景 | 主体认可后添加，不逐件堆满路径；工具和杂物不新增交互系统。 |

## 已找到的免费候选

| 资源 | 公开页面信息 | 本厅用途 / 下载建议 |
|---|---|---|
| [Old Industrial Pipe Pack (PBR) — Fab](https://www.fab.com/listings/e5275b2c-6a12-40ee-bc65-fa636741e174) | 页面明确 Free；SLASH / RENDAR；磨损钢管模块，共用一套 PBR；提供 FBX、glTF、GLB、USDZ | 可补旧支管和三通。优先取 FBX+纹理；本体已具备主排烟管，不必为主体等待下载。 |
| [Industry Props Pack 6 — Fab](https://www.fab.com/listings/b5603e44-e1b0-4346-9c3d-04887aa9f87d) | 页面明确 Free / Permanent Collection；SilverTm；Unreal Engine 格式，工业存储类道具 | 优先补桶、箱和容器；它不是焚化炉设备包。获取时保留 Fab 账户显示的具体许可及下载记录。 |
| [Rusty Pipes FREE — Fab](https://www.fab.com/listings/65d9d308-1b8c-4628-a2c7-d1e9ee7a03d9) | 作者说明免费；扫描旧锈管；8K Diffuse/Normal、4K Roughness/AO；glTF/GLB/USDZ | 少量近景管线候选，不必沿全场复制高分辨率贴图。 |
| [Modular Industrial Pipes 01 — Poly Haven](https://polyhaven.com/a/modular_industrial_pipes_01) | 免费 CC0；含直管、弯头、三通、法兰和带压力表阀门；多种格式、PBR 贴图 | 最建议先取这一套：可直接覆盖支管、阀门和表盘需求。取 2K 或 4K FBX/Blend 完整 ZIP，保留独立模块。 |
| [Power Box 01 — Poly Haven](https://polyhaven.com/a/power_box_01) | 免费 CC0；配电箱，开关与露出的线缆 | 可选备选；本厅观察台已复用项目现有精修配电柜，目前无需下载。 |
| [Korean Fire Extinguisher 01 — Poly Haven](https://polyhaven.com/a/korean_fire_extinguisher_01) | 免费 CC0；灭火器模型 | 入口与观察台楼梯脚各一个；标签语言需后续适配。 |
| [Metal Walkway 014 — ambientCG](https://ambientcg.com/view?id=MetalWalkway014) | 免费 CC0；锈蚀金属走道 PBR，含 1K–8K ZIP | 可作为观察台/踏步表面候选；这是材质，不能替代有厚度和碰撞的楼梯网格。 |
| [Concrete 034 — ambientCG](https://ambientcg.com/view?id=Concrete034) | 免费 CC0；混凝土 PBR | 可补炉区基座或灰渣坑表面，不必全场替换当前已采用地牢材质。 |

Poly Haven 的模型/贴图采用 [CC0 许可](https://polyhaven.com/license)；ambientCG 同样采用 [CC0 许可](https://docs.ambientcg.com/license/)。Fab 免费价格已从具体页面核实，但抓取页没有展开具体许可条款，所以不把“免费”写成 CC0 或可公开再分发原件。下载后请保留原 ZIP、来源页面及许可文件。

不推荐用搜索中出现的 AI 风格化通风机替代本厅写实机械。Poly Haven 的 `Industrial Pipe & Valve 01` 是 HDRI，不是管道模型，已排除出模型清单。

## 给素材的交接方式

将选中的原始 ZIP/项目包放到 `D:/FPS3D/资产/焚化处理厅/`，或告知实际路径。优先给完整 FBX/GLB/Blend + BaseColor、Normal、Roughness、Metallic/AO；带 UDIM 或 ORM 打包时保留说明。专用炉体若只找到整体模型，可保留整体候选，后续按炉口、设备墙和作业带重新适配，不能直接整厅缩放。
