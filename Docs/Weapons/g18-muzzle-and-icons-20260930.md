# G18 枪口与图标收尾（2026-09-30）

## 范围

继续完成 G18 的三款通用枪口及装备／改装栏贴图。钛金制退器按用户要求排除，不加入运行时资产或枪匠目录。原有全自动、17／33 发容量和单／双持接入沿用已有实现。

此前保存的扩容弹匣封闭壳体、全息／全景瞄具导轨座，以及镭射／手电前移 25 mm 与同步发射点调整继续使用。对应制作来源分别为 `G18AttachmentRepair20260930` 和 `G18TacticalFit20260930`。

## 枪口

普通消音器、战术消音器、制退器沿用已接受外形，移除旧 M1911 转接段，按 G18 枪管口的实际轴心、外径和开口制作环形转接段。转接段保持贯通，入口略嵌入原枪管端面。

三个部件均显式保存 `MountForward`、`MountUp`、`Muzzle` 挂点。战术消音器现在有独立出口挂点；运行时现有 G18 枪口代码会读取该位置。源几何已经补偿既有装配代码的平移，不额外改动公共 M1911 装配规则。

资产仍为 `/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_suppressor`、`SM_G18_tactical_suppressor`、`SM_G18_brake`。原槽位材质保留，普通消音器的内腔改为原有专用凹腔材质。制作及保存记录：

- `SourceAssets/G18MuzzleFit20260930/author_muzzles.py`
- `SourceAssets/G18MuzzleFit20260930/Exports/*_Editable.blend` 与 FBX
- `SourceAssets/G18MuzzleFit20260930/import_receipt.json`

最初停止前留下的两份钛金候选制作文件未发布到运行时，现已移入 `trash/g18-hk416-publication-20261001/SourceAssets/G18MuzzleFit20260930/Exports/`。当前制作脚本明确只导出上述三款。

## 装备与改装图标

所有图标均为 **1024 × 1024 RGBA 透明 PNG**。

| 用途 | 内容 |
| --- | --- |
| 装备栏基础图 1 张 | 当前 G18 整枪，原始 BaseColor／Metallic／Roughness／Normal 材质 |
| 改装选项 21 张 | 中性灰度，当前配件几何，保留纹理、法线与材质层次 |
| 左栏分类 7 张 | 对应原厂部件或拆除图示，与该类原厂选项一致 |

原厂照门使用原模型完整独立照门；扳机与枪管按原始骨骼权重提取。数值型扳机／枪管选项共用真实原厂部件，不使用整枪缩略图。原厂枪口采用裸枪管单件图。无战术附件选项采用圆环减号拆除图示。握把三种纹理使用游戏中共用的颗粒、菱纹、快速点纹材质，原厂握把保留 G18 原始材质。

扩容弹匣、瞄具、镭射、手电和三款枪口均从当前修复后的制作文件出图。相机按部件实际前向设定，枪口在屏幕左侧、上方为 +Z，不用最长轴猜方向或镜像纹理。

手电旧 Blender 材质中的失效法线路径仅在图标场景中修复为已有 `T_flashlight_Normal.png`；握把法线使用相同 UV0 并匹配其命名。生产场景保存打包纹理，便于后续重制。

- 装备栏 PNG：`Content/ColdSteelData/Icons/ue_g18.png`
- 装备栏 Texture2D：`/Game/ColdSteelData/Icons/ue_g18`
- 改装 PNG：`Content/ColdSteelData/AttachmentIcons20260913/ue_g18_*.png`
- 改装 Texture2D：`/Game/Weapons/G18/Integrated20260929/Icons/ue_g18_*`
- 制作场景、图像与回执：`SourceAssets/G18IconsFinal20260930/{Scenes,Icons,render_receipt.json,import_receipt.json}`

原 `G18Integration20260929/author_icons.py` 入口改为调用本次生产配方；完整导入器支持清单指定的材质绑定，避免三款枪口重导入后失去专用材质。原有动态图标装配入口继续覆盖改装后装备状态。

## 交付边界

本轮只制作与后台导入保存资产，没有新增 C++ 改动。先前原生构建成功状态沿用其原始构建记录。本轮没有启动交互编辑器、运行游戏、额外截图或做实机验收。制作渲染是交付用图标，不是游戏效果验收。游戏内视觉和操作效果由用户测试。
