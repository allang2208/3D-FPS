# RSH 专属大口径消音器

用户先要求参考 ASH 完成模型，随后要求接入游戏。作者模型、贴图、可编辑分件和 FBX / GLB 已完成，UE 模型、材质及专属图标已后台导入保存，枪匠目录和运行源码已接入，包含本次源码的基础 DLL 已构建成功并落盘。

## 外观

- 参考现有 `ASH12TacticalSuppressor20260919` 的粗筒身、八道胶囊形纵槽、斜纹套环和深色前后收边。
- 重建为适合 RSH 的短粗比例，模型艺术比例为长 18 cm、最大外径 5.4 cm；这些是本游戏造型参数，不是现实产品规格。
- 纵槽和套环斜纹为几何，表面微纹由独立贴图表现。没有直接缩放 ASH 成品或将 ASH 安装座套到 RSH 上。
- 后接座依据 RSH 源模型 `3_l` 枪管前端的外轮廓，在原端面贴合后连续过渡到筒身；原点为安装面，+X 朝前、+Z 向上。
- 主体和接座参考本枪已有导轨 PBR 的深色枪钢，套环保留暗钛色分区，前端短凹口使用消光材质。仅制作外观及浅凹口。

## 文件

| 文件 | 用途 |
| --- | --- |
| `RSH12_HeavySuppressor_Editable.blend` | 独立配件母版；包含最终网格、隐藏的 `EDITABLE_Construction` 分件和安装/出口标记，贴图已打包 |
| `RSH12_HeavySuppressor_FitSource.blend` | 同一配件与静态 RSH 参考枪；灰色参考枪不参与导出，也不代表游戏当前材质或动画状态 |
| `Exports/SM_RSH12_HeavySuppressor.fbx` | 单网格游戏导出，43,200 三角面，四个材质槽 |
| `Exports/SM_RSH12_HeavySuppressor.glb` | 同一模型的自包含材质格式，便于后续查看和传递 |
| `Textures/` | Shell / Band / Mount 三组 2K BaseColor、ORM、NormalDX、NormalGL，共 12 张贴图 |
| `author_model.py` | 可复现建模入口；不启动 UE，不包含截图、渲染或测试调用 |
| `authoring.json` | 实际导出记录、分件配方、贴图约定、原端面轮廓及坐标变换 |

四个材质槽：`RSH12Heavy_Shell`、`RSH12Heavy_Band`、`RSH12Heavy_Mount`、`RSH12Heavy_Inner`。最后一个为消光常量材质；其余为独立贴图材质。BaseColor 为 sRGB，ORM 为线性 R=AO、G=Roughness、B=Metallic，UE 使用 NormalDX，Blender 使用 NormalGL，避免重复翻转法线绿通道。

制作单位为米；FBX 负责厘米单位转换。导出枢轴位于 RSH 原枪口实际端面，枪口表现位置为配件局部 `(0.18, 0, 0)` 米。`prepare_integration.py` 将作者记录的 accessory → RSH canonical 矩阵与现用 RSH 握姿注册累计，生成 `RSH12MuzzleAssets.h` 的安装变换；固定挂接 `WPN_root`，静态网格只转换一次单位。

## 专属改造边界

枪匠入口为 `ue_rsh12 → muzzle → rsh12_heavy_suppressor`，显示“RSH 大口径消音器”。保留原厂选项，沿用既有实例改造保存；仅本枪接受该配件 ID。

模型保存于 `/Game/Weapons/RSH12/HeavySuppressor20261004/SM_RSH12_HeavySuppressor`，包含四个材质槽和 MountFace / Muzzle / AimGuide 插槽。三组外部材质采用自身贴图和共享 WeaponSurface 单层淋湿，端口独立消光。源 ORM 派生粗糙度及 WS 通道贴图，不覆盖源图。

专属菜单 PNG 和 Texture2D 已写入实际 `FramedFirearms` 图标目录。单持、双持和法杖副手的消音状态、共同手枪消音声、配件出口与枪口火光抑制已接入源码。数值沿用发布时 ASH 专属消音器：后坐力降低 30%、稳定性提高 30%、弹速降低 20%、开镜耗时增加 10%。

详细接入位置和制作入口见 [接入记录](../../Docs/Weapons/rsh12-heavy-suppressor-20261004.md)。本目录 `import_receipt.json`、`icon_receipt.json`、`catalog_receipt.json` 为已完成的保存记录；`build_receipt.json` 记录已成功编译全部相关源文件的共享工程构建和实际 DLL 落盘时间。本任务尚未开始的重复构建排队已取消。

## 来源与状态

- 造型参考为项目已有 ASH 作者模型及当时用户提供的参考。原参考的权利不因本次制作改变；本轮未下载外部模型，也未改 ASH 资产。
- 配件外观由本轮参数化建模生成。接口使用 RSH 源枪管端面；装配源包含 Medji 的 RSH-12 静态参考几何，沿用 [RSH 署名](../../Docs/ThirdParty/RSH12-Medji-CCBY4.md) 的 CC BY 4.0 记录。作者源及参考仅保留在本机，未发布。
- 后台 Blender 制作和导出已完成，制作日志为 `Author-console.log`。图标采用实际模型灰阶素材和已有边框母版制作；这是游戏 UI 资产，不是验收截图。
- 未启动图形编辑器、游戏或 PIE，未进行外观、听感、存档或回归测试，由用户自行测试。
