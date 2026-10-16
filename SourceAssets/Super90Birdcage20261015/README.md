# 霰弹枪通用鸟笼消焰器

按用户要求制作并适配 SUPER90。外形为短筒、六组纵向开槽、环形前缘和独立后端连接座；使用真实开口、圆角及加权法线，材质沿用干净深灰金属。仅为游戏可见外观，不包含螺纹或内部机械设计。

## 文件与约定

- `ShotgunBirdcage01_Editable.blend`：可编辑源；主体与接座独立。
- `Exports/SM_ShotgunBirdcage01_LOD0.fbx` / `.glb`：近景游戏网格。
- 同目录 `LOD1` / `LOD2`：远景版本；`SM_ShotgunBirdcage01_Lods.fbx` 为 UE LODGroup 导入件。
- `author_model.py`：建模和导出；`authoring_receipt.json` 记录三个 LOD 的实际三角数与材质配方。
- `author_icon.py`：恢复 `ShotgunIconsFramed20261015/Final` 中当前正式图标；旧简化 Blender 框已被用户否决，旧作者脚本已归档。
- `install_assets.py` / `install.ps1`：保存 UE 网格、材质、平直法线与图标，沿用现有批次互斥。
- `integrate_catalog.py`：只更新 SUPER90 的鸟笼选项，保留收束器和原厂枪口。

Blender 单位为米，+X 朝前、+Z 向上，原点为后端安装基准。SUPER90 使用与收束器相同的实际枪管前端接触位置，沿 `WPN_root` 跟随；枪口特效挂点随新配件长度更新。

## 用户确定的游戏属性

- 后坐力倍率 `0.85`。
- 腰射随机散布倍率 `0.85`。
- 减弱枪口火光与瞬时照明。

普通枪声、AI 听觉范围、枪口烟雾、伤害、弹速和弹丸锥角不变。火光表现走独立系数，不将本配件登记为消音器。与原厂和收束器共享 `muzzle` 槽，沿用既有装备实例存档与网络装备配方。

共享资产目录：`/Game/Weapons/CommonShotgun/Birdcage20261015`。当前已制作安装变换的宿主为 SUPER90；后续其他霰弹枪可复用主体、材质、ID 和图标，再适配其实际安装面。

资产已导入并保存，`install_receipt.json` 的 complete 为 true：三档 LOD 网格、四组材质、平直法线和图标共七个资产。`build_game_receipt.json` 和 `build_editor_receipt.json` 的最终 exitCode 均为 0。

本轮未执行检查、测试、游戏预览或验收渲染；图标是改造栏所需生产资产。未主动打开图形编辑器或游戏，实机效果由用户确认。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90Birdcage20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
