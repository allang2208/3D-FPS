# 尼泊尔弯刀模块化 · 2026-10-26

本批将当前 `ue_kukri` 接入五栏改造：刀身、握柄、柄尾、挂绳／挂饰、刀身符文。四个实体原装件；符文仅保留空槽。本批不新增属性加成或新的刀刃、握柄、柄尾造型。挂绳提供原装／无挂绳两个选择，使用已有 `gunsmith_parts` 应用、撤销和保存事务。

## 模型与接口

- 母版：`SourceAssets/Kukri20261020/Kukri_Editable.blend`。Fab powers28 资产及其许可沿用原作者目录；本批不扩大源素材再分发权限。
- 原模型的三个连通体分别为钢刃／贯穿刀茎、木柄、挂绳。钢刃和木柄在握点空间 `Z=-7.5 cm` 同平面切分，柄尾包含下段木柄和内部钢茎。刀柄两侧及铆钉保持一组。
- `+Z` 指向刀尖，`+X` 指向刃口，原点为现有拳心。刀身和握柄保留该原点，柄尾归零到切面，挂绳归零到原装绳环安装端。
- 保留原轮廓、面角法线和原 UV；切割新增的边界插值属性，切口封面采用平面 UV。完整连接环及各件原点记录在 `modules.json`。
- 挂绳配方使用 `parent_slot: pommel`，其局部变换随柄尾变换组合；没有挂绳时不创建该组件，穿孔仍属于柄尾。
- 刀尖／刀根采样元数据沿用 `KukriRhythm`。原有攻击距离、动作时钟、正反握及抛接刀根变换不变。

## 文件与制作入口

| 文件 | 用途 |
|---|---|
| `author_modules.py` | 后台切分、封口和 FBX 导出；不渲染预览 |
| `Kukri_Modules_Editable.blend` | 可编辑原装装配，含隐藏的完整母版 |
| `Export/SM_Kukri_*_Factory.fbx` | 四个原装模块 |
| `modules.json` | 原点、截面连接环、导出路径与三角形数量 |
| `publish_catalog.py` | 发布两份独立目录，只给共享 items.json 的 ue_kukri 增加目录字段 |
| `kukri-modules.json` | 与持握、预览、图标和掉落共用的模块装配配方 |
| `kukri-gunsmith.json` | 五栏、原装选项与无挂绳选项 |
| `import_modules.py` / `import_receipt.json` | 后台导入并逐包保存；复用当前 M_Kukri |
| `render_icon_inputs.py` / `IconInputs/` | 用拆分后的实际模型制作图标源图，不运行游戏或渲染验收图 |
| `Icons/` / `imagegen-prompts.json` | 项目内永久图标母图与内置 image_gen 提示词记录 |
| `deploy_icons.py` / `import_icons.py` | PNG 映射与 Texture2D 实际导入保存 |

图标：刀身和挂绳为基于认可金属框母版及实际部件图的内置 image_gen 产物。握柄和柄尾的生成请求被服务以 violence 类别拒绝，未重试；这两项使用已制作的实际模型灰阶渲染图。空符文及无挂绳复用已有中性拆除图标。这两张实际模型图尚未具有与其余图标相同的生成式金属框。

运行目录：`Content/ColdSteelData/kukri-modules.json`、`kukri-gunsmith.json`；新网格位于 `/Game/Weapons/Kukri20261020/Modules20261026/`。旧存档缺少目录字段时，装配器按 `ue_kukri` 定义回退到此目录，不批量重写存档。

## 接入范围

- 近战改造系统按武器读取五栏，原装恢复与无挂绳使用现有事务；没有向共享剑类栏目追加刀专用槽。
- 主手、双持左手和手枪配副手弯刀分别按各自物品实例请求模块资源。只在实例／物品数据改变时刷新，模块加载异步完成，不重播拔刀。
- 世界持握按同一目录构造现有 `FFPSBodyWeapon.Parts`，涵盖主手、双刀、副手刀和远端人物；保持原握点数据。
- 改造预览、物品图标、地面掉落复用 `ColdSteelModularSword` 的现有装配入口。挂绳隐藏及父部件变换加入该入口。
- 弯刀改造总览使用其自身攻击间隔、基础攻击距离与普通攻击耗体口径，避免显示双手剑格挡等无关行。

未执行游戏、联机、视觉测试或验收。构建结果与资产保存回执分别记录，不以模型导出或资产保存代替运行验收。

## 本批落盘结果

- 四个模块 StaticMesh 与十一项图标 Texture2D 已通过后台 commandlet 导入并保存；分别见 `import_receipt.json` 和 `icon_import_receipt.json`。
- `FPSGAMEEditor Win64 Development` 构建成功（本任务命令，退出码 0）；见 `build-editor-console.log`。
- `FPSGAME Win64 Development` 构建成功；复用本批源码完成后共享工作区已结束的串行构建结果，日志归档为 `build-game-shared.log`，未重复提交 Game 构建。
- 编译记录见 `build_receipt.json`。没有打开 UE 编辑器，没有启动游戏或运行测试／验收。
- 使用入口：背包内选中尼泊尔弯刀，进入“改造武器”。本批可操作项为挂绳原装／拆除；其他栏先提供独立原装件，符文为空槽。

## 后续刀身外观批次

三款可换刀身已由 `../KukriBladeVariants20261026/` 制作并接入：轻型迅刃、厚背重刃、百炼均衡刃。选项与图标按共享资源保存，均无属性／特效加成。此目录的原装发布脚本已保留后续刀身条目与选项库引用，避免重建原装时删除新选项。详见该批 README 和保存回执；运行效果仍由用户测试。

握柄、柄尾、挂绳／挂饰及刀身符文的三款外观现由 `../KukriComponentVariants20261026/` 补齐，五栏合计 15 款。新批次均无数值加成，保留原装与拆除项；制作及编译状态以该批 README、导入和发布回执为准。

正式菜单图标已由 [KukriFinalIntegration20261026](../KukriFinalIntegration20261026/README.md) 接续，含原厂、三款改造、分类和移除状态。此处的旧图与渲染仍是历史制作输入；后续重跑旧发布入口时，最后执行该新批次的图标部署与导入入口。
