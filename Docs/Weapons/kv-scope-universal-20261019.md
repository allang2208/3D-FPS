# KV 原包瞄准镜通用改造

## 来源与型号

来自用户选定的 [Chukavin Sniper Rifle 模型包](https://sketchfab.com/3d-models/chukavin-sniper-rifle-b3bb922bdf1a481a96b9e2940b2d26fc)，本地原生文件名为 `KV Inhibitor.blend`，瞄具对象为 `other\sight_scope.smd`。源包记录为 MWIII KV Inhibitor，不能把展示页标题当作准确现实型号。保留原来源／许可证；没有发布或再分发源包。

包内没有明确的瞄准镜型号字符串。贴图有俄文高低／风偏调节标识和风格化厂标，无法可靠读取型号。现实 SVCH 曾配 1П88（改进型 Hyperon），依据：[《卡拉什尼科夫》杂志 2023-10-07 报道](https://www.kalashnikov.ru/kontsern-kalashnikov-podtverdil-kachestvo-serijnyh-vintovok-svch/)。这只能支持候选方向，不能证明游戏源模型就是某个 1П88 子型号。因此正式配件使用中性名称「KV 战术瞄准镜」，不标注未经确认的厂家或子型号。

## 实现

- 配件 ID：`optic / kv_scope_4x`（保留原 ID 兼容已安装配件与图标）。按用户后续要求，游戏配置为 1×／2×／4× 三档切换、枪械稳定性 ×1.05，保留开镜耗时 +10%。这不是源镜真实规格声明。
- 沿用现有中心十字分划、主相机倍率及镜内显示流程。原包没有可用分划图；顶部／侧面调节鼓不冒充变倍环。
- 适配现有支持 LPVO 的 15 个枪型：M4A1、AKM、QBZ191、RSH12、ASH12、M16A2、A762、SVD、PKM、LMG201、HK416、Super90、M870、SVCH、Saiga12K。短手枪的限制保留。
- 原镜主体 34,146 三角形，保留拓扑、UV、法线和源基色／法线贴图。实体长度约 24 cm；这是源包按当前枪体比例注册后的尺寸，不代表现实产品尺寸。
- 共同坐标 +X 朝前、+Z 朝上，以原枪导轨顶面为 Z=0，前后镜片中心生成 `SightRear / SightFront / SightUp`，ADS 读实际插槽。
- Common 主体共享；HK416 沿原有组件空间导出，M16 保留提把桥与锁定鞋，ASH12 补齐两只脚下的导轨承接。
- RSH12、M870、Saiga12K 的窄轨用独立 120 mm 上轨座，上轨高 8 mm；下夹爪沿用各宿主已测轮廓。Super90 使用自身轮廓的转接座。镜身平移 -29.75 mm 使两脚跨距位于短轨中心，未缩放镜身。
- AKM／SVD 保留原桥的生命周期；PKM 保留 `PKM_Cover` 父骨骼；LMG201 仍在固定根轨。高倍显示与枪口特效补偿包含新 ID。
- 共用金属框灰阶图标：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/optic_kv_scope_4x.png`。内置 ImageGen 使用真实侧视源与认可金属框母版制作；提示与输入记录在作者目录。
- SVCH 默认仍为机械瞄具；本次没有改枪体、V9 手模、动画、换弹／左手拉栓、弹匣修复。

## 制作和落盘

作者目录：`SourceAssets/SVCHScopeUniversal20261019`。

- `prepare_source.py`：提取原镜与坐标注册。
- `author_fittings.py`、`KVScope_Fittings_Editable.blend`：原镜、安装座与图标素材。
- `publish_catalog.py`：局部插入目录，保留其他选项。
- `install_assets.py`：导入新材质、静态网格、插槽和图标，逐项保存。
- `run_finish.ps1`：现有 UE 批次互斥下构建 Editor DLL 和无界面导入。
- 构建、资产保存结果分别以 `build_receipt.json`、`assets_receipt.json` 为准。

按用户规则不启动游戏、不追加实机或跨枪验收，由用户测试。

## 本次交付状态

2026-10-19 14:10:57（北京时间），`FPSGAMEEditor Win64 Development` 后台构建成功。14:35:59，无界面导入完成，14 项新资产全部保存（7 网格、4 材质、2 贴图、1 图标），见 `assets_receipt.json` 与 `import_resume_receipt.json`。

首轮导入的 Blender `.001` 名称后缀及 commandlet 缺少编辑器子系统问题已在制作脚本中修正。导入保留源法线，使用内置切线生成；没有为此启动编辑器。历史失败日志保留，最终状态以上述完成回执为准。

图标由内置 ImageGen 制作，完整提示保存在 `SourceAssets/SVCHScopeUniversal20261019/icon_generation.json`，最终 PNG 为 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/optic_kv_scope_4x.png`。没有进行游戏内、跨枪装配或射击测试。

## 后续调整：1／2／4 倍与稳定性

首次安装默认 1×。开镜时滚轮向上依次 1→2→4，向下 4→2→1，端点保持；同一配件的配置刷新不重置当前档位。HUD 显示当前倍率与滚轮提示，总览显示 `1/2/4×`。镜身调节鼓保留原静态外观。

15 个兼容枪型的同 ID 选项均加入 `stability_mult: 1.05`，复用现有稳定性评分计算，物品效果文案同步为「枪械稳定性提高5%」。作者目录：`SourceAssets/SVCHScopeUniversal20261019/Zoom124`；构建状态以该目录本轮回执为准，本次不重复导入模型和图标、不进行实机测试。

本轮源码与目录已保存。用户关闭编辑器后，2026-10-19 15:41:18（北京时间）执行 `FPSGAMEEditor Win64 Development` 基础构建，结果为 `Succeeded`，目标已是最新；以 `Zoom124/build_receipt.json` 为本轮完成回执。早前 Live Coding 未启动和并行模块编译失败的日志仅保留为历史记录，不代表最终状态。本轮没有启动游戏或执行实机测试。
