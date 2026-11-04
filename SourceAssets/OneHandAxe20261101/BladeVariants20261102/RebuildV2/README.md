> 2026-11-04 整理：被否决的成品与旧导入入口已归档到 `trash/HatchetPublication20261104/`；保留 `author.py`，因为当前 R4/R5 仍直接提取其中的几何函数。诊断与 Review 是失败对照，不能当作当前成品。详见 [归档清单](../../../../Docs/Publication/Hatchet20261104/cleanup-manifest.json)。

> 2026-11-04 材质接续：当前厚背重劈与百炼弧锋的纹理、可编辑源和图标改由 `../OtherBladesFactoryFinish20261104/` 维护。该更新仅处理材质，不恢复本目录的几何生成入口，也不表示原 R2 外形通过验收。钩月当前为 `../CrescentReferenceR4_20261104/`。

> 此版三款模型已被用户否决，不是合格基线。钩月最新重建见 ../CrescentR3/README.md；其余两款尚未在后续轮次重新制作。

# 三款通用斧刃重建 R2 · 2026-11-03

用户否决 V1 的三款扭曲斧刃，要求逐个排查、重新设计并优化。本轮直接制作和检查实际模型，不使用概念图代替模型。

## 排查与处理

V1 对 118,752 三角面的原装网格做非线性形变，继承了原有表面起伏；不同的压窄、扩宽、加强脊线让刃面和过渡区出现不规则高光。R2 只复用实际握柄接口，从独立轮廓重建平整侧面、渐变磨刃和斧颈过渡，重新计算作者法线和 UV，重新烘焙 PBR。

| 选项 | 逐项改动 | 三角面 | 主体厚度 |
| --- | --- | ---: | ---: |
| 轻型钩月 `axe_swift_crescent` | 窄身钩月轮廓、两道真实铣削浅槽、窄磨刃；去除挤压大面 | 7,820 | 14 mm |
| 厚背重劈 `axe_heavy_cleaver` | 宽腹厚背、较直的顶脊、宽楔形磨刃；侧面保持平面 | 7,402 | 24 mm |
| 百炼弧锋 `axe_folded_arc` | 平顺弧形轮廓、中等厚度；钢纹改为低对比细纹，仅作用于基色 | 7,470 | 18 mm |

制作中发现的刃尖楔面相交已通过端点收敛修正；斧颈布尔接缝中的成对反向内部面已移除。斧颈细小阴影折痕采用面积加权作者法线处理。每款分别查看正面、斜面、厚度和无纹理灰模；证据在 `Review/`，不是 UE 实机截图。

`export_diagnosis.json` 记录最终 FBX 重新导入后的检查：三款开放边、非流形边、退化面均为 0，UV／法线为有限数值。实际握柄接合端最大偏差分别为 0.00831／0.00841／0.00831 mm。微小差异来自制作倒角和导出精度，接口原点及 +11.5 cm 分界继续沿用。

## 资产与接入

- 可编辑模型：`<Kind>_Editable.blend`；正式网格／纹理在 `Export/`、`Textures/`。
- 新网格使用 `SM_TacticalHatchet_Head_<Kind>_R2`，同族 `ModulesV1` 目录内新路径，不覆盖被否决的旧网格。
- 三套 2K BaseColor／ORM／Normal；ORM 为 AO=1、粗糙度、金属度。OpenGL 法线只在 UE Texture 上翻绿一次。
- 复用原模块导入函数及 `TacticalHatchetImportLibrary`，保留作者法线、重建切线，启用同族 Nanite；封闭网格材质为单面。
- 共享图标从实际 R2 模型直接渲染，使用三维厚倒角方框、四角铆钉、内环和深灰底板。部件保持安装朝向、灰阶，完整留在内环内；独立作者场景为 `<Kind>_Icon.blend`，不修改游戏材质。
- 正式键仍为 `blade_1_axe_swift_crescent`／`blade_1_axe_heavy_cleaver`／`blade_1_axe_folded_arc`，同步 PNG 和 UE Texture2D，不增加逐武器副本。
- `import_receipt.json` 记录后台 commandlet 实际保存的 18 个资产：3 网格、3 材质、9 PBR 贴图、3 UI 图标。
- `register.py` 只替换模块表中的三款斧刃视觉配方和共享库外观说明；原数值、改造 ID、特殊斧刃、握柄、挂坠、动作和存档字段不变。

## 当前制作入口

1. Blender 后台运行 `author.py -- SwiftCrescent`、`-- HeavyCleaver`、`-- FoldedArc`。
2. 用户要求模型检查时运行 `check_export.py` 和逐款 `render_review.py -- <Kind>`。
3. Blender 后台运行 `render_icons.py`，得到模型对应的三张正式共享图。
4. 在既有 UE 批次互斥下运行 `run_import.ps1`；已有编辑器运行时改用原有互斥桥，不另开竞争进程。
5. Python 运行 `register.py` 发布配方和图标 PNG。

父目录作者、导入、图标制作与登记入口已转到 R2；旧版源码保存在 `Before/LegacyScripts/`，旧部署入口已停用，避免重新安装 V1。历史模型和回执保留，不批量删除。

本轮没有 C++ 修改，不需要原生构建。完成范围为模型排查、实际模型重建、检查渲染、后台资产保存及数据接入；未启动 UE 交互编辑器或游戏，游戏内效果由用户测试。
