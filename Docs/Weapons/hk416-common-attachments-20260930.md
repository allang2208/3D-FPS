# HK416 通用改造件接入（2026-09-30）

本轮承接 HK416 的 EOTH 全息瞄准镜、多口径消音器，扩充同一把枪的现有通用配件。钛金制退器按用户此前要求不添加。其他枪的数据不在本轮修改范围。

## 内容

| 槽位 | 新增选项 |
| --- | --- |
| 瞄具 | 全景薄框红点、紧凑型二倍棱镜、1–6×低倍可变瞄准镜 |
| 枪口 | 战术消音器、枪口制退器 |
| 前握把 | 45°侧倾握把、战术垂直握把、棱镜阻手器、共振二代前握把 |
| 枪托 | 骨架枪托、镂空轻型枪托、高性能后托、战术伸缩枪托 |
| 后握把 | 幻影后握把、稳固防滑后握、均衡后握把 |
| 弹匣 | 扩容弹匣、大弹鼓 |

共 18 个新增改造选项；新增枪托、后握把、弹匣三个槽及原装选项。所有同名通用选项从当前 M4 目录复制，保留既有 stats、effects、说明和 ID。保留当前 HK416 基础数值和原有配件。

## 制作与接入

- 枪托、后握把、原厂枪口按实际网格分配独立材质分区；替换时隐藏对应分区，拆除时恢复。枪管、机匣、机械骨骼和原始 UV 保留。
- 通用部件保留尺寸与原 UV0；按 HK416 的导轨、枪口轴、枪托接口、握把颈部制作连接几何。瞄具使用独立 SightRear / SightFront / SightUp；LPVO 变倍环使用自身轴向的 ZoomRing 挂点。
- 扩容弹匣保留上半部、供弹口和抓握区，以原始完整表面片段沿测得的中心曲线延长约 49.47 mm，原底盖整体移动。拼接处保留原表面纹路和 UV；闭合下半部残留切口。
- 弹鼓保留现有主体和手部接触，使用 HK416 原装供弹口、卡榫段和封闭连接圈。两种替换弹匣挂在原弹匣骨骼上；弹鼓沿用抛弃与取新弹鼓状态流程。
- 三种新增前握把动作分支与弹鼓支撑分支使用现有成组手型及完整腕臂链；HK416 原有机械轨道与动作尾段接续。新增 56 段动作，包括普通/空仓换弹、装配、检视、奔跑与快速近战；RVG 原有动作保留并补入弹鼓换弹组合。
- 金属区域采用本枪机匣的无文字 PBR 样本及物理 UV3；保留原 UV0 的结构法线、标记、非金属和光学区域。材质以静态配件用途保存，接入当前淋湿材质库。
- 枪匠模型、倍率调节、枪口特效位置、消音声、装备栏配方异步资源、背包和存档复用现有接入合同。
- 5 张专用图标使用本轮真实模型轮廓和认可的金属方框母图，通过内置 imagegen 生成；另派生 3 张分类图。图片与 Texture2D 同时覆盖根目录和 FramedFirearms 正式查找路径。其余通用件复用既有标准图标。

## 可重建来源

作者目录：`SourceAssets/HK416CommonAttachments20260930`。

制作顺序：`author_models.py` → `author_magazine.py` → `author_drum.py` → `author_coating.py` → `author_animations.py` → `author_icons.py`。`icon_generation.json` 记录内置 imagegen 的提示词、输入约定和原始输出路径；`FramedIcons` 为工程内交付图片。

历史制作曾使用独立 DLL 宿主。`prepare_isolated_authoring.py` 与 `run_isolated_authoring.ps1` 已于 2026-10-01 归档至 `trash/g18-hk416-publication-20261001/SourceAssets/HK416CommonAttachments20260930/`，不再通过复制 DLL 的宿主写主工程资产。后续使用本工程受保护的后台入口；工程编辑器已经运行时使用现有桥批次，不另起进程覆盖已加载或未保存的资源。原 `Saved/AssetAuthoring/HK416CommonHost` 未在本次整理中操作。

`run_authoring.ps1` 使用现有端口 8000 批次互斥运行后台导入；`import_assets.py` 导入模型、材质、动作并调用 `import_icons.py`。`publish_catalog.py` 只更新 HK416 目录块。`build_editor.ps1` 在本工程编辑器关闭时构建本轮 FPSGAME 模块的普通 Editor DLL（`-Module=FPSGAME`），最多四个并行编译任务；不重写其他编辑器占用的插件 DLL。

原始 HK416：MojoLeeDa 的 [HK416 Full ReWorked](https://sketchfab.com/3d-models/hk416-full-reworked-669a9ee17dc44580b53425a08c2f83d0)，CC BY 4.0；归因及原始素材见 `SourceAssets/HK416Reworked20260930/provenance.json`。通用模型、Infima 骨架与动画分别保留原有资产目录的许可，不能将 HK416 的 CC BY 许可套用于其他来源。

## 交付状态

实际资产保存与构建状态分别记录在本轮 `import_receipt.json`、`icon_import_receipt.json`、`catalog_publication.json`、`build_receipt.json`。脚本存在本身不代表已完成导入。

本轮已保存 19 个静态配件模型、56 段动画、枪体分区与 16 个 Texture2D（8 个图标键的两条查找路径）。独立宿主的启动配置扫描了未加载的 GameFeatureData 类，产生 handled ensure 并使 commandlet 返回 1；本轮显式保存操作均已完成，详见 `delivery_assets.json`，不将退出码描述为成功。FBX 的 bind-pose 提示与 HK416 原始导入相同；没有据此宣称运行时已经验收。

原生 FPSGAME 模块已完成后台编译和链接，构建结果为 `Succeeded`，普通 Editor DLL 已落盘；详见 `build_receipt.json` 与 `Saved/BuildEditor/hk416-common-attachments-20260930.log`。

按照用户规则，没有启动游戏、PIE、验收渲染、自动回归、lint 或配件一致性测试。生产图标渲染用于制作交付图片。游戏效果与交互由用户测试。
