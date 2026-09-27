# M1911 扩容弹匣（2026-09-27）

按枪械技能的扩容弹匣、手枪、配件图标与通用模型规则制作。未运行游戏、测试、验收截图或验收渲染。

## 配置

`ue_m1911` 开放 `magazine` 槽，提供 `false` 原厂弹匣与 `ext_mag` 扩容弹匣。

| 项目 | 扩容效果 |
|---|---|
| 容量 | 原厂 7 发 → 10 发，`mag_delta=3` |
| 普通与空仓装填耗时 | ×1.10，`reload_mult=1.1`；空仓沿用同一倍率 |
| 开镜耗时 | 基础耗时 +5%，`ads_percent=0.05` |

复用枪匠属性、物品安装状态、弹药扣除和存档路径；扩容本身不补发弹药。双持各自使用对应手枪的安装状态与计算容量。普通与空仓换弹继续使用 M1911 当前动作及时钟，不进入 M4 弹匣动作分支。

10 发单排弹匣的外观类别参考 [CMC Power Mag 官方产品页](https://cmproducts.com/power-mag-full-size-1911-10-round-45-acp-stainless-magazine.html)。新增模型是本机既有 M1911 游戏资产的派生，未下载参考产品模型、贴图或品牌标识；原模型许可与再分发边界沿用现有工程来源记录。

## 模型与材质

- 母版：`SourceAssets/M1911RearRain20260913/M1911_RearFinish_Editable.blend`。
- 使用原厂 `M1911_MagazineShell`、`M1911_MagazineFloorplate` 和 `M1911_MagazineFollower`；不缩放整只弹匣。
- 上部插接段、卡口、抓握区、原 UV 与法线保留。沿原下段壳体的真实截面向下续接，原下缘与底板整体移动；口部与托弹板保留。
- 新壳段单独烘焙 1024 BaseColor / ORM / Normal，延续原烤蓝钢材质；不拉长观察孔或将旧 UV 推到图集外。
- LOD0 / LOD1 / LOD2：4966 / 2483 / 993 三角形，离线导出 FBX LOD Group。
- 原厂区域复用 `M_M1911_Hero_Magazine` 及现有湿润映射；新增壳段提供独立 `WeaponWetness` 材质与天气映射资产。
- 源模型按原枪骨架网格坐标导出；挂到 `WPN_SOCKET_Magazine`，运行时抵消参考骨链变换，无猜测装配偏移。更换后隐藏原厂专属材质分区，恢复原装时显示回来；独立子弹材质与骨骼继续沿用。

## 接入

- `Weapons/M1911MagazineVisual.*`：单持原厂分区与扩容装配。
- `Weapons/M4DrumVisual.cpp`：为 M1911 开放扩容视觉入口；左轮仍不使用盒式弹匣。
- `Weapons/PistolDualWieldComponent.cpp`：复制副手的弹匣选项与模型，并同步隐藏或恢复左手原厂弹匣。
- `Weapons/M1911WeaponAssets.h`：专属模型与天气资产地址；现有图标/拾取预加载路径复用该映射。
- `WeatherViewEffectsComponent.cpp`：合并新增材质的湿润映射。
- `Content/ColdSteelData/gunsmith.json`：仅修改 M1911 定义中的弹匣槽、选项和说明，保留其他枪械的并行修改。

## 已保存内容

作者目录 `SourceAssets/M1911ExtendedMagazine20260927` 保留测量输入、可编辑 Blender、FBX、贴图、图标场景、导入脚本、目录变更前副本及回执。

引擎目录 `/Game/Weapons/M1911/ExtendedMagazine20260927` 已保存 1 个静态网格（含三档 LOD）、1 个材质、3 张材质贴图、1 个天气映射资产、3 张图标 Texture2D。

UI 实际使用的 PNG 位于 `Content/ColdSteelData/AttachmentIcons20260913`：`ue_m1911_category_magazine`、`ue_m1911_magazine_false`、`ue_m1911_magazine_ext_mag`。1024 RGBA 透明图使用真实部件、水平正交侧视和技能统一灰阶。分类与原厂共用同版图；图标去色仅作用于图标作者场景。

当前编辑器自动导入 PNG 后产生的共享目录未保存图标包未覆盖；本轮明确保存的 Texture2D 副本放在新配件的 `Icons/T_…` 目录。保存回执：`SourceAssets/M1911ExtendedMagazine20260927/import_receipt.json`。

## 构建与测试状态

后续同日按用户要求完成露出加长段与底板边角圆润化，当前运行资产已重导保存，原路径、容量和动作接口保持不变。新 LOD 为 7246 / 3622 / 1448 三角形，当前作者源转至 `SourceAssets/M1911AttachmentPolish20260927`；详见 [两种瞄具座与弹匣圆角修订](m1911-attachment-polish-20260927.md)。本文件此前的模型面数描述保留为初版记录。

资产已导入保存、枪匠配置已落盘。用户正常关闭 UE 后，工程现有的常规 `FPSGAMEEditor Win64 Development` 构建已完成，日志 `Saved/BuildEditor/build-20260927-181044.log` 记录 `Result: Succeeded`。本轮源码已纳入该构建，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 于 18:11:03 更新。沿用这次成功的标准构建，没有另起并行构建或重开编辑器。

没有进行运行、动画接触、装卸、弹药存档或视觉验收。模型的接口保留属于制作方案，不能代替用户在游戏中的测试。

后续防滑纹设计读取配置时，发现本轮 `effects` 原先使用字符串数组，与 `GunsmithSystem` 要求的 `{text, benefit}` 对象数组不符。已补正实际目录与生成脚本，保持容量与耗时数值不变；换弹提示按技能改为定性文字。此修正仅涉及配置和作者脚本，未重复构建或运行测试。
