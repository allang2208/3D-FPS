# 黑色皮革手套 V4：缝制和使用细节收尾

对应用户“继续，把剩下做完”。此前提出的四项优化中，V3 已完成材质分区、柔软腕口及基础接触抛光；本轮完成剩余的针脚嵌入、裁片转角和局部细擦痕。沿用物品 `ue_field_gloves_black`。

## 完成的作者内容

- 手背双道线、裁片内部接缝、腕部束带、织标、掌面补强和指侧针脚都采用有长度的弧形线体，两端设针孔压痕，线槽轻微下陷。
- 线体中央较高、针脚两端沉入表面，相邻针脚高度略有变化。主线距约 2.5 mm，内部与掌面部分约 2.7 mm，织标约 2.0 mm。针孔压痕深度参数约 0.12 mm，线体高度约 0.12–0.17 mm。
- 手背两个裁片转角加入局部叠边和短褶皱；在高模中形成实际起伏，再烘焙至法线和高度图。游戏网格继续保留 V3 的腕口、接触范围和整体轮廓。
- 接缝边缘制作窄幅磨亮，掌心、指腹与指侧加入有限范围的方向性摩擦痕。擦痕同步影响颜色、粗糙度和微高度，不用均匀亮色噪点铺满整只手套。
- 针孔遮蔽、线体、压痕和高度共同来源于缝制参数；手背、掌面与手指各自的作者字段用于高模和贴图制作。
- 延续 V3 皮革、织物和短绒分区，以及背厚内薄的腕口。沿用原骨架和现有动画，保留同一装备 ID 与战斗数值。
- 掉落 FBX、展示源和 320×320 透明装备图标随最终表面一起重做；背包、装备栏和仓库共用同一物品图标。

## 输出与预算

作者目录：`SourceAssets/BlackLeatherDetail20260928/StitchWearV4/`。

UE 目录：`/Game/Characters/ModularOutfit20260924/BlackLeatherStitchWearV4/`。

统一图标：`Content/ColdSteelData/Icons/BlackLeatherStitchWearV4/ue_field_gloves_black.png`。

母版 `.blend` 内保留可编辑高模、原生绑定的游戏网格及作者材质。`Sources/` 来自 V3 已完成的腕口作者源，`Authored/` 为 22 套原生输出。上一版源与资产保留。

游戏成本沿用 V3：双手 25,166、单手 12,583、Body 26,824 三角面，三级 LOD；每组 BaseColor / ORM / Normal / Relief 四张贴图，第一人称 4K、Body 2K，保留 mip 和流送。新增作者图仅在离线烘焙使用，没有新增运行时贴图槽。浅层 POM 的统一 UV、接缝淡出及步进预算保持原值。

制作入口位于 `Tools/ModularOutfit/`：

- `black_leather_stitch_wear.py`：缝制字段与 V3 源续接。
- `build_black_leather_stitch_wear.py`：高模、烘焙、掉落和图标制作。
- `finish_black_leather_stitch_maps.py`、`author_black_leather_stitch_family.py`：图集边界与各原生派生。
- `import_black_leather_stitch_wear.py`：材质、22 套网格及物品引用保存；支持现有编辑器内的短批次接入。

## 接入状态

作者高模、贴图、图标、掉落 FBX 及 22 套原生派生已落盘。首个保存批次因 PIE 正在运行而在写入前停止；随后用户明确授权结束当前运行，已通过现有编辑器互斥桥完成全部七个保存批次，保留编辑器打开。

已保存 22 个骨骼网格、8 张纹理、2 个材质和 1 个掉落网格，共 33 个 UE 资产；现有黑色手套的外观配方、掉落模型/材质、说明及统一图标路径已更新。最终批次返回 `BLACK_LEATHER_DETAIL_PUBLISHED ue_field_gloves_black 22`。

最终保存回执为作者目录 `published.json`，桥输出位于 `Saved/black-leather-stitch-v4-saved-batch-00.txt` 至 `black-leather-stitch-v4-saved-batch-06.txt`。接入脚本在作者目录 `Integration/batch-00.py` 至 `batch-06.py`。资产保存与游戏内效果分别记录。

未进行游戏测试、截图或验收预览。缝线清晰度、实际光照和动作中的穿插表现由用户测试。
