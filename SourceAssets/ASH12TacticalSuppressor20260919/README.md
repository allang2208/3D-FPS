# ASH 战术消音器

按用户提供的截图制作，作为 ASH-12 独占枪口配件。主体为大直径凹槽筒身、宽斜纹套环及深色后接座。不可见面为本次造型补全，不宣称对截图对象的精确重建。

## 作者资产

- `Reference/user_suppressor.png`：用户提供的造型参考；截图权利不因建模改变，不用于公开素材再分发。
- `author_model.py`：参数化外观模型和贴图作者入口。
- `ASH12_TacticalSuppressor_Editable.blend`：可编辑分件、最终网格、材质和图标场景。
- `SM_ASH12_TacticalSuppressor.fbx`：单个游戏配件网格，53,760 三角面、四个材质区。
- `Textures/`：三组 2K BaseColor、ORM、DirectX 法线，以及供 Blender 使用的 OpenGL 法线。
- `ue_ash12_muzzle_ash12_tactical_suppressor.png`：实际模型生成的透明 1024×1024 配件图标，前端向左。
- `import_assets.py` / `import.json`：UE 制作与导入入口、实际材料绑定和保存回执。

按游戏比例制作，长度为 26 cm、最大外径为 8.2 cm。源对象 +X 指向枪口，+Z 为上方，后安装端面为 x=0；运行装配沿用当前 ASH 原厂枪口端面的骨骼基准。模型只包含外观结构和短暗色端口凹面。

材质分为 Shell、Band、Mount、Inner；主体涂层匹配 ASH 当前枪体的深灰表面，套环采用参考图的暖色金属分区。纵槽及套环纹路使用真实几何，细微表面纹理使用独立 PBR 贴图；没有将枪体 UV 图集直接贴到新网格上。可编辑分件保存在 `EditableConstruction` 集合。

## 游戏接入

- 独立选项 ID：`ash12_tactical_suppressor`，仅登记在 `ue_ash12` 的 `muzzle` 槽。
- 运行网格：`/Game/Weapons/ASH12/TacticalSuppressor20260919/SM_ASH12_TacticalSuppressor`。
- 使用现有枪匠的预览、应用、实例存档、拆卸恢复、掉落及武器图标装配入口；运行层也限制该 ID 只能用于 ASH。
- 与现有战术消音器使用同一组游戏数值：后坐力 ×0.75、稳定性 ×1.25、弹速 ×0.8、开镜耗时 +5%。外观变大没有另加未经要求的性能增益。
- 消音状态纳入现有音效和火光抑制逻辑；枪口表现位置显式使用本件 +X 轴和 26 cm 前端位置。
- 三组外部材质对应的湿润／水珠版本已合并到 ASH 私有天气表，暗色端口不加水珠。
- 打包目录和武器专属 PNG/Texture 图标已接入。

## 状态

模型、贴图、图标及 UE 资产已制作并保存；目录及 C++ 接入已修改。编辑器关闭后已执行普通 Editor 模块构建，结果为 `Succeeded`（目标已是最新状态，无需重新编译）。构建日志：`Saved/BuildEditor/build-20260919-204405.log`。按用户规则未进行实机测试、截图或验收渲染；图标渲染仅用于交付产品 UI 资产。
