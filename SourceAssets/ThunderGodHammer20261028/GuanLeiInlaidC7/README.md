# 贯雷锤座 C7：嵌银回雷纹与特殊改造

2026-10-29 用户要求：按照此前升级后的建模方式升级贯雷锤座，并调整为特殊改造。

## 模型与材质

沿用用户选定的 `SeatNorseConceptV5/C_InlaidThunder.png` 与 `SeatInlaidC6` 的一体雕槽制作方式，从 `ModulesV1` 原厂中央锤座重新制作。两组折返雷纹在上下肩部相互呼应，银色槽底嵌入本体；不增加外置钢条框架，也不以光滑平板代替原厂锤座。圆徽、原生交叠三角符文、左右锤头连接面、上盖和下方颈部安装面保留。

肩部局部加密、实体雕槽和连续法线过渡；未修改区域保留原厂 UV 与面角法线。源模型 482,852 三角面，密度用于近景锤肩凹槽，沿用本锤 C6 的 Nanite、完整 fallback 和显式切线配置；不将面数或 Nanite 当作性能测试结论。

独立 4096×4096 BaseColor、ORM、Normal 三张贴图。原有纹理信息保留；新增刻纹和嵌银在实际 UV／切线域制作，属于材质高度梯度法线，不冒称高模投射烘焙。Normal 为 OpenGL 约定，UE 使用 Normalmap 压缩、关闭 sRGB、翻转绿色通道；作者法线保留、Mikk 切线在 UE 重建。

## 配方与图标

- 稳定 ID `guan_lei_seat`，武器限定 `ue_thunder_god_hammer`，槽位 `head_mount`。
- `tier` 从 `legendary` 改为 `special`。只更新模型、造型说明和分类，投掷、召回、伤害、动画、最新用户音效均沿用。
- 模型目录 `/Game/Weapons/ThunderGodHammer20261028/GuanLeiInlaidC7`。
- 新灰阶金属框图标使用实际 C7 模型的生产取景和已认可边框母版，经内置 imagegen 制作。实际加载键为 `ue_thunder_god_hammer_head_mount_guan_lei_seat`，源 PNG、提示词和导入回执一并保留。

## 作者源与接入

- `GuanLei_InlaidC7_Editable.blend`：可编辑模型，PBR 贴图打包。
- `Export/`、`Textures/`：FBX 与三张纹理。
- `design.py`、`author_geometry.py`、`author_textures.py`、`finish_source.py`：本次冻结的制作源。
- `import.ps1` / `import_assets.py`：后台导入模型与材质。
- `render_icon_source.py`：只为配套图标制作模型取景，不是额外验收渲染。
- `import_icon.ps1` / `import_icon.py`：保存图标后调用 `publish.py`，仅更新当前贯雷的目录字段，写入前保存旧值并保留其他改造。
- 实际保存及引用切换状态分别见 `import_receipt.json`、`icon_import_receipt.json`、`publication_receipt.json`。

未启动游戏、PIE 或追加视觉／性能验收。资产制作、保存和配置接入不等于游戏测试通过。
