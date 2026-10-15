# 焚化区收集物细节与材质精修 V2

本轮按用户要求逐件检查六件收集物。保持名称、稀有度、占格、出售价值和容器概率；制作源、模型、PBR 与背包图标一起更新。

| 物品 | 发现的问题 | 本轮制作 |
| --- | --- | --- |
| 耐火陶瓷组件 | 光滑白色、圆角过大；压条与夹具关系不清，铭牌被压扁 | 更紧的铸件圆角、颗粒与气孔表面、四块轻微色差；隔热垫、压条、六角螺栓、折弯托架、独立宽铭牌 |
| 密封呼吸滤罐 | 平面标签与圆筒不贴合，盖子信息不足 | 曲面标签、卷边接缝、盖沿、开盖字样和封签线；区分粉末涂层与裸金属 |
| 高温热电偶 | 接头和护线段简略，壳体表面过于一致 | 铸铝壳、锁紧螺母、螺纹段、探杆焊口、护线套及插头分模线／螺丝 |
| 工业过滤芯 | 内侧缺少支撑、铭牌拉伸、端盖收边单薄 | 内支撑笼、滤材灌封边、卷边端盖、牌面铆钉；按真实牌面比例重绘标签，强调滤材纤维 |
| 封存焚化事故档案 | 布面与纸张区分弱，封签像平塑料条 | 布面织纹、沿边缝线、纸张分层色差、暗红织带和蜡印；封面改为记录室卷宗字段 |
| 烟气净化催化芯 | 大圆角孔阵列像杯格，薄壁与钣金关系不足 | 更密的 36×24 直通孔、共享陶瓷薄壁、包边填料、螺栓垫圈、折边接缝与提手焊缝 |

材质采用统一的 4K BaseColor／ORM／Normal 图集；金属、铸铝、粉末涂层、橡胶、滤纸、布、纸和陶瓷分别设置反照率、粗糙度与表面法线。表面噪声先控制频率再取导数，不用高强度噪声或全物件随机锈斑代替材质。标签按实际长宽分别排版。

图标继续共用 `collection_icon_orientation.py`：2×1 水平、1×2 竖直、方形三分之四视角。按实际几何投影居中，透明背景、每格 512 像素。降低过强的补光以显示结构；主体朝向保持一致。

## 制作与保存

入口依次为 `Scripts/setup.py`、`Scripts/prepare_surfaces.py`、Blender `Scripts/author_models.py`、Blender `Scripts/render_icons.py`、`Scripts/import_staged.ps1`、`install_revision.ps1`。初始复制的 `prepare_textures.py` 未用于本修订，现已移入工程 `trash/m66-incineration-retired-20261015/` 对应路径。

可编辑 Blender 分件源在 `Authored`，FBX／GLB 在 `Export`，PBR 在 `Textures`。UE 在独立内容宿主中全新导入，材质／纹理使用 `/Game/Items/IncinerationCollectibles20261015/V2`，六个网格保留原 V1 稳定对象路径，旧背包／共享库存中的路径继续有效。安装前备份正式网格与图标；有项目编辑器加载时不从外部覆盖。

现有玩家物品定义、世界网格路径、图标路径和玩法数据不变，不需要 C++ 改动或 DLL 构建。模型在 UE 导入时完成材质和网格构建及保存。旧版可编辑源仍在父目录，安装前生产文件已归档至工程 `trash/m66-incineration-retired-20261015/SourceAssets/IncinerationCollectibles20261015/VisualRefineV2/Before/Main`。

本轮检查范围为模型与图标外观、输出像素／构图和导入保存，不包含游戏运行或主客机操作。具体发现和实际落盘状态见 `Receipts/visual-review.json`、`Receipts/ue-import.json`、`Receipts/installation.json` 和 `delivery.json`；脚本存在不代表安装完成。
