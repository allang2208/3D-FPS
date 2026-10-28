# 尼泊尔弯刀：各部件三款外观改造

本轮用户授权：每个部件设计三款，能生成设计图就生成，否则直接建模，完成后接入游戏，由用户检查。沿用上一轮“先不设置数值”。

## 当前选项

| 改造栏 | 三款改造 |
|---|---|
| 刀身 | 轻型迅刃、厚背重刃、百炼均衡刃（保留上一批） |
| 握柄 | 棱纹胶柄、缠革握柄、层压木柄 |
| 柄尾 | 包钢柄尾、棱面柄尾、环纹柄尾 |
| 挂绳／挂饰 | 编织短绳、铜环短穗、方牌挂饰 |
| 刀身符文 | 折翼纹、环结纹、三峰纹 |

共 15 款改造，本轮新增 12 款。原装、无挂绳、无附加符文继续保留。全部新选项 `stats={}`、`effects=[]`；符文为静态表面纹样，无发光、触发机制或战斗加成。挂饰为随武器运动的静态模块，未添加新的绳索物理。

使用入口：背包 → 尼泊尔弯刀 → 改造武器。目录在游戏实例初始化时加载；在当前编辑器重新开始一次游戏运行，或正常启动新构建的独立游戏后，再打开改造菜单。没有由制作脚本替用户启动游戏。

## 设计与制作

- `Concepts/` 保存 9 张内置 image_gen 设计图和符印原图，提示词在 `design-prompts.json`，结果在 `concept-receipt.json`。缠革握柄、层压木柄、包钢柄尾三项被图像工具以 violence 拒绝，未重试；按本轮明确授权直接制作三维资产。
- `author_components.py` 使用已接受原装模块的真实接口。握柄保留两端与手部外轮廓，棱纹和皮缝采用浅凹几何及材质细节；金属铆钉保留。柄尾保留连接截面和通孔，侧面增加棱面或浅环纹。
- 编绳保留原装安装段；铜环短穗及方牌保留上端、缩短下段绳体，再增加实际连接环、皮条或带孔方牌。连接偏移仍由原装 `parent_slot: pommel` 配方提供。
- 源 UV 保存在 `SourceUV` 层，新成品使用独立 UV0 图集烘焙 BaseColor、ORM、Normal。握柄为 2048 贴图，柄尾／挂饰为 1024 贴图。UV 变化不移动原装连接面。
- `author_runes.py` 将三张符印按实际刀面坐标烘焙至原装刀身 UV，限制在裸露侧面。已有三款刀身沿用同一 UV 合同，所以三种纹样分别适配四款刀身；不复制整把武器网格。
- `render_icons.py` 以最终模型和符印制作 12 张共享灰阶金属框图标。符文图标只显示符印，不带整刀。图标用的框、材质灰阶转换只存在于图标作者场景。

完整可编辑文件：`Kukri_Components_Editable.blend`、`Kukri_Rune_Icons_Editable.blend`、`Kukri_Component_Icons_Editable.blend`。FBX 在 `Export/`，PBR 和刀面遮罩在 `Textures/`，共享菜单图在 `Icons/`。

## 接入与材质恢复

- 新 UE 目录：`/Game/Weapons/Kukri20261020/ComponentVariants20261026/`。
- 共享选项：`Content/ColdSteelData/shared-knife-component-options.json`，通过现有 `options_library` / `options_column` 读取。刀身继续使用上一轮共享库。
- 各槽的实体网格和原装安装变换合并到 `kukri-modules.json`；没有改写其他武器目录、玩家存档、动作或数值。
- 符文通过 `surface_materials` 对四种刀身的实际材质槽分别绑定。每个刀身也明确登记基础材质，使卸除符文时恢复对应刀身表面，不残留旧纹样。
- `FModuleGeometry` 增加持久材质路径列表，`DescribeKukri` 将它写入现有世界装备材质数组。主手、双持、副手和远端持握读取相同配方；没有新增复制 USTRUCT 字段或逐帧资产加载。
- 旧原装发布脚本和上一轮刀身发布脚本保留后续选项、共享库引用和材质映射，避免重建早期原装件时抹掉本批。

## 本批完成状态

- 模型、材质、遮罩和图标共 **76 个 UE 资产已导入并逐包保存**，见 `import_receipt.json`；本轮目录发布完成，见 `publication_receipt.json`。
- 检测到已有 UE 编辑器，使用现有 MCP 批次锁完成导入和保存，未新开、关闭或重启编辑器。
- 当前编辑器 Live Coding 返回 Success，见 `live-coding-result.txt`。`FPSGAME Win64 Development` 常规构建成功，见 `build-game-console.log`。
- **当前编辑器使用热编译补丁，基础 Editor DLL 未在编辑器占用期间重写。** 以后关闭编辑器后做常规 `FPSGAMEEditor` 构建，才能将该材质描述代码并入基础 Editor DLL；Game 可执行文件已完成常规构建。
- 未运行游戏、联机、截图、性能或视觉验收测试，外观及组合效果由用户检查。

源素材沿用原 Kukri 模型的来源与许可；本批不扩大素材再分发授权。`Before/` 只保存本轮目录修改前副本。

## 全面接入接续

最终标准图标与基础 Editor DLL 的后续完成记录见 [KukriFinalIntegration20261026](../KukriFinalIntegration20261026/README.md)。本段上方的 Live Coding／基础 DLL 状态保留本批当时事实，以新批次回执作为后续完成依据。旧模型／目录发布脚本重跑后，最后执行新批次的图标部署与导入，避免覆盖正式金属框图标。
# 2026-10-26 接入修复补记

九款实体改造件的源 MeshDescription 缺失问题已由 [KukriAssetRepair20261026](../KukriAssetRepair20261026/README.md) 重建并替换正式网格包。当前 `import_components.py` 已接入持久源网格导入合同，禁止在 PIE 中执行制作导入。符文、图标和数值保持原配置；游戏内效果由用户检查。
