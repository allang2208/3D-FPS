# 符文长剑：原生符文金色强化

2026-09-22。用户授权按原生符文遮罩、UV 对位和金色材质方案调整。

## 当前入口

- 物品仍为 `ue_rune_sword`；改造仍为 `gunsmith_parts.blade_2 = golden_glow_rune`。
- UE 目录：`/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922`。
- 专用材质实例：`MI_AzureRunesword_NativeGold`；母材质：`M_AzureRunesword_NativeGold`。
- 使用独立剑刃原 UV0。金色分支不再调用共鸣圆环投射纹样。
- 原装剑刃/护手/握把/配重网格、骨架、动画及攻击命中减冷却属性未改。
- 其他剑和其他符文选项沿用原来的表现。

## 护手根部修订

当前版本已补上属于护手网格的剑根原生字符，并修正剑根浅色笔画。使用剑身、护手两张独立 UV0 遮罩，共用从 0.06 m 到 0.811727 m 的长度进度；护手纹章与其他装饰不纳入金色选区。当前制作与重建步骤见 [RuneSwordVisualPolish20260922](../RuneSwordVisualPolish20260922/README.md)。`bake_native_mask.py` 已转到该版本入口；以下步骤仅保留初版制作记录。

## 初版制作源与恢复顺序

1. Blender 后台执行 `export_blade_uv.py`，读取现行拆分剑刃的作者 FBX，导出面角 UV0、位置与三角形数据到 `blade_uv_source.npz`。不改源 FBX、不重导网格。
2. Python 3.11（numpy、Pillow、scipy）执行 `bake_native_mask.py`。用实际剑刃 UV 三角形限定原始颜色贴图中的蓝色笔画，强/弱阈值连通提取边缘，制作 2048×2048 遮罩。
3. 如需局部修笔，`include.png` / `exclude.png` 为与原图同尺寸的灰度编辑层。当前未人工逐字重画，保持源笔画身份。不可用新生成符号代替原字符。
4. 经 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 执行 `install_material.py`。首次导入遮罩；后续只续作/更新材质。若重新烘焙了 PNG，需先在 UE 对本任务遮罩重导，再执行材质更新。
5. 原生逻辑在 `Source/FPSGAME/Weapons/MeleeRuneVisual.cpp`，装配外观键在 `ModularSwordVisual.cpp`。完成必要的原生编译后生效。

遮罩是着色数据：R=原生符文字形，G=紧邻笔画的微弱光晕，B=按实际剑刃位置烘焙的根到尖进度。B 不使用碎片化 UV 的纵坐标。UV 岛外延 3 像素用于接缝过滤。

## 材质与切换

专用母材质复制当前 `M_AzureRunesword`，保留其法线、金属度、粗糙度及其他 PBR 连接；仅在原生笔画遮罩内混合暖金底色并替换原发光。原材质和网格默认材质绑定不修改。

金色选项为剑刃创建独立 MID，同时移除旧共鸣投射层。卸下或选择其他符文时，从实际网格资产恢复原材质，再按原流程应用其他选项。不会修改共享材质的全局参数。

手持、改造草稿/应用/取消、物品预览与世界掉落继续复用既有装配入口。外观键加入此版本标识，使已经装配的金色剑也会在下一次刷新时重装材质。预览时间继续通过 `ColdSteelMeleeRune::UpdatePose` 传入。

默认参数：金色底色 linear `(0.58, 0.285, 0.052)`，发光 linear `(1.0, 0.49, 0.10)`，亮度 `0.75`，呼吸幅度 `0.055`，流光增量 `0.24`；光带约 6.25 秒从根到尖运行一轮。设 `BreathStrength=0`、`FlowStrength=0` 即为静态金色版本。曝光补偿只作用于新增发光。

## 交付边界

`install_receipt.json` 记录资产保存与材质编译结果。`compile-result-02.txt` 返回 `Result: Success / Live coding succeeded`，本次原生改动已通过 Live Coding 接入当前编辑器；未关闭编辑器或重建常规基础 DLL。第一次编译的静态网格指针类型推导错误已修正。未运行游戏测试、截图、渲染预览或验收，效果由用户测试。

模型和原贴图来源继续沿用原 Meshy 资产；本目录的密集几何数据及衍生遮罩保留本机，不因本次制作新增公开再分发许可。
