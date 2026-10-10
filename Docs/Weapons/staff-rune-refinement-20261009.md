# 法杖符文细化（2026-10-09）

用户要求参照剑类符文，升级法杖上粗糙的符文表现。本轮处理鹰眼、暴击、风暴三个 `shaft_rune` 选项；替换原来等距重复三次的粗线条模型，保持改造 ID、效果数值、存档、图标、其他部件及装配代码。

## 设计依据与结果

参考高地双手剑 `WildRuneTotemV2_20260922` 的完整非平铺构图，以及 `MeleeRuneFade20260922/native_gold_fade.hlsl` 的金属底纹、沿长度错相呼吸、首尾渐隐流光。采用法杖自己的三个主题，不复制剑的兽颚纹样。

| 符文 | 主印 | 向下衔接与收束 |
| --- | --- | --- |
| 鹰眼 | 眼印、狭长瞳孔和羽刃 | 不等长羽纹、开放弧线、细尖尾纹 |
| 暴击 | 裂击菱印和锐利冲击刻痕 | 斜切笔画、断刃楔纹、分叉尖端 |
| 风暴 | 涡眼与雷电核心 | 两处不同大小的风旋、连续雷纹、细叉尾纹 |

三套黑白源图用内置 imagegen 分别制作，原始像素保持不变；黑白是材质覆盖数据，不是游戏中的显示颜色。保留已安装 `M_Staff_RuneV2` 的暖铜色基准 `(0.68,0.34,0.08)`，不执行之前已取消的全符文改黄要求。

源图与完整提示词在：

- `SourceAssets/ApprenticeStaff20260927/RuneRefinement20261009/Art/T_StaffRune_eagle_eye_rune.png`
- 同目录 `T_StaffRune_crit_rune.png`、`T_StaffRune_storm_rune.png`
- `SourceAssets/ApprenticeStaff20260927/RuneRefinement20261009/prompts.json`

## 贴合与材质

从当前杖身作者源 `BarkRebuildV21/Staff_NaturalBark_V21.blend` 的实际树皮三角面裁出四条表面，不使用名义圆柱或平面替代树皮。符文位于原有四个朝向，局部 Z 为 43.2–56.8 cm，角宽为每侧 0.44 弧度；对角线仍留给导魔线。表面径向偏移 0.014 cm，用于分离深度，不改木杆本体。

每个符文是四条裁切表面合并成的一个网格，共 3,920 三角面、一个材质槽。材质为单面 Masked / Default Lit：黑底完全裁掉，仅保留原图笔画；不是包围法杖的可见底板，也不增加半透明光晕层。

材质通过五次局部采样生成笔画覆盖、边缘细法线和粗糙度变化。木纹的大起伏来自原树皮几何，细刻纹来自着色法线，未声称对木杆执行了实体挖槽。原图磨痕保留为镶嵌表面的层次；金属底纹持续可见，发光按长度错相缓慢呼吸，并以首尾归零的时间包络向上流动。RGB 按统一比例限制峰值，避免裁白。无新增 Tick、光源、Niagara 或玩法逻辑。

非二次幂源图由 UE 构建时 StretchToPowerOfTwo；关闭 sRGB，灰度压缩，保留 mip 和流送，最大边 2048。`Export/artwork.json` 记录原图尺寸与实际非黑像素取景矩形；Blender/FBX 的 V 翻转在材质坐标中处理。可编辑源包含打包原图和按实际表面分组的网格。

## 接入与恢复

- 可编辑源：`SourceAssets/ApprenticeStaff20260927/RuneRefinement20261009/Staff_EngravedRunes.blend`。
- 制作入口：同目录 `author_blender.py`；导出 `Export/meshes.json` 和三个 FBX。
- 材质配方：`rune_field.hlsl`、`rune_glow.hlsl`、`install_ue.py`。
- 新资产目录：`/Game/Weapons/ApprenticeStaff20260927/RuneRefinement20261009`。
- 正式引用保持 `/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_shaft_rune_<ID>`。
- 旧正式网格及 V21 对应网格分别保存在新资产目录 `Before/Runtime`、`Before/AuthorSource`，磁盘原包保存在作者目录 `Before/Content`。

三个正式网格、三个 V21 对应网格、三个版本网格、三个材质和三张纹理已通过当前编辑器的批次互斥桥保存。`install-receipt.json` complete 为 true，三个材质的必要编译均无错误。首次接入遇到 PIE，在写资产前停止；用户回复已退出后完成接入。

`BarkRebuildV21/import_model.py` 在本轮回执 complete 后使用新符文导出与材质，避免整杖重导恢复粗线条。水晶和杖冠的独立版本分支保留。

恢复时在编辑器内把备份网格的几何、材质复制回原引用并保存；编辑器完全关闭时也可按原相对路径恢复 `Before/Content`。同时将本轮回执 complete 设为 false，避免重导重新应用。不要在编辑器加载目标包时覆盖磁盘文件。

本轮没有启动游戏、截图、预览渲染或自测；编译与保存属于制作步骤，实际观感由用户体验。源图不是游戏实机预览。
