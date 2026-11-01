# M24 FullBodyV3

按用户确认保留原装枪托，重构前部机匣与完整上下护木。参考图的隐藏面采用适配现有 M24 的设计，并非实物工程复刻。

制作源 `author.py`：原枪托连接边界 → 铣削过渡段 → 机匣侧壁与弹匣口 → 开窗机匣套筒 → 完整包覆护木；真实开孔、封闭端壁、倒角、沉头螺钉、侧轨与连续顶轨。枪管、活动枪栓、弹匣、通用握把、瞄具和消音器沿用现有接口。

`factory_front_faces.json` 指定原生前部 1864 个面。`M24ChassisAssetTools::SplitFactoryFront` 仅改当前骨骼资产的材质分区，保留顶点、骨架、权重、UV 与手臂矫正。`M24_FactoryFront` 随先进枪机系统隐藏/恢复，`M24_FactoryChassis` 保持原装枪托可见。原生骨骼不从旧 FBX 重导。

脚架只重做 `SM_M24_Bipod_Base`：横轴、镂空支架、沉入式安装螺钉和贴合垫。原有双腿网格、铰链 `(0,-45,2.2) cm`、手部动作和 0.48 秒展开时序保留。`bipod_fit.py` 按用户要求检查原装/新护木与夹座的实际接触，结果在 `bipod-fit.json`；垫层与宿主有限重合表达压紧接触。

表面沿用武器母材质的独立静态实例，UV0 为 4 cm 物理平铺微法线/粗糙度，UV1 分别烘焙枪身和脚架座的 2K 边缘、凹槽与遮蔽 mask。深色涂层金属、螺钉钢和接触垫独立分区。只更新 M24 的对应图标。

制作次序：`author.py`、`author_bipod.py`、`textures.py`、`bake_masks.py`、`bake_bipod.py`、`author_icons.py`。必要 DLL 构建后通过 `run_assets.ps1` 导入保存，再执行 `publish.py`。`prepare_pipeline.py` 是初次建立脚本，后续不要重复运行以覆盖现行导入逻辑。

交付状态以 `delivery-status.json` 和 `install_receipt.json` 为准。未运行游戏、动作回归或多人验收，由用户实机测试。
