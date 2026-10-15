# 通用战锤柄尾配重 BuildV1

三款：八棱镇击配重 `octagonal_impact`、镂笼灵巧配重 `caged_agility`、双盘平衡配重 `twin_disc_balance`。首个宿主为 `ue_steel_warhammer`，使用 `pommel` 槽。用户最终数值已写入 `catalog.py` 和正式选项目录，见 [当前数值记录](../BalanceV2/README.md)。

## 可编辑制作源

- `CommonHammerPommels_Editable.blend`：三款完整几何、原装接合段与 PBR 材质，作者展示位置沿 X 分开；FBX 在局部安装原点导出。
- `author_pommels.py`、`catalog.py`：可重建几何和作者目录。重建不自动导入 UE。
- `Export/`：三个 FBX；`exports.json`：三角形数、局部范围、材质槽和 UE 安装偏移。
- `read_factory.py`、`factory_geometry.json`：本轮制作采用的原装几何尺寸。
- `Textures/`：1024 像素车纹法线及 ORM。其余金属复用战锤、通用锤头和中央锤座已有材质与贴图。

## 接口与尺度

作者单位为米，+Z 沿柄轴。安装面及 UE 偏移保持 `Z=-8.5 cm`。原装配重顶部 12 mm 的几何、UV 和面角法线保留，从真实下切环过渡到新连接颈。三款总长约 8.75 cm，比原装约 7.50 cm 多出的部分沿柄尾方向延伸；包覆、握点与安装面不移动。

八棱款 9,720 三角形，镂笼款 22,240 三角形，双盘款 23,340 三角形。六根笼肋有实体厚度和封闭端面，窗口真实贯通；双盘由实体短芯固定连接。无新增骨骼、物理摆动或攻击碰撞逻辑。

## 正式改造图标

`render_icon_sources.py` 从最终几何生成 `IconSources/` 透明灰阶素材并保存独立作者场景 `CommonHammerPommels_IconSources.blend`。这些是 UI 资产制作素材，不是游戏验收画面。

`Icons/` 是内置 image_gen 依据实际模型素材和既有框体母版制作的正式金属框图。提示词、来源和生成输出记录在 `icon_generation.json`。共享运行键为 `pommel_<id>`，不为宿主重复生成一套。

## 导入与配置

`import_background.ps1` 在现有资产批次互斥下执行：有 GUI 编辑器时转当前桥；无 GUI 时调用后台 PythonScript commandlet，只保存本轮新包和本轮未发布的部分保存。不会关闭或重启编辑器，不保存共享旧材质。

`import_pommels.py` 保存模型、车纹材质、两张表面纹理和三张 Texture2D 图标后，再运行 `register_pommels.py` 合并 `common-hammer-pommels.json`、`warhammer-modules.json` 及 `warhammer-gunsmith.json` 的柄尾选项。保留原装件及其他槽内容；后续重新制作外观时保留目录中已确定的属性。

正式模型路径：`/Game/Weapons/CommonHammerPommels20261014/BuildV1/SM_CommonHammerPommel_<id>_V1`。正式图标目录：`/Game/ColdSteelData/AttachmentIcons20260913/pommel_<id>`。

模型与图标交付状态以 `import_receipt.json` 和 `commandlet_receipt.json` 为准；它们记录的是赋值前的资产导入批次。当前数值记录在 `../BalanceV2/balance_receipt.json`；新增武技冷却字段的原生构建状态记录在 `../BalanceV2`。未运行游戏、联机、自动测试或验收渲染。
