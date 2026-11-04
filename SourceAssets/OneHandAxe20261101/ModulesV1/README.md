# 碳钢战斧三槽拆分

本轮按“先拆分并接通用改造”制作。沿用 `ue_tactical_hatchet` 和尼泊尔弯刀动作族；不新增斧头外形、不改通用选项数值。运行时仍使用现有近战改造、装配、物品实例与存档通道。

## 生产内容

- 原装斧头、原装握柄、原装柄尾。斧头包含原斧颈；根槽仍为 `blade_1`。
- 握柄：`knife_grip_checkered` 棱纹胶柄、`knife_grip_leather` 缠革握柄、`knife_grip_laminate` 层压木柄。
- 柄尾：`knife_pommel_steel` 包钢柄尾、`knife_pommel_faceted` 棱面柄尾、`knife_pommel_ringed` 环纹柄尾。
- 六个选项的 ID、文案、数值读取 `shared-knife-component-options.json`，图标直接使用现有共享文件。只为三款原装件新增独立图标母图，分类与原装项共用对应母图。

## 安装契约

源为已修正作者法线的 `../TacticalHatchet_Editable.blend`。保持 42 cm 总长、原拳心坐标、+Z 朝斧头、+X 朝刃口及既有骨骼挂载比例。三段保持原装外表面与手部接触轮廓，只封新增切口。

- 斧头：根坐标原点，切口 Z=11.5 cm。
- 握柄：局部原点在 Z=11.5 cm 接口，装配偏移仅应用一次。
- 柄尾：局部原点在 Z=-7.75 cm 接口，保留原穿绳孔。
- `modules.json` 保存实际接口点环、局部原点、导出路径与三角面数。切口上的 UV 接缝顶点以 0.005 mm 容差局部合并，UV/法线仍按面角保留。
- 三款握柄不改变几何；棱面与环纹柄尾仅在安装端以下局部塑形，保留接口与穿孔。共享改造的外观适配使用战斧自身几何。

原装三件继续使用原 4096 PBR；新握柄为 2048 PBR，柄尾为 1024 PBR。法线为 OpenGL 切线空间，UE 设置绿通道翻转。ORM 为 R=生成的 AO/凹隙项、G=粗糙度、B=金属度；原始 MetalRough 不冒充 AO。原装资产仍使用既有材质。

`author_modules.py` 复用 Kukri 的裁切插值、面角和材质作者函数，所有具体安装端取自本战斧。`TacticalHatchetImportLibrary::FinalizeMesh` 仅扩展允许本武器 `ModulesV1` 目录，继续保留作者法线并生成有效切线。

## 生产入口与交付状态

1. Blender 后台运行 `author_modules.py`：FBX、PBR、可编辑装配和接口记录。
2. `render_icon_inputs.py`：三款实际分件的灰阶图标素材与可编辑出图场景。`icon_prompts.json` / `icon_provenance.json` 记录内置 image_gen 金属框母图来源。
3. `deploy_icons.py`：部署原装/分类 PNG；`import_batch.py`：保存九个网格、六套材质及对应贴图、六个 UI Texture2D。
4. `register_modules.py`：仅更新本战斧两个配置文件，修改前副本在 `Before`。共享选项库与其他武器不重写。
5. 正式 UE `ColdSteelWeaponIconCatalog` 为整斧输出 2×3 透明背包图标。

制作完成不等于游戏验收。最终落盘状态以 `delivery.json`、`import_receipt.json`、`icon_import_receipt.json`、`registration_receipt.json` 为准。本轮不运行游戏、PIE、回归或额外验收渲染，由用户自行测试。
