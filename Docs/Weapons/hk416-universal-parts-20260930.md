# HK416 拆分通用配件

将用户提供 HK416 Full ReWorked 的 EOtech 组件与 Silencer_low 独立整理为两个新选项。原 HK416 的 `holographic`、`true` 选项保留，新选项使用独立 ID。

| 名称 | ID | 属性 |
| --- | --- | --- |
| EOTH全息瞄准镜 | `eoth_holographic` | `ads_percent = -0.05` |
| 多口径消音器 | `multi_caliber_suppressor` | `ads_percent = 0.05`，`bullet_speed_mult = 0.85`，`recoil_mult = 0.8`，`stability_mult = 1.15`，`hip_spread_mult = 0.9` |

遵循项目既定口径：`ads_percent` 直接表示开镜耗时的有符号变化，负数缩短、正数延长。不进行速度倒数换算。名称中的 EOTH 按用户原文保留。

适用目录为当前 13 把枪：M4A1、AKM、QBZ191、M1911、G18、Dan Wesson 715、ASH12、M16A2、A762、SVD、PKM、LMG201、HK416。同 ID 的名称、描述、属性和 effects 完全共用一份作者配方；分别追加至各枪目录，避免未经适配的新枪自动出现实体选项。

## 模型与接口

- 作者源：`SourceAssets/HK416UniversalParts20260930`；正式网格：`/Game/Weapons/CommonHK41620260930/Meshes`。
- EOTH：共用步枪版、HK416 原参考帧版、M16 提把座版、M1911 曲面座版、G18 测量座版、715 固定枪架座版。三款手枪镜体按既有紧凑接口缩至 65%，安装座保留各枪下接触面。
- 消音器：共用枪口版、手枪开放式延长接环版、HK416 原参考帧版。共用网格 +X 向前、+Z 向上；HK416 保留已有组件参考帧。
- 每枪沿用现有挂接骨骼、安装位置、原厂部件显隐和导轨规则。AKM 使用独立现代瞄具桥；PKM 跟随机盖；LMG201 跟随固定机匣导轨；手枪镜跟随套筒、枪口件跟随枪管；715 跟随固定枪架。
- 原始 UV0、金属、粗糙度、法线、玻璃及分划材质保留。合并前将四个 UV 通道按索引统一，保留安装座涂层使用的 UV2/UV3。M16 安装座沿用本枪表面，其余安装座沿用各自材质；原有淋湿材料注册继续生效。
- 瞄具使用 `SightRear`、`SightFront`、`SightUp` 实体标记；消音器使用 `Muzzle`、`AimGuide` 标记。开火、枪口烟火与双持左手复制读取同一出口。
- 运行代码补入消音判定、双持配件复制与长枪口快速近战分支，以及装备图标/掉落配方的资源预载。改造、草稿预览及存档沿用现有配置 ID 流程。

## 图标与来源

共享图标键为 `optic_eoth_holographic` 和 `muzzle_multi_caliber_suppressor`。复用 HK416 同一实物已经制作的灰阶图与 FramedFirearms 金属框图，各自保存 PNG 和 UI Texture2D。没有改动枪体装备栏的原厂目录图；装配后的实例展示沿用已有配方系统。

原作者 **MojoLeeDa**，作品 [HK416 Full ReWorked](https://sketchfab.com/3d-models/hk416-full-reworked-669a9ee17dc44580b53425a08c2f83d0)，原导入记录的许可证为 CC BY 4.0。归因与源包散列保留在 `SourceAssets/HK416Reworked20260930/provenance.json`。本次修改包括拆件、参考帧转换、安装接口和紧凑版适配；不将原模型的许可套用于其他安装座来源。

`authoring.json` 记录导出配方，`catalog_publication.json` 记录属性与适用枪型，`import_receipt.json` 记录实际保存网格和纹理。按用户规则未启动游戏、未执行运行测试或视觉验收。

必要构建遇到系统提交内存不足后采用 `-MaxParallelActions=2`。正式目标的 Unity 合并编译另暴露文件内名称相撞；仅给 `BowAssembly.cpp` 的槽名表/圆柱路径、`CastingToolRackComponent.cpp` 的响应/侧向上限数组、`DungeonWallArt.cpp` 的向量读取函数增加所属模块前缀，数值与逻辑不变。编译产物状态记录在本轮 `build_receipt.json`。

最终状态：9 个静态网格、4 个 UI 纹理已实际保存，13 把枪的 26 个选项已落盘；`FPSGAMEEditor Win64 Development` 正式构建成功，日志 `Saved/BuildEditor/hk416-universal-parts-20260930.log`。没有启动或重启编辑器，也没有运行游戏测试。
