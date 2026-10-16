# 通用霰弹枪收束器：方形外壳方案 01

按用户提供的参考照片使用 Blender 后台精确建模，保留平直长侧面、大顶部圆角、偏上的前端开口及克制的分段缝。随后按用户要求接入 SUPER90 枪口改造，弹丸散布倍率为 0.65。

## 文件

- `ShotgunChoke_Box01_Editable.blend`：可编辑源，主体、后端座、前端饰钉独立；包含 UV0、PBR 材质、加权法线与安装基准。
- `Exports/SM_ShotgunChoke_Box01_LOD0.fbx` / `.glb`：近景模型。
- `Exports/SM_ShotgunChoke_Box01_LOD1.fbx` / `.glb`、`LOD2`：按同一轮廓减少圆弧采样的远景版本。
- `Reference/user_shape_reference.png`：用户本轮参考原图；图片来源及再分发许可未提供，仅作为本地制作参考。
- `author_model.py`：完整建模及导出入口。
- `authoring_receipt.json`：实际导出路径、几何数量、材质参数与源枪口挂点信息。
- 当前正式图标来自 `../ShotgunIconsFramed20261015/Final/muzzle_shotgun_choke.png`，使用实际模型单件图和工作流认可的金属框母版，经内置 imagegen 重制；`author_icon.py` 恢复这张最终图。旧简化框和旧图标场景只作为制作历史。

## 模型约定

主体为游戏外观网格，前端开口使用浅的暗色视觉凹腔；没有内部机械结构。单张照片未展示的后端座属于本次美术设计。

Blender 单位为米，+X 朝前、+Z 向上；原点为后端安装基准。主体和后端连接座分开编辑，后续其他霰弹枪可复用主体、单独适配连接座。初始建模回执保留源枪口骨骼信息；最终 SUPER90 安装位置使用当前上方枪管的实际前端圆环，转回 WPN_root 局部坐标，不沿用偏低的旧枪口标记。

大面保持平面，圆角和接缝使用几何；先设置平滑与硬边，再生成加权法线。材质为深灰金属的 PBR 常量，连接座参考现有 SUPER90 枪管的色调与粗糙度；没有噪声凹凸、伪造磨损或默认法线图。GLB 自带材质参数，FBX 导入 UE 时需按对应槽重建/绑定材质。

## 状态

已后台导入并保存共享网格、三档 LOD、五组 WS1 材质、平直法线与图标；已接入 SUPER90 枪口改造。目录、装卸、保存配方、世界挂件、枪口特效、弹丸散布与 UI 数值路径已接上。

`install_receipt.json` 的 complete 为 true；Game 与 Editor 常规构建最终均返回 0。早期 Game 构建受另一处 HeQueNetAudit 生成代码错误阻断，在对应源码更新后重试成功。后台导入已修正 commandlet 渲染配置，并避免访问不可用的 LevelEditor 播放状态。

未主动打开图形编辑器或运行游戏，未执行视觉、联机、回归测试。仅制作了改造栏所需图标，没有生成验收预览。造型及实机效果由用户确认。

完整接入说明：`Docs/Weapons/shotgun-choke-integration-20261015.md`。

后台重建：使用 Blender 5.1 的 `--background --python author_model.py`。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90Choke20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
