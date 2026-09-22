# 符文长剑：剑根补色、改造预览灯光与统一图标

后续图标修订：剑身Ⅱ最终采用语义图标，参见 [RuneSwordSemanticIcons20260922](../RuneSwordSemanticIcons20260922/README.md)。用户否决的字形主体图标已归档到 `trash/melee-runes-publication-20260922`；本目录实物图仍用于其他部位，剑身Ⅱ以语义图标为准。

## 剑根漏色原因与处理

实际模块在 Z=0.125 m 切分。最靠近护手的原生蓝色字符属于 `SM_RuneSword_Guard_factory` 及对应护手变体，初版仅对独立剑身应用原生遮罩。原始贴图中部分浅笔画的蓝绿差低于初版 0.10 强阈值，也形成小范围漏色。原图、实际面角 UV0 与空间位置共同用于定位，见 `root_diagnosis.json`、`blade_guard_uv.npz` 和 `surface_mapping.npz`。

现在剑身与护手分别使用 `T_RuneSword_NativeMask` 和 `T_RuneSword_GuardNativeMask`。护手选区限定顶部剑根的原生青蓝笔画（Z > 0.06 m、abs(X) < 0.052 m），不处理纹章、两翼、皮革及其他配重装饰。剑根强阈值为 0.055，弱阈值 0.018；非剑根区域沿用初版阈值。保留原形状与原 UV，不重画字形。两张遮罩 B 通道共用真实高度 0.06～0.811727 m，避免流光在模块边界重置。R 为笔画、G 为窄光晕。

运行装配为护手顶部设置独立遮罩 MID；卸下金色改造时恢复该网格默认材质。预览时间同步所有模块。网格、属性、动画、存档和其他符文选项未改。

## 改造栏预览

`M4MeleePreview.cpp` 为符文长剑的独立预览场景加入三盏中性矩形柔光：镜头侧主光、镜头侧补光、侧后轮廓光。保留原始 PBR，天光强度 1.5，局部曝光补偿 +0.35 EV。灯光由现有 FPreviewScene 持有并随预览释放；不修改关卡、全局曝光、双通道透明度或纹理流送路径。

## 图标

已生成并同步 24 张选项图和 5 张分类图，共 29 张。有效选项快照及运行资产映射见 `icon_manifest.json`。当前网格来源为模块源、三款符文配重源及三款共享配重银色装配源；必要 6 mm 安装座随对应配重保留。

- 实物单件、1024×1024 RGBA、透明背景，主体较大投影尺寸占 83%。
- 依据实际安装轴旋转：原生 +Z（剑尖／朝剑身安装端）朝左，原生 +X 朝上，相机 -Y 水平正交，无二维镜像。
- Cycles 48 samples、AgX、统一中性三灯，按物理尺寸归一化。
- 数值剑身改造复用原装剑身实物图；分类图复用该栏原装图。
- 剑身 II 使用现行符文材质的 t=1 s 静帧；金色为原生笔画遮罩。Blender 对 UE 投射法线和水晶透射为近似表现，不能作为 UE 实机材质验收。
- PNG 与 UE Texture 副本均位于 `Content/ColdSteelData/AttachmentIcons20260913`。导入为 UI、sRGB、无 mip。

可编辑源为 `RuneSword_AttachmentIcons.blend`，每个独立外观一组场景，贴图已打包。`icon_render_receipt.json` 记录模型来源、方向和摄影设置，`icon_deploy_receipt.json` 记录 29 个部署资源与 PNG 哈希。`Before`、`baseline.json` 保留本轮替换前文件。`icon_contact_sheet.jpg` 为交付图标排版图，不是游戏截图。

## 重建入口

1. 需要重新读模型时，用 Blender 后台执行 `extract_root_uv.py`，再用 Python 3.11 执行 `map_native_ink.py`。
2. Python 3.11 执行 `bake_root_correction.py`，生成剑身与护手遮罩。原目录 `NativeRuneGold20260922/bake_native_mask.py` 指向同一入口。
3. 经 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 执行 `import_masks.py` 导入两张遮罩。
4. Python 执行 `prepare_icon_materials.py`，Blender 后台执行 `render_icons.py`，输出图标和可编辑场景；`contact_sheet.py` 生成排版图。
5. 经现有桥执行 `deploy_icons.py` 同步 PNG 和 UE Texture。重建／重新部署应另存新的回执，不覆盖本轮历史记录。

## 本轮交付记录

两张遮罩已导入并保存；29 个图标已同步保存。必要的 C++ Live Coding 返回 `Result: Success / Live coding succeeded`，见 `compile-result.txt`。没有启动游戏、运行回归或进行预览窗口视觉验收，游戏内漏色及灯光最终效果由用户测试。重新打开改造栏可加载新预览场景和图标。
