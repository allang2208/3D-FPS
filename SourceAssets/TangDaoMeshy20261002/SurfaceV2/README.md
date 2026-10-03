# 唐刀表面精修 V2

2026-10-02，按用户授权制作，并同步改造件。属于第一轮材质与微表面精修；没有进行第二轮轮廓、雕刻几何或拓扑改造。

## 本轮制作

- 在实际适配后的整刀 UV0 上烘焙局部位置和几何法线，生成钢、金色金属、缠柄和棱边分区。分区由真实握柄区域和原始 PBR 分类共同确定。
- 清洁裸钢和金色金属按金属度 1、缠柄按 0 制作；边界保留过滤过渡。保留原有黑红配色和龙纹。
- 钢刀面使用缎面粗糙度，几何棱边更光滑；刀根雕纹保留原色变化。宽刀面适度减弱原基色中的低频明暗条带，不整体抹平雕刻区域。
- 按拟合后模型的米制位置生成 0.45 mm 间距的细研磨纹，以及 1.2 mm 间距、0.012 mm 高度的缠柄交织纹理。细法线叠加在完整原始结构法线上再烘焙，原始 AO 独立保留。
- 新图集为 4096×4096。新的微表面细节按此分辨率制作；原始 2K 颜色和结构法线仍是输入，没有把上采样称为新增雕刻细节。
- 主材质明确接到 UE Substrate Front Material，同时保留传统 PBR 输出；静态/Nanite 用途，不使用手臂骨骼材质用途。

## 同步范围

四个原装部件、三款刀刃、三款护手、三款握柄共用同一精修图集，保持原 UV0、安装截面、源几何与原法线。
两类柄尾转接件使用同色系的金色金属材质；六款共用柄尾增加专用 `tang_dao_surface_v2` 外观。
符文来源的柄尾保留其独立法线、纹理和发光；寒晶来源的柄尾仅对金属槽增加私有副本，保留水晶和银色镶嵌槽。

剑身Ⅱ符文使用半透明覆盖层；唐刀四款刀刃使用普通静态网格渲染，保留精细网格和 4K 材质。2026-10-02 已修正表面升级后 Nanite 导致覆盖层消失的问题，资产保存回执见 [符文覆盖层修复](RuneRepair20261002/README.md)。
其他武器仍使用各自的原外观，原装/改造 ID、数值、动画和存档合同保持当前配置。

运行材料覆盖写入 `Content/ColdSteelData/tang-dao-modules.json`，覆盖持握、改造台、库存预览和世界模块装配入口。
另存一份使用精修材质的整刀网格作世界显示回退，几何仍来自当前整刀。新增旋风材质与映射同步保存。
持握根使用前一轮用户要求的 +Z 180° 朝向，本轮合并目录保留其当前值。

## 图标与性能

彩色库存图按精修材质重新制作，384×768，并使用独立 `ue_tang_dao_surface_v2` PNG/Texture2D。
2026-10-02 后续按背包规则改为读取实际 UE 原厂模块与游戏材质出图；旧 Blender 库存入口已转接，两个现有库存纹理均重新导入。制作与落盘记录见 [背包图标规则同步](../InventoryIconRules20261002/README.md)。
现有灰阶金属框改造图继续描述同一造型，本轮没有重新生成 AI 边框母图。
主材质仍只采样 BaseColor、ORM、Normal 三张图；13 个原装/变体复用一套图集。PBR 纹理保持 mip 和流送，未改项目纹理池或照明配置。

## 制作与接入入口

1. Blender 后台运行 `bake_coordinates.py`。
2. 项目 Python 运行 `author_maps.py`。
3. Blender 后台运行 `bake_finish.py`，保存 `TangDao_SurfaceV2_Editable.blend` 和新切线法线。
4. UE 无界面 PythonScript commandlet 运行 `import_surface.py`，实际保存资产并合并目录。
5. Blender 后台运行上一层 `render_production_icons.py -- --inventory-only`。
6. UE 无界面 PythonScript commandlet 运行 `import_inventory.py`，保存正式库存 Texture2D 和物品图标入口。

新 UE 资产位于 `/Game/Weapons/TangDao20261002/SurfaceV2`；源贴图位于 `Textures/`，工艺参数为 `surface_recipe.json`。
安装覆盖为 `bindings.json`，原运行目录备份为 `Before/`。上一层 `install_catalog.py` 与图标制作入口同步复用精修版本。

材质/网格保存回执为 `import_receipt.json`，本轮成功保存日志为 `import-commandlet-resume.log`。
正式库存图保存回执为 `inventory_import_receipt.json`，日志为 `inventory-commandlet.log`。
没有 C++ 修改，无需原生编译；没有主动打开编辑器、启动游戏、截图或验收测试。效果交由用户测试，重新进入游玩后读取新目录。

后续用户报告剑身Ⅱ符文缺失，关闭 Nanite 后仍未恢复。继续排查与专用刀身表面发光修复见 [RuneRepairFollowup20261002](RuneRepairFollowup20261002/README.md)。该后续修复包含 C++ 和 Editor／Game 构建，刀刃绑定 `M_TangDaoBladeRuneSurface`，保留本目录原 PBR 纹理；`import_surface.py` 同步执行专用材质入口。
